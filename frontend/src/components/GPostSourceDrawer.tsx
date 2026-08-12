import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { DocumentContent, GPostMapping, SourceDocument } from "../types";

export function GPostSourceDrawer({
  mapping, document, onClose,
}: { mapping: GPostMapping; document: SourceDocument | null; onClose: () => void }) {
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [error, setError] = useState("");
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!document) return;
    api.getDocumentContent(document.id).then(setContent).catch((cause) => setError(cause.message));
    window.setTimeout(() => closeRef.current?.focus(), 0);
  }, [document?.id]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", close); return () => window.removeEventListener("keydown", close);
  }, [onClose]);
  const page = mapping.source_page ?? 1;
  const pageText = content?.pages.find((item) => item.page_number === page)?.text
    ?? content?.extracted_text ?? mapping.source_excerpt ?? "";
  return <div className="source-drawer-backdrop" role="presentation" onMouseDown={(event) => {
    if (event.target === event.currentTarget) onClose();
  }}><aside className="source-drawer" role="dialog" aria-modal="true" aria-label="G-POST mapping source">
    <header><div><span className="eyebrow">Source evidence</span><h2>{document?.title ?? "Manual configuration"}</h2><small>{document?.document_type.replaceAll("_", " ") ?? "No uploaded document evidence"}</small></div><button ref={closeRef} aria-label="Close source viewer" onClick={onClose}>×</button></header>
    <div className="source-drawer-nav"><span>Page {page}</span><span>{mapping.source_section || "Section not recorded"}</span>{document && <Link to={`/documents/${document.id}`}>Open Full Document</Link>}</div>
    {error && <p className="form-error">{error}</p>}
    <article className="source-citation"><strong>Relevant text</strong><p>{mapping.source_excerpt || "No excerpt is attached to this mapping."}</p><dl><div><dt>CL command</dt><dd>{mapping.cl_command}</dd></div><div><dt>Authority</dt><dd>{mapping.source_authority || "Not recorded"}</dd></div><div><dt>Page</dt><dd>{mapping.source_page ?? "Not recorded"}</dd></div><div><dt>Section</dt><dd>{mapping.source_section || "Not recorded"}</dd></div></dl></article>
    <section className="source-page-text"><h3>Extracted page text</h3>{content ? <pre>{pageText}</pre> : <p className="loading">Loading document source…</p>}</section>
  </aside></div>;
}
