"""Local, deterministic and deliberately conservative G-POST diagnostic parsing."""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_LISTING_BYTES = 2_000_000
SEVERITIES = {"INFO", "WARNING", "ERROR", "FATAL"}
PREFIX = re.compile(r"^\s*(?:\[)?(INFO|WARNING|WARN|ERROR|ERR|FATAL)(?:\])?\s*[:\-]?\s*(?:\[([A-Z0-9_.-]+)\]\s*)?(.*)$", re.I)
LINE_REF = re.compile(r"\bline\s*[:#]?\s*(\d+)\b", re.I)
CODE_REF = re.compile(r"\b(?:code|msg)\s*[:#]?\s*([A-Z][A-Z0-9_.-]+)\b", re.I)


@dataclass(frozen=True)
class DiagnosticRecord:
    severity: str
    code: str | None
    message: str
    line_reference: int | None
    source_reference: str | None
    custom_logic_reference_id: int | None
    raw_excerpt: str


class GPostDiagnosticParser:
    def parse(self, text: str, custom_logic: list[tuple[int, str]] | None = None) -> list[DiagnosticRecord]:
        if not text.strip(): raise ValueError("Diagnostic listing is empty")
        if len(text.encode("utf-8")) > MAX_LISTING_BYTES: raise ValueError("Diagnostic listing exceeds the 2 MB local parsing limit")
        links = [(item_id, name, name.casefold()) for item_id, name in (custom_logic or [])]
        records: list[DiagnosticRecord] = []
        for physical_line, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line: continue
            match = PREFIX.match(line)
            if match:
                severity = {"WARN": "WARNING", "ERR": "ERROR"}.get(match.group(1).upper(), match.group(1).upper())
                code = match.group(2)
                message = match.group(3).strip() or "Diagnostic message not provided"
            elif any(token in line.upper() for token in ("WARNING", "ERROR", "FATAL")):
                # The keyword is evidence, but an unfamiliar layout means the exact severity is unknown.
                severity, code, message = "UNKNOWN", None, line
            else:
                continue
            if not code and (code_match := CODE_REF.search(line)): code = code_match.group(1)
            line_reference = int(ref.group(1)) if (ref := LINE_REF.search(line)) else physical_line
            linked_id = None; source = None
            folded = line.casefold()
            exact = [(item_id, name) for item_id, name, key in links if key in folded]
            if len(exact) == 1: linked_id, source = exact[0][0], f"Custom Logic → {exact[0][1]}"
            records.append(DiagnosticRecord(severity, code, message, line_reference, source,
                                             linked_id, raw[:500]))
        if not records:
            records.append(DiagnosticRecord("UNKNOWN", None, "No recognized diagnostic structure; site format verification required.",
                                             None, None, None, text.splitlines()[0][:500]))
        return records


def fil_static_checks(source: str, known_identifiers: list[str] | None = None) -> list[dict]:
    """Advisory lexical checks only; this is not a FIL compiler."""
    findings: list[dict] = []
    if not source.strip(): return [{"severity": "ERROR", "code": "FIL_EMPTY", "message": "FIL source is empty."}]
    for opening, closing, label in (("(", ")", "parentheses"), ("[", "]", "brackets")):
        if source.count(opening) != source.count(closing):
            findings.append({"severity": "WARNING", "code": "FIL_UNBALANCED", "message": f"Unbalanced {label}."})
    identifiers = [item.casefold() for item in (known_identifiers or [])]
    duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
    for item in duplicates:
        findings.append({"severity": "WARNING", "code": "FIL_DUPLICATE_IDENTIFIER", "message": f"Duplicate identifier: {item}"})
    return findings
