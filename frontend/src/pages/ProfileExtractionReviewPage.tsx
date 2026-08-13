import {
  useEffect, useMemo, useRef, useState,
} from "react";
import {
  Link, useNavigate, useParams, useSearchParams,
} from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type {
  DocumentContent,
  MachineProfileRevision,
  ProfileEvidence,
  ProfileExtractionRun,
  ProfileProposal,
  ProfileReviewSummary,
  SourceDocument,
} from "../types";
import {
  REVIEW_QUEUES,
  PROPOSAL_STATUS_META,
  REVIEW_STATUS_META,
  activeFilterEntries,
  batchAcceptBlockReason,
  currentValue,
  filterProposals,
  filtersFromParams,
  queueCounts,
  showValue,
  type ReviewQueue,
  type ReviewView,
} from "./profileReview";

type ReviewAction =
  | "accepted" | "accepted_with_edit" | "rejected" | "deferred"
  | "manually_entered" | "not_applicable";
type BatchAction = "accept" | "defer" | "reject" | "not_applicable";

const QUEUE_KEYS = new Set<string>(REVIEW_QUEUES.map(([key]) => key));
const VIEW_KEYS = new Set<string>(["detailed", "compact", "checklist"]);
const sessionKey = (runId: number, suffix: string) =>
  `profile-review:${runId}:${suffix}`;

function StatusBadge({
  kind, value,
}: { kind: "proposal" | "review"; value: string }) {
  const meta = kind === "proposal"
    ? PROPOSAL_STATUS_META[value] : REVIEW_STATUS_META[value];
  return <span
    className={`review-status-badge ${kind}-${value}`}
    aria-label={`${kind === "proposal" ? "Proposal" : "Review"} status: ${meta?.label ?? value}`}
  >
    <span aria-hidden="true">{meta?.icon ?? "•"}</span>
    {meta?.label ?? value.replaceAll("_", " ")}
  </span>;
}

function HighlightText({ text, term }: { text: string; term: string }) {
  const query = term.trim();
  if (!query) return <>{text}</>;
  const index = text.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
  if (index < 0) return <>{text}</>;
  return <>
    {text.slice(0, index)}
    <mark>{text.slice(index, index + query.length)}</mark>
    {text.slice(index + query.length)}
  </>;
}

function humanLabel(key: string, proposals: ProfileProposal[]) {
  return proposals.find((item) => item.field_key === key)?.field_label
    ?? key.replaceAll("_", " ");
}

function flattenComparison(
  key: string,
  current: unknown,
  proposed: unknown,
): Array<{ key: string; current: unknown; proposed: unknown }> {
  if (
    current && proposed
    && typeof current === "object" && typeof proposed === "object"
    && !Array.isArray(current) && !Array.isArray(proposed)
  ) {
    const left = current as Record<string, unknown>;
    const right = proposed as Record<string, unknown>;
    return Array.from(new Set([...Object.keys(left), ...Object.keys(right)]))
      .filter((child) => left[child] !== right[child])
      .map((child) => ({
        key: child,
        current: left[child],
        proposed: right[child],
      }));
  }
  return [{ key, current, proposed }];
}

export function ProfileExtractionReviewPage() {
  const { machineId, runId } = useParams();
  const machine = Number(machineId); const id = Number(runId);
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const queue = (
    QUEUE_KEYS.has(params.get("queue") ?? "")
      ? params.get("queue") : "needs-review"
  ) as ReviewQueue;
  const view = (
    VIEW_KEYS.has(params.get("view") ?? "")
      ? params.get("view") : "detailed"
  ) as ReviewView;
  const autoAdvance = params.get("auto") !== "0";
  const queryParam = params.get("q") ?? "";
  const filters = useMemo(() => filtersFromParams(params), [params]);

  const [run, setRun] = useState<ProfileExtractionRun | null>(null);
  const [summary, setSummary] = useState<ProfileReviewSummary | null>(null);
  const [proposals, setProposals] = useState<ProfileProposal[]>([]);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [revisions, setRevisions] = useState<MachineProfileRevision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [highlightedId, setHighlightedId] = useState<number | null>(null);
  const [busyIds, setBusyIds] = useState<Set<number>>(new Set());
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [searchInput, setSearchInput] = useState(params.get("q") ?? "");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [evidenceExpanded, setEvidenceExpanded] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    () => new Set(
      JSON.parse(sessionStorage.getItem(sessionKey(id, "categories")) ?? "[]"),
    ),
  );

  const [editAction, setEditAction] = useState<ReviewAction | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editNote, setEditNote] = useState("");
  const [editDirty, setEditDirty] = useState(false);
  const [batchAction, setBatchAction] = useState<BatchAction | null>(null);
  const [highConfidenceBatch, setHighConfidenceBatch] = useState(false);
  const [batchModalIds, setBatchModalIds] = useState<number[]>([]);
  const [batchBusy, setBatchBusy] = useState(false);

  const [draft, setDraft] = useState<MachineProfileRevision | null>(null);
  const [comparison, setComparison] = useState<Array<{
    field_key: string; current: unknown; proposed: unknown; changed: boolean;
  }>>([]);
  const [base, setBase] = useState<"active" | "blank" | "selected_revision">("active");
  const [sourceRevisionId, setSourceRevisionId] = useState<number | undefined>();
  const [approval, setApproval] = useState(false);
  const [variantSelection, setVariantSelection] = useState("");
  const [rerunBusy, setRerunBusy] = useState(false);

  const [sourceContent, setSourceContent] = useState<DocumentContent | null>(null);
  const [technicalView, setTechnicalView] = useState(import.meta.env.MODE === "test");
  const [sourceLoading, setSourceLoading] = useState(false);
  const sourceDocumentId = Number(params.get("source") ?? 0);
  const sourceEvidenceId = Number(params.get("citation") ?? 0);
  const sourceOpenedHere = useRef(false);
  const sourceCloseButton = useRef<HTMLButtonElement>(null);

  const listRef = useRef<HTMLElement>(null);
  const evidenceRef = useRef<HTMLElement>(null);
  const categoryRef = useRef<HTMLElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const rowRefs = useRef<Map<number, HTMLElement>>(new Map());

  function updateParams(
    updates: Record<string, string | null>,
    replace = false,
  ) {
    const next = new URLSearchParams(params);
    Object.entries(updates).forEach(([key, value]) => {
      if (value == null || value === "" || value === "all") next.delete(key);
      else next.set(key, value);
    });
    setParams(next, { replace });
  }

  async function load() {
    setLoading(true); setError("");
    try {
      const [runData, proposalData, revisionData, summaryData, documentData] =
        await Promise.all([
          api.getProfileExtraction(id),
          api.listProfileProposals(id),
          api.listProfileRevisions(machine),
          api.getProfileReviewSummary(id),
          api.listDocuments(machine),
        ]);
      setRun(runData);
      setProposals(proposalData);
      setRevisions(revisionData);
      setSummary(summaryData);
      setDocuments(documentData);
      setVariantSelection(runData.selected_machine_variant ?? "");
      setSourceRevisionId((current) => current ?? revisionData[0]?.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Review workspace failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [id]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if ((params.get("q") ?? "") !== searchInput) {
        updateParams({ q: searchInput || null }, true);
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (queryParam !== searchInput) setSearchInput(queryParam);
  }, [queryParam]);

  const activeRevision = revisions.find((item) => item.status === "approved");
  const visible = useMemo(
    () => filterProposals(proposals, queue, filters, summary, activeRevision),
    [proposals, queue, filters, summary, activeRevision],
  );
  const counts = useMemo(
    () => queueCounts(proposals, summary),
    [proposals, summary],
  );
  const selectedField = params.get("field");
  const selected = proposals.find((item) =>
    item.field_key === selectedField || String(item.id) === selectedField
  ) ?? null;
  const selectedIndex = selected
    ? visible.findIndex((item) => item.id === selected.id) : -1;
  const activeFilters = activeFilterEntries(filters);

  useEffect(() => {
    if (!visible.length) return;
    if (!selected || !visible.some((item) => item.id === selected.id)) {
      updateParams({ field: visible[0].field_key }, true);
    }
  }, [visible, selected?.id]);

  useEffect(() => {
    if (!selected) return;
    const row = rowRefs.current.get(selected.id);
    row?.scrollIntoView?.({ block: "nearest" });
  }, [selected?.id, view]);

  useEffect(() => {
    if (!loading) {
      const restore = (element: HTMLElement | null, suffix: string) => {
        if (element) {
          element.scrollTop = Number(
            sessionStorage.getItem(sessionKey(id, suffix)) ?? 0,
          );
        }
      };
      restore(listRef.current, "field-scroll");
      restore(evidenceRef.current, "evidence-scroll");
      restore(categoryRef.current, "category-scroll");
    }
  }, [loading, view]);

  useEffect(() => {
    sessionStorage.setItem(
      sessionKey(id, "categories"),
      JSON.stringify([...expandedCategories]),
    );
  }, [expandedCategories]);

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!editDirty) return;
      event.preventDefault();
    };
    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, [editDirty]);

  useEffect(() => {
    if (!sourceDocumentId) {
      setSourceContent(null);
      return;
    }
    setSourceLoading(true);
    api.getDocumentContent(sourceDocumentId)
      .then(setSourceContent)
      .catch((cause) => setError(cause.message))
      .finally(() => setSourceLoading(false));
    window.setTimeout(() => sourceCloseButton.current?.focus(), 0);
  }, [sourceDocumentId]);

  function saveScroll() {
    if (listRef.current) sessionStorage.setItem(
      sessionKey(id, "field-scroll"), String(listRef.current.scrollTop),
    );
    if (evidenceRef.current) sessionStorage.setItem(
      sessionKey(id, "evidence-scroll"), String(evidenceRef.current.scrollTop),
    );
    if (categoryRef.current) sessionStorage.setItem(
      sessionKey(id, "category-scroll"), String(categoryRef.current.scrollTop),
    );
  }

  function attemptSelect(proposal: ProfileProposal, replace = false) {
    if (
      editDirty
      && selected?.id !== proposal.id
      && !window.confirm("Discard the unsaved review edit and switch fields?")
    ) return;
    setEditAction(null); setEditDirty(false);
    updateParams({ field: proposal.field_key }, replace);
  }

  function move(offset: number) {
    if (!visible.length) return;
    const index = selectedIndex < 0 ? 0 : selectedIndex;
    const target = visible[Math.max(0, Math.min(visible.length - 1, index + offset))];
    if (target) attemptSelect(target);
  }

  function moveTo(predicate: (proposal: ProfileProposal) => boolean) {
    if (!visible.length) return;
    const start = Math.max(selectedIndex + 1, 0);
    const ordered = [...visible.slice(start), ...visible.slice(0, start)];
    const target = ordered.find(predicate);
    if (target) attemptSelect(target);
  }

  function nextAfterAction(reviewedId: number) {
    if (!autoAdvance) return;
    const index = visible.findIndex((item) => item.id === reviewedId);
    const remaining = visible.filter((item) =>
      item.id !== reviewedId && item.review_status === "pending"
    );
    const next = visible.slice(Math.max(index + 1, 0)).find((item) =>
      item.id !== reviewedId && item.review_status === "pending"
    ) ?? remaining[0];
    if (next) {
      updateParams({ field: next.field_key }, true);
      return;
    }
    const recommended = summary?.recommended_next_queue;
    setToast((current) => `${current} ${
      recommended && recommended !== queue
        ? `Queue complete. Recommended next queue: ${recommended.replaceAll("-", " ")}.`
        : "Current queue complete."
    }`.trim());
  }

  function openEdit(action: ReviewAction) {
    if (!selected) return;
    setEditAction(action);
    setEditValue(showValue(selected.reviewed_value_json ?? selected.proposed_value_json));
    setEditNote(selected.review_note ?? "");
    setEditDirty(false);
  }

  async function review(
    action: ReviewAction,
    reviewedValue?: unknown,
    reviewNote = "",
  ) {
    if (!selected || busyIds.has(selected.id)) return;
    const prior = proposals;
    const optimistic = {
      ...selected,
      review_status: action,
      reviewed_value_json: action === "accepted"
        ? selected.proposed_value_json
        : action === "accepted_with_edit" || action === "manually_entered"
          ? reviewedValue : null,
      review_note: reviewNote || null,
    };
    setProposals((items) => items.map((item) =>
      item.id === selected.id ? optimistic : item
    ));
    setBusyIds((items) => new Set(items).add(selected.id));
    setError("");
    try {
      const updated = await api.reviewProfileProposal(selected.id, {
        review_status: action,
        reviewed_value: reviewedValue,
        review_note: reviewNote,
      });
      setProposals((items) => items.map((item) =>
        item.id === updated.id ? updated : item
      ));
      const nextSummary = await api.getProfileReviewSummary(id);
      setSummary(nextSummary);
      const status = REVIEW_STATUS_META[action]?.label ?? action;
      setToast(`${selected.field_label} marked ${status.toLocaleLowerCase()}.${autoAdvance ? " Moving to next pending field." : ""}`);
      setHighlightedId(selected.id);
      window.setTimeout(() => setHighlightedId(null), 900);
      setEditAction(null); setEditDirty(false);
      nextAfterAction(selected.id);
    } catch (cause) {
      setProposals(prior);
      setError(cause instanceof Error ? cause.message : "Review action failed");
    } finally {
      setBusyIds((items) => {
        const next = new Set(items); next.delete(selected.id); return next;
      });
    }
  }

  function requestReview(action: ReviewAction) {
    if (!selected) return;
    if (
      action === "accepted_with_edit" || action === "manually_entered"
      || (
        action === "accepted"
        && (
          selected.proposal_status === "conflicting"
          || selected.confidence < (summary?.confidence_medium_threshold ?? .7)
        )
      )
    ) {
      openEdit(action);
      return;
    }
    void review(action);
  }

  function submitEdit() {
    if (!editAction) return;
    const needsValue = ["accepted_with_edit", "manually_entered"].includes(editAction);
    const parsed = Number.isNaN(Number(editValue)) ? editValue : Number(editValue);
    if (needsValue && !editValue.trim()) {
      setError("A reviewed value is required.");
      return;
    }
    if (!editNote.trim()) {
      setError("A review note is required for this action.");
      return;
    }
    void review(editAction, needsValue ? parsed : undefined, editNote.trim());
  }

  function openBatch(action: BatchAction, ids = [...selectedIds], high = false) {
    setBatchAction(action);
    setBatchModalIds(ids);
    setHighConfidenceBatch(high);
  }

  const batchCandidates = batchModalIds
    .map((proposalId) => proposals.find((item) => item.id === proposalId))
    .filter((item): item is ProfileProposal => Boolean(item));
  const batchEligibility = batchCandidates.map((proposal) => ({
    proposal,
    reason: batchAction === "accept"
      ? batchAcceptBlockReason(proposal, summary)
      : proposal.review_status === "pending" ? null : "Already reviewed",
  }));
  const batchEligible = batchEligibility.filter((item) => !item.reason);
  const batchBlocked = batchEligibility.filter((item) => item.reason);

  async function applyBatch() {
    if (!batchAction || !batchEligible.length) return;
    setBatchBusy(true); setError("");
    try {
      const eligibleIds = batchEligible.map((item) => item.proposal.id);
      const result = highConfidenceBatch
        ? await api.acceptEligibleHighConfidence(id, eligibleIds)
        : await api.batchReviewProfileProposals(id, eligibleIds, batchAction);
      const reviewStatus = {
        accept: "accepted",
        defer: "deferred",
        reject: "rejected",
        not_applicable: "not_applicable",
      }[batchAction];
      setProposals((items) => items.map((item) =>
        result.succeeded.includes(item.id)
          ? {
            ...item,
            review_status: reviewStatus,
            reviewed_value_json: batchAction === "accept"
              ? item.proposed_value_json : null,
          }
          : item
      ));
      setSummary(result.summary);
      setToast(
        `${result.succeeded.length} fields updated.`
        + (result.failed.length ? ` ${result.failed.length} fields were blocked safely.` : ""),
      );
      setSelectedIds(new Set());
      setBatchAction(null);
      setBatchModalIds([]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Batch review failed");
    } finally {
      setBatchBusy(false);
    }
  }

  function startGuidedReview() {
    const recommended = (summary?.recommended_next_queue ?? "needs-review") as ReviewQueue;
    const high = summary?.confidence_high_threshold ?? .9;
    const medium = summary?.confidence_medium_threshold ?? .7;
    const prioritized = [...proposals].filter((item) => item.review_status === "pending")
      .sort((left, right) => {
        const priority = (item: ProfileProposal) =>
          item.proposal_status === "conflicting" ? 0
            : item.proposal_status === "found" && item.confidence >= high ? 1
              : item.proposal_status === "found" && item.confidence >= medium ? 2
                : item.proposal_status === "found" ? 3 : 4;
        return priority(left) - priority(right) || right.confidence - left.confidence;
      });
    updateParams({
      queue: recommended,
      field: prioritized[0]?.field_key ?? null,
      auto: "1",
    });
    void api.recordProfileReviewEvent(id, {
      event_type: "guided_review_started", queue: recommended,
    }).catch(() => undefined);
  }

  function selectQueue(nextQueue: ReviewQueue) {
    updateParams({ queue: nextQueue, field: null });
    setSelectedIds(new Set());
    void api.recordProfileReviewEvent(id, {
      event_type: "review_queue_opened", queue: nextQueue,
    }).catch(() => undefined);
  }

  function clearFilters() {
    const next = new URLSearchParams(params);
    [
      "category", "proposal", "review", "confidence", "safety",
      "verification", "evidence", "document", "authority", "scope",
      "variant", "optional", "q",
    ].forEach((key) => next.delete(key));
    setSearchInput("");
    setParams(next);
  }

  function openSource(evidence: ProfileEvidence) {
    saveScroll();
    sourceOpenedHere.current = true;
    updateParams({
      source: String(evidence.document_id),
      citation: String(evidence.id),
      page: String(evidence.page_start ?? 1),
    });
    void api.recordProfileReviewEvent(id, {
      event_type: "source_drawer_opened",
      queue,
      proposal_id: selected?.id,
      document_id: evidence.document_id,
    }).catch(() => undefined);
  }

  function closeSource() {
    void api.recordProfileReviewEvent(id, {
      event_type: "source_drawer_closed",
      queue,
      proposal_id: selected?.id,
      document_id: sourceDocumentId,
    }).catch(() => undefined);
    if (sourceOpenedHere.current) {
      sourceOpenedHere.current = false;
      navigate(-1);
    } else {
      updateParams({ source: null, citation: null, page: null }, true);
    }
  }

  const selectedEvidence = selected?.evidence.find(
    (item) => item.id === sourceEvidenceId,
  ) ?? selected?.evidence.find((item) => item.document_id === sourceDocumentId);
  const sourcePage = Number(params.get("page") ?? selectedEvidence?.page_start ?? 1);
  const sourceText = sourceContent?.pages.find(
    (page) => page.page_number === sourcePage,
  )?.text ?? sourceContent?.extracted_text ?? "";

  function moveCitation(offset: number) {
    if (!selected?.evidence.length || !selectedEvidence) return;
    const index = selected.evidence.findIndex((item) => item.id === selectedEvidence.id);
    const target = selected.evidence[Math.max(
      0, Math.min(selected.evidence.length - 1, index + offset),
    )];
    if (target) updateParams({
      source: String(target.document_id),
      citation: String(target.id),
      page: String(target.page_start ?? 1),
    }, true);
  }

  async function createDraft() {
    setError("");
    try {
      const result = await api.applyProfileDraft(id, {
        base_strategy: base,
        source_revision_id: base === "selected_revision" ? sourceRevisionId : undefined,
        review_summary: "Reviewed local draft; not approved.",
      });
      setDraft(result.revision); setComparison(result.comparison);
      setSummary(await api.getProfileReviewSummary(id));
      setToast(`Revision v${result.revision.revision_number} created as an inactive draft.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Draft creation failed");
    }
  }

  async function approve() {
    if (!draft || !approval) return;
    try {
      setDraft(await api.approveProfileRevision(
        draft.id, "Exact machine applicability reviewed and acknowledged.",
      ));
      setToast(`Revision v${draft.revision_number} explicitly approved.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Approval failed");
    }
  }

  async function rerunForVariant() {
    if (!variantSelection) return;
    setRerunBusy(true); setError("");
    try {
      const next = await api.rerunProfileExtraction(id, variantSelection);
      navigate(`/machines/${machine}/profile-extraction/${next.id}?queue=needs-review`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Variant re-run failed");
    } finally {
      setRerunBusy(false);
    }
  }

  useEffect(() => {
    const dialog = document.querySelector<HTMLElement>(
      '[role="dialog"][aria-modal="true"]',
    );
    if (!dialog) return;
    const focusable = dialog.querySelector<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), '
      + 'textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
    );
    window.setTimeout(() => focusable?.focus(), 0);
  }, [editAction, batchAction, helpOpen, sourceDocumentId]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const overlayOpen = Boolean(
        sourceDocumentId || helpOpen || editAction || batchAction,
      );
      if (overlayOpen && event.key === "Tab") {
        const dialog = document.querySelector<HTMLElement>(
          '[role="dialog"][aria-modal="true"]',
        );
        const focusable = dialog
          ? [...dialog.querySelectorAll<HTMLElement>(
            'button:not([disabled]), input:not([disabled]), select:not([disabled]), '
            + 'textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
          )].filter((item) => item.offsetParent !== null)
          : [];
        if (focusable.length) {
          const first = focusable[0];
          const last = focusable.at(-1)!;
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault(); last.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault(); first.focus();
          }
        }
        return;
      }
      const target = event.target as HTMLElement | null;
      const typing = target && (
        ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
        || target.isContentEditable
      );
      if (typing) {
        if (event.key === "Escape") target.blur();
        return;
      }
      if (event.key === "Escape") {
        if (sourceDocumentId) closeSource();
        else if (helpOpen) setHelpOpen(false);
        else if (editAction) setEditAction(null);
        else if (batchAction) setBatchAction(null);
        return;
      }
      if (overlayOpen) return;
      const key = event.key.toLocaleLowerCase();
      if (key === "n" || event.key === "ArrowDown") { event.preventDefault(); move(1); }
      else if (key === "p" || event.key === "ArrowUp") { event.preventDefault(); move(-1); }
      else if (key === "a") requestReview("accepted");
      else if (key === "e") openEdit("accepted_with_edit");
      else if (key === "r") requestReview("rejected");
      else if (key === "d") requestReview("deferred");
      else if (key === "m") openEdit("manually_entered");
      else if (key === "x") requestReview("not_applicable");
      else if (key === "o" && selected?.evidence[0]) openSource(selected.evidence[0]);
      else if (event.key === " ") {
        event.preventDefault(); setEvidenceExpanded((value) => !value);
      } else if (key === "f") {
        event.preventDefault(); searchRef.current?.focus();
      } else if (key === "?") setHelpOpen(true);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  if (loading) return <section className="page"><p role="status">Loading review workspace…</p></section>;
  if (!run || !summary) {
    return <section className="page"><p role="alert" className="form-error">
      {error || "Extraction review is unavailable."}
    </p></section>;
  }

  const statusFor = (proposal: ProfileProposal) =>
    proposal.review_status !== "pending"
      ? proposal.review_status : proposal.proposal_status;
  const selectedAcceptReason = selected
    ? batchAcceptBlockReason(selected, summary) : null;
  const highCandidates = proposals.filter((item) =>
    item.review_status === "pending"
    && item.confidence >= summary.confidence_high_threshold
  );

  async function confirmSimple(proposal: ProfileProposal) {
    setError("");
    try {
      const updated = await api.reviewProfileProposal(proposal.id, { review_status: "accepted", review_note: "Confirmed in simplified machine-information review." });
      setProposals((items) => items.map((item) => item.id === updated.id ? updated : item));
      setSummary(await api.getProfileReviewSummary(id)); setToast(`${proposal.field_label} confirmed.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Confirmation failed"); }
  }

  async function confirmAllClearFields() {
    const ids = highCandidates.filter((item) => item.proposal_status === "found").map((item) => item.id);
    if (!ids.length) return;
    try { await api.batchReviewProfileProposals(id, ids, "accept"); await load(); setToast(`${ids.length} clear fields confirmed.`); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Batch confirmation failed"); }
  }

  if (!technicalView) return <section className="page extraction-review-page v1-extraction-review">
    <PageHeader eyebrow="Machine information" title="Review Found Information" description={`${summary.machine_name} · ${summary.documents_analyzed} machine documents checked`} action={<Link className="button secondary" to={`/machines/${machine}/profile-extraction/new`}>Choose Different Documents</Link>} />
    {error && <p role="alert" className="form-error">{error}</p>}<div className="review-toast" aria-live="polite">{toast && <span>✓ {toast}</span>}</div>
    <section className="panel simple-extraction-summary"><div><strong>{summary.found}</strong><span>Found</span></div><div><strong>{summary.pending}</strong><span>Needs Review</span></div><div><strong>{summary.accepted + summary.accepted_with_edit}</strong><span>Confirmed</span></div><button className="button primary" disabled={!highCandidates.length} onClick={() => void confirmAllClearFields()}>Confirm All Clear Fields</button></section>
    <div className="simple-extraction-list">{proposals.map((proposal) => { const evidence = proposal.evidence[0]; const confirmed = proposal.review_status === "accepted" || proposal.review_status === "accepted_with_edit"; const status = confirmed ? "Confirmed" : proposal.proposal_status === "found" ? "Found" : "Needs Review"; return <article className="panel" key={proposal.id}><div><h2>{proposal.field_label}</h2><strong>{showValue(proposal.reviewed_value_json ?? proposal.proposed_value_json) || "Not found"}{proposal.unit ? ` ${proposal.unit}` : ""}</strong>{evidence && <p>Source: {evidence.document_title} · Page {evidence.page_start ?? "—"}</p>}</div><span className={`document-status ${confirmed ? "ready" : proposal.proposal_status === "found" ? "processing" : "failed"}`}>{status}</span>{!confirmed && proposal.proposal_status === "found" && <button onClick={() => void confirmSimple(proposal)}>Confirm</button>}<details><summary>Technical Extraction Details</summary><dl><div><dt>Confidence</dt><dd>{Math.round(proposal.confidence * 100)}%</dd></div><div><dt>Proposal status</dt><dd>{proposal.proposal_status}</dd></div><div><dt>Review status</dt><dd>{proposal.review_status}</dd></div></dl>{evidence && <blockquote>{evidence.excerpt}</blockquote>}</details></article>; })}</div>
    <details className="panel"><summary>Advanced</summary><p>Open the complete evidence-authority, filtering, comparison, and proposal-management workspace.</p><button onClick={() => setTechnicalView(true)}>Open Technical Review Workspace</button></details>
  </section>;

  return <section className="page extraction-review-page">
    <PageHeader
      eyebrow={`Extraction #${run.id}`}
      title="Profile review workspace"
      description={`${summary.machine_name} · ${run.provider_name} provider`}
      action={<Link className="button secondary" to={`/machines/${machine}/profile-extraction/new`}>
        New extraction
      </Link>}
    />
    <aside className="safety-banner" role="alert">
      <span className="safety-icon">!</span>
      <div><strong>Qualified review required</strong><p>{run.safety_notice}</p></div>
    </aside>
    {error && <p role="alert" className="form-error">{error}</p>}
    <div className="review-toast" aria-live="polite" aria-atomic="true">
      {toast && <span>✓ {toast}</span>}
    </div>

    <section className="review-dashboard panel" aria-labelledby="review-summary-heading">
      <header>
        <div>
          <span className="eyebrow">Guided review dashboard</span>
          <h2 id="review-summary-heading">{summary.machine_name}</h2>
          <p>
            Variant: <strong>{summary.selected_variant ?? "Not selected"}</strong>
            {" · "}Run: <strong>{summary.run_status.replaceAll("_", " ")}</strong>
            {" · "}{summary.documents_analyzed} documents analyzed
          </p>
        </div>
        <button className="button primary" onClick={startGuidedReview}>
          Start guided review
        </button>
      </header>
      <div className="review-summary-metrics">
        {[
          ["Total", summary.total], ["Found", summary.found],
          ["Not found", summary.not_found], ["Conflicts", summary.conflicting],
          ["Ambiguous", summary.ambiguous], ["Pending", summary.pending],
          ["Accepted", summary.accepted],
          ["Accepted + edit", summary.accepted_with_edit],
          ["Rejected", summary.rejected], ["Deferred", summary.deferred],
          ["Manual entry", summary.manually_entered],
          ["Not applicable", summary.not_applicable],
          ["Required remaining", summary.remaining_required_review],
        ].map(([label, value]) => <div key={label}>
          <strong>{value}</strong><small>{label}</small>
        </div>)}
      </div>
      <div className="review-progress-grid">
        <div>
          <label htmlFor="review-progress">
            Review progress: {summary.reviewed} / {summary.total} fields reviewed
          </label>
          <progress
            id="review-progress"
            max={summary.total}
            value={summary.reviewed}
            aria-valuetext={`${summary.reviewed} of ${summary.total} fields reviewed`}
          />
          <small>{summary.review_progress_percent}% intentionally reviewed</small>
        </div>
        <div>
          <label htmlFor="documentation-coverage">Documentation coverage</label>
          <progress
            id="documentation-coverage"
            max={100}
            value={summary.documentation_coverage}
            aria-valuetext={`${summary.documentation_coverage}% documentation coverage`}
          />
          <small>{summary.documentation_coverage}% · not a safety score</small>
        </div>
      </div>
    </section>

    {run.detected_variants_json.length > 1 && <section className="variant-warning">
      <strong>Multiple machine variants detected</strong>
      <p>{run.detected_variants_json.join(", ")}. Variant-dependent fields remain
        unresolved until exact applicability is confirmed.</p>
      <div className="variant-controls">
        <label>Exact variant
          <select
            aria-label="Exact machine variant"
            value={variantSelection}
            onChange={(event) => setVariantSelection(event.target.value)}
            disabled={rerunBusy}
          >
            <option value="">Select exact variant</option>
            {run.detected_variants_json.map((value) =>
              <option key={value}>{value}</option>
            )}
          </select>
        </label>
        <button
          className="button secondary"
          disabled={rerunBusy || !variantSelection || variantSelection === run.selected_machine_variant}
          onClick={() => void rerunForVariant()}
        >
          {rerunBusy ? "Re-running extraction…" : "Re-run for selected variant"}
        </button>
      </div>
    </section>}

    <nav className="review-queues" aria-label="Review queues">
      {REVIEW_QUEUES.map(([key, label]) => <button
        key={key}
        className={queue === key ? "active" : ""}
        aria-current={queue === key ? "page" : undefined}
        onClick={() => selectQueue(key)}
      >
        {label}<span>{counts[key]}</span>
      </button>)}
    </nav>

    <section className="sticky-review-header" aria-label="Review controls">
      <div>
        <strong>{REVIEW_QUEUES.find(([key]) => key === queue)?.[1]}</strong>
        <span>{visible.length} visible</span>
        <span>{summary.pending} pending</span>
        <span>{summary.conflict_pending} conflicts</span>
        <span>{selectedIds.size} selected</span>
      </div>
      <label className="review-search">
        <span className="sr-only">Search profile fields</span>
        <input
          ref={searchRef}
          aria-label="Search profile fields"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search fields or evidence…"
        />
      </label>
      <div className="sticky-review-actions">
        <button onClick={() => move(-1)} disabled={selectedIndex <= 0}>← Previous</button>
        <button onClick={() => move(1)} disabled={selectedIndex < 0 || selectedIndex >= visible.length - 1}>Next →</button>
        <label className="auto-advance-toggle">
          <input
            type="checkbox"
            checked={autoAdvance}
            onChange={(event) => updateParams({ auto: event.target.checked ? "1" : "0" }, true)}
          />
          Auto-advance
        </label>
        <select
          aria-label="Review view"
          value={view}
          onChange={(event) => updateParams({ view: event.target.value })}
        >
          <option value="detailed">Detailed review</option>
          <option value="compact">Compact table</option>
          <option value="checklist">Category checklist</option>
        </select>
        <button onClick={() => setFiltersOpen((value) => !value)}>
          Filters {activeFilters.length ? `(${activeFilters.length})` : ""}
        </button>
        <button aria-label="Keyboard shortcuts" onClick={() => setHelpOpen(true)}>?</button>
      </div>
    </section>

    {filtersOpen && <section className="review-filter-panel" aria-label="Advanced filters">
      <label>Category<select
        value={filters.category}
        onChange={(event) => updateParams({ category: event.target.value, field: null })}
      ><option value="all">All categories</option>
        {summary.category_summaries.map((item) =>
          <option key={item.category} value={item.category}>{item.category.replaceAll("_", " ")}</option>
        )}
      </select></label>
      <label>Proposal status<select
        value={filters.proposalStatus}
        onChange={(event) => updateParams({ proposal: event.target.value, field: null })}
      ><option value="all">All proposal states</option>
        {Object.keys(PROPOSAL_STATUS_META).map((value) =>
          <option key={value} value={value}>{PROPOSAL_STATUS_META[value].label}</option>
        )}
      </select></label>
      <label>Review status<select
        value={filters.reviewStatus}
        onChange={(event) => updateParams({ review: event.target.value, field: null })}
      ><option value="all">All review states</option>
        {Object.keys(REVIEW_STATUS_META).map((value) =>
          <option key={value} value={value}>{REVIEW_STATUS_META[value].label}</option>
        )}
      </select></label>
      <label>Confidence<select
        value={filters.confidence}
        onChange={(event) => updateParams({ confidence: event.target.value, field: null })}
      ><option value="all">Any confidence</option><option value="high">High only</option>
        <option value="medium">Medium</option><option value="low">Low</option>
      </select></label>
      <label>Evidence<select
        value={filters.evidence}
        onChange={(event) => updateParams({ evidence: event.target.value, field: null })}
      ><option value="all">Any evidence state</option><option value="has">Has supporting evidence</option>
        <option value="none">No evidence</option><option value="conflicting">Has conflicting evidence</option>
      </select></label>
      <label>Source document<select
        value={filters.sourceDocument}
        onChange={(event) => updateParams({ document: event.target.value, field: null })}
      ><option value="all">All documents</option>{documents.map((document) =>
        <option key={document.id} value={document.id}>{document.title}</option>
      )}</select></label>
      <label>Source authority<select
        value={filters.sourceAuthority}
        onChange={(event) => updateParams({ authority: event.target.value, field: null })}
      ><option value="all">All authorities</option>{Array.from(new Set(documents.map(
        (item) => item.document_type,
      ))).map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}
      </select></label>
      <label>Claim scope<select
        value={filters.claimScope}
        onChange={(event) => updateParams({ scope: event.target.value, field: null })}
      ><option value="all">All claim scopes</option>{summary.category_summaries.map((item) =>
        <option key={item.category} value={item.category}>{item.category.replaceAll("_", " ")}</option>
      )}</select></label>
      <label>Variant applicability<select
        value={filters.variant}
        onChange={(event) => updateParams({ variant: event.target.value, field: null })}
      ><option value="all">All variants</option>{run.detected_variants_json.map((value) =>
        <option key={value}>{value}</option>
      )}</select></label>
      <label>Sort by<select
        value={filters.sort}
        onChange={(event) => updateParams({ sort: event.target.value })}
      ><option value="priority">Review priority</option><option value="field">Field</option>
        <option value="category">Category</option><option value="confidence">Confidence</option>
        <option value="proposal">Proposal status</option><option value="review">Review status</option>
        <option value="evidence">Evidence count</option>
      </select></label>
      <label>Direction<select
        value={filters.direction}
        onChange={(event) => updateParams({ direction: event.target.value })}
      ><option value="asc">Ascending</option><option value="desc">Descending</option>
      </select></label>
      <div className="filter-checks">
        {[
          ["safety", filters.safetyOnly, "Safety-relevant only"],
          ["verification", filters.verificationOnly, "Requires exact-machine verification"],
          ["optional", filters.optionalOnly, "Optional capability"],
        ].map(([key, checked, label]) => <label key={String(key)}>
          <input
            type="checkbox"
            checked={Boolean(checked)}
            onChange={(event) => updateParams({ [String(key)]: event.target.checked ? "1" : null, field: null })}
          />{String(label)}
        </label>)}
      </div>
      <button className="button secondary" onClick={clearFilters}>Clear filters</button>
    </section>}

    {activeFilters.length > 0 && <div className="active-filter-chips" aria-label="Active filters">
      {activeFilters.map(([key, label]) => <button
        key={key}
        onClick={() => updateParams({ [key]: null, field: null })}
        aria-label={`Remove ${label} filter`}
      >{label} ×</button>)}
      <button onClick={clearFilters}>Clear all</button>
    </div>}

    <section className="category-completion-strip" aria-label="Category completion">
      {summary.category_summaries.map((item) => <button
        key={item.category}
        className={filters.category === item.category ? "active" : ""}
        onClick={() => updateParams({
          category: filters.category === item.category ? null : item.category,
          field: null,
        })}
      >
        <span>{item.complete ? "✓" : "○"}</span>
        <strong>{item.category.replaceAll("_", " ")}</strong>
        <small>{item.reviewed} / {item.total} reviewed · {item.pending} pending
          {item.conflicts ? ` · ${item.conflicts} conflicts` : ""}</small>
      </button>)}
    </section>

    <div className="review-position-toolbar">
      <span>
        {selectedIndex >= 0
          ? `Field ${selectedIndex + 1} of ${visible.length} in ${REVIEW_QUEUES.find(([key]) => key === queue)?.[1]}`
          : `No fields in ${REVIEW_QUEUES.find(([key]) => key === queue)?.[1]}`}
      </span>
      <div>
        <button onClick={() => moveTo((item) => item.review_status === "pending")}>Next unresolved</button>
        <button onClick={() => moveTo((item) => item.proposal_status === "conflicting" && item.review_status === "pending")}>Next conflict</button>
        <button onClick={() => moveTo((item) => item.proposal_status === "not_found" && item.review_status === "pending")}>Next not-found</button>
        <button onClick={() => moveTo((item) => item.confidence < summary.confidence_medium_threshold && item.review_status === "pending")}>Next low-confidence</button>
      </div>
    </div>

    <div className="bulk-entry-actions">
      <button
        className="button secondary"
        disabled={!visible.length}
        onClick={() => setSelectedIds(new Set(visible.map((item) => item.id)))}
      >Select all visible</button>
      <button
        className="button secondary"
        disabled={!visible.some((item) => item.review_status === "pending")}
        onClick={() => setSelectedIds(new Set(
          visible.filter((item) => item.review_status === "pending").map((item) => item.id),
        ))}
      >Select all eligible in queue</button>
      <button
        className="button secondary"
        disabled={!highCandidates.length}
        onClick={() => openBatch("accept", highCandidates.map((item) => item.id), true)}
      >Review and accept eligible high-confidence proposals</button>
    </div>

    {view === "detailed" && <div className="field-review-grid review-workspace">
      <nav
        ref={categoryRef}
        className="field-category-nav category-review-nav"
        aria-label="Category review status"
        onScroll={saveScroll}
      >
        <button
          className={filters.category === "all" ? "active" : ""}
          onClick={() => updateParams({ category: null, field: null })}
        >All categories <span>{proposals.length}</span></button>
        {summary.category_summaries.map((item) => <button
          className={filters.category === item.category ? "active" : ""}
          key={item.category}
          onClick={() => updateParams({ category: item.category, field: null })}
        >
          <strong>{item.complete ? "✓ " : ""}{item.category.replaceAll("_", " ")}</strong>
          <small>{item.reviewed}/{item.total} reviewed</small>
          <span>{item.pending}</span>
        </button>)}
      </nav>
      <ProposalList
        proposals={visible}
        selected={selected}
        selectedIds={selectedIds}
        highlightedId={highlightedId}
        onSelect={attemptSelect}
        onToggle={(proposalId) => setSelectedIds((items) => {
          const next = new Set(items);
          if (next.has(proposalId)) next.delete(proposalId); else next.add(proposalId);
          return next;
        })}
        listRef={listRef}
        rowRefs={rowRefs}
        onScroll={saveScroll}
      />
      <aside
        ref={evidenceRef}
        className="proposal-evidence detailed-evidence"
        onScroll={saveScroll}
      >
        {selected ? <>
          <header>
            <span className="eyebrow">{selected.field_category.replaceAll("_", " ")}</span>
            <h2>{selected.field_label}</h2>
            <div className="status-pair">
              <StatusBadge kind="proposal" value={selected.proposal_status} />
              <StatusBadge kind="review" value={selected.review_status} />
            </div>
          </header>
          <dl>
            <div><dt>Current active</dt><dd>{showValue(currentValue(selected, activeRevision))}</dd></div>
            <div><dt>Proposal</dt><dd>{showValue(selected.proposed_value_json)} {selected.unit}</dd></div>
            <div><dt>Confidence</dt><dd>{Math.round(selected.confidence * 100)}%</dd></div>
            <div><dt>Evidence</dt><dd>{selected.evidence.length} citations</dd></div>
          </dl>
          {selected.interpretation_note && <p className="variant-warning">{selected.interpretation_note}</p>}
          {selected.requires_exact_machine_verification && <p className="verification-warning">
            ! Exact machine option must be verified.
          </p>}
          {selected.safety_relevant && <p className="verification-warning">
            ! Safety-relevant field requires individual qualified review.
          </p>}
          <ReviewActions
            disabled={busyIds.has(selected.id)}
            acceptReason={selectedAcceptReason}
            onAction={requestReview}
          />
          <button
            className="evidence-collapse"
            aria-expanded={evidenceExpanded}
            onClick={() => setEvidenceExpanded((value) => !value)}
          >{evidenceExpanded ? "Collapse evidence" : "Expand evidence"}</button>
          {evidenceExpanded && <EvidenceCards
            proposal={selected}
            search={filters.search}
            onOpen={openSource}
          />}
          <Link to={`/manual-assistant?machine=${machine}&question=${encodeURIComponent(
            `Explain the evidence and missing information for ${selected.field_label}.`,
          )}`}>Ask why this was proposed →</Link>
        </> : <div className="review-empty"><h2>Queue complete</h2>
          <p>No fields match the current queue and filters.</p>
          {summary.recommended_next_queue && <button
            onClick={() => selectQueue(summary.recommended_next_queue as ReviewQueue)}
          >Open recommended queue</button>}
        </div>}
      </aside>
    </div>}

    {view === "compact" && <CompactTable
      proposals={visible}
      revision={activeRevision}
      selectedIds={selectedIds}
      selected={selected}
      onSelect={attemptSelect}
      onToggle={(proposalId) => setSelectedIds((items) => {
        const next = new Set(items);
        if (next.has(proposalId)) next.delete(proposalId); else next.add(proposalId);
        return next;
      })}
      onReview={requestReview}
    />}

    {view === "checklist" && <CategoryChecklist
      proposals={visible}
      summary={summary}
      expanded={expandedCategories}
      onToggleCategory={(category) => setExpandedCategories((items) => {
        const next = new Set(items);
        if (next.has(category)) next.delete(category); else next.add(category);
        return next;
      })}
      onSelect={attemptSelect}
      onReview={requestReview}
    />}

    {selectedIds.size > 0 && <section className="batch-action-bar" aria-label="Batch actions">
      <strong>{selectedIds.size} fields selected</strong>
      <span>
        {Array.from(selectedIds).filter((proposalId) => {
          const proposal = proposals.find((item) => item.id === proposalId);
          return proposal && !batchAcceptBlockReason(proposal, summary);
        }).length} eligible for batch acceptance
      </span>
      <button onClick={() => openBatch("accept")}>Accept selected</button>
      <button onClick={() => openBatch("defer")}>Defer selected</button>
      <button onClick={() => openBatch("reject")}>Reject selected</button>
      <button onClick={() => openBatch("not_applicable")}>Mark not applicable</button>
      <button onClick={() => setSelectedIds(new Set())}>Clear selection</button>
    </section>}

    <section className={`draft-readiness panel ${summary.draft_ready ? "ready" : "not-ready"}`}>
      <header><div><span className="eyebrow">Revision readiness</span>
        <h2>{draft
          ? draft.status === "approved" ? "Revision approved" : "Draft created"
          : summary.draft_ready ? "Ready for draft" : "Not ready for draft"}</h2>
      </div><span className="readiness-badge">{summary.draft_ready ? "✓ Ready" : "! Review required"}</span>
      </header>
      {!summary.draft_ready && <ul>{summary.readiness_reasons.map((reason) =>
        <li key={reason}>{reason}</li>
      )}</ul>}
      <div className="readiness-links">
        {summary.conflict_pending > 0 && <button onClick={() => selectQueue("conflicts")}>Review conflicts</button>}
        {summary.found_pending > 0 && <button onClick={() => selectQueue("needs-review")}>Review pending found fields</button>}
        {summary.not_found_pending > 0 && <button onClick={() => selectQueue("not-found")}>Resolve not-found fields</button>}
        {summary.variant_rerun_required && <button onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>Re-run selected variant</button>}
      </div>
      <div className="draft-controls">
        <label>Draft basis<select value={base} onChange={(event) =>
          setBase(event.target.value as typeof base)
        }><option value="active">Start from current active revision</option>
          <option value="blank">Start from blank draft</option>
          <option value="selected_revision">Start from selected prior revision</option>
        </select></label>
        {base === "selected_revision" && <label>Prior revision<select
          aria-label="Prior revision"
          value={sourceRevisionId}
          onChange={(event) => setSourceRevisionId(Number(event.target.value))}
        >{revisions.map((revision) => <option key={revision.id} value={revision.id}>
          v{revision.revision_number} · {revision.status}
        </option>)}</select></label>}
        <button
          className="button primary"
          disabled={!summary.draft_ready || (base === "selected_revision" && !sourceRevisionId)}
          onClick={() => void createDraft()}
        >Create reviewed draft</button>
      </div>
      {draft && <>
        <p><strong>Revision v{draft.revision_number}</strong> · {draft.status}.
          {draft.status !== "approved" && " This draft is inactive."}</p>
        <div className="revision-comparison human-comparison">
          {comparison.filter((item) => item.changed).flatMap((item) =>
            flattenComparison(item.field_key, item.current, item.proposed)
          ).map((item) => <div key={`${item.key}-${showValue(item.proposed)}`}>
            <strong>{humanLabel(item.key, proposals)}</strong>
            <span>{showValue(item.current)} → {showValue(item.proposed)}</span>
          </div>)}
        </div>
        <details><summary>Show technical details</summary>
          <pre>{JSON.stringify(comparison.filter((item) => item.changed), null, 2)}</pre>
        </details>
        <label className="approval-check">
          <input
            type="checkbox"
            checked={approval}
            onChange={(event) => setApproval(event.target.checked)}
          />
          I confirm this draft was reviewed against the exact machine configuration
          and is not automatically certified for production use.
        </label>
        <button
          className="button primary"
          disabled={!approval || draft.status === "approved"}
          onClick={() => void approve()}
        >{draft.status === "approved" ? "Explicitly approved" : "Approve as active revision"}</button>
      </>}
    </section>

    {editAction && selected && <div className="modal-backdrop" role="presentation">
      <section
        className="review-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-review-heading"
      >
        <header><h2 id="edit-review-heading">
          {REVIEW_STATUS_META[editAction]?.label ?? "Review field"} · {selected.field_label}
        </h2><button aria-label="Close edit" onClick={() => {
          if (!editDirty || window.confirm("Discard this unsaved review edit?")) {
            setEditAction(null); setEditDirty(false);
          }
        }}>×</button></header>
        {["accepted_with_edit", "manually_entered"].includes(editAction) && <label>
          Reviewed value<input
            value={editValue}
            onChange={(event) => { setEditValue(event.target.value); setEditDirty(true); }}
          />
        </label>}
        <label>Required review note<textarea
          rows={4}
          value={editNote}
          onChange={(event) => { setEditNote(event.target.value); setEditDirty(true); }}
        /></label>
        <div className="modal-actions">
          <button className="button primary" onClick={submitEdit}>Save and continue</button>
          <button className="button secondary" onClick={() => {
            setEditAction(null); setEditDirty(false);
          }}>Discard</button>
        </div>
      </section>
    </div>}

    {batchAction && <div className="modal-backdrop" role="presentation">
      <section
        className="review-modal batch-confirmation"
        role="dialog"
        aria-modal="true"
        aria-labelledby="batch-review-heading"
      >
        <header><div><span className="eyebrow">Protected batch workflow</span>
          <h2 id="batch-review-heading">
            Confirm {batchAction.replaceAll("_", " ")} for {batchEligible.length} fields
          </h2></div><button aria-label="Close batch review" onClick={() => setBatchAction(null)}>×</button>
        </header>
        <p>Confidence is not proof of safety. Every accepted value remains advisory
          and requires exact-machine review before revision approval.</p>
        <h3>Eligible fields</h3>
        <ul>{batchEligible.map(({ proposal }) => <li key={proposal.id}>
          <label><input
            type="checkbox"
            checked={batchModalIds.includes(proposal.id)}
            onChange={() => setBatchModalIds((items) =>
              items.includes(proposal.id)
                ? items.filter((value) => value !== proposal.id)
                : [...items, proposal.id]
            )}
          />{proposal.field_label} · {Math.round(proposal.confidence * 100)}%
          </label>
        </li>)}</ul>
        {batchBlocked.length > 0 && <><h3>Excluded safely</h3>
          <ul className="blocked-fields">{batchBlocked.map(({ proposal, reason }) =>
            <li key={proposal.id}><strong>{proposal.field_label}</strong> — {reason}</li>
          )}</ul></>}
        <div className="modal-actions">
          <button
            className="button primary"
            disabled={batchBusy || !batchEligible.length}
            onClick={() => void applyBatch()}
          >{batchBusy ? "Applying reviewed actions…" : "Acknowledge and apply"}</button>
          <button className="button secondary" onClick={() => setBatchAction(null)}>Cancel</button>
        </div>
      </section>
    </div>}

    {helpOpen && <div className="modal-backdrop" role="presentation">
      <section className="review-modal shortcut-help" role="dialog" aria-modal="true" aria-labelledby="shortcuts-heading">
        <header><h2 id="shortcuts-heading">Keyboard shortcuts</h2>
          <button aria-label="Close keyboard shortcuts" onClick={() => setHelpOpen(false)}>×</button>
        </header>
        <dl>
          {[
            ["N / ↓", "Next field"], ["P / ↑", "Previous field"], ["A", "Accept"],
            ["E", "Edit and accept"], ["R", "Reject"], ["D", "Defer"],
            ["M", "Enter manually"], ["X", "Mark not applicable"], ["O", "Open source"],
            ["Space", "Expand or collapse evidence"], ["F", "Focus search"], ["Escape", "Close overlay"],
          ].map(([key, action]) => <div key={key}><dt>{key}</dt><dd>{action}</dd></div>)}
        </dl>
      </section>
    </div>}

    {sourceDocumentId > 0 && <div className="source-drawer-backdrop" role="presentation">
      <aside
        className="source-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-drawer-heading"
      >
        <header>
          <div><span className="eyebrow">{selectedEvidence?.evidence_type ?? "source"} evidence</span>
            <h2 id="source-drawer-heading">
              {sourceContent?.document.title ?? selectedEvidence?.document_title ?? "Source document"}
            </h2>
            <small>{sourceContent?.document.document_type.replaceAll("_", " ")}
              {" · "}Page {sourcePage}
              {selectedEvidence?.section_title ? ` · ${selectedEvidence.section_title}` : ""}
            </small>
          </div>
          <button ref={sourceCloseButton} aria-label="Close source drawer" onClick={closeSource}>×</button>
        </header>
        <div className="source-drawer-nav">
          <button onClick={() => moveCitation(-1)} disabled={!selectedEvidence || selected?.evidence[0]?.id === selectedEvidence.id}>← Previous citation</button>
          <button onClick={() => moveCitation(1)} disabled={!selectedEvidence || selected?.evidence.at(-1)?.id === selectedEvidence.id}>Next citation →</button>
          <Link
            target="_blank"
            rel="noreferrer"
            to={`/documents/${sourceDocumentId}?page=${sourcePage}&highlight=${encodeURIComponent(
              selectedEvidence?.raw_value_text ?? selected?.field_label ?? "",
            )}`}
          >Open full document in new tab ↗</Link>
        </div>
        {selectedEvidence && <section className={`source-citation ${selectedEvidence.evidence_type}`}>
          <strong>{selectedEvidence.evidence_type} citation</strong>
          <p><HighlightText
            text={selectedEvidence.excerpt}
            term={selectedEvidence.raw_value_text ?? selected?.field_label ?? ""}
          /></p>
          <dl>
            <div><dt>Exact extracted value</dt><dd>{selectedEvidence.raw_value_text ?? "—"}</dd></div>
            <div><dt>Relevance</dt><dd>{Math.round(selectedEvidence.relevance_score * 100)}%</dd></div>
            <div><dt>Variant applicability</dt><dd>{selected?.variant_applicability_json.join(", ") || "General"}</dd></div>
            <div><dt>Verification</dt><dd>{selected?.requires_exact_machine_verification ? "Required" : "Not flagged"}</dd></div>
          </dl>
        </section>}
        <section className="source-page-text">
          <h3>Extracted page text</h3>
          {sourceLoading ? <p>Loading source page…</p>
            : <pre><HighlightText
              text={sourceText || "No extracted page text is available."}
              term={selectedEvidence?.raw_value_text ?? selected?.field_label ?? ""}
            /></pre>}
        </section>
      </aside>
    </div>}
  </section>;
}

function ProposalList({
  proposals, selected, selectedIds, highlightedId, onSelect, onToggle,
  listRef, rowRefs, onScroll,
}: {
  proposals: ProfileProposal[];
  selected: ProfileProposal | null;
  selectedIds: Set<number>;
  highlightedId: number | null;
  onSelect: (proposal: ProfileProposal) => void;
  onToggle: (proposalId: number) => void;
  listRef: React.RefObject<HTMLElement | null>;
  rowRefs: React.RefObject<Map<number, HTMLElement>>;
  onScroll: () => void;
}) {
  return <section
    ref={listRef}
    className="proposal-list guided-proposal-list"
    aria-label="Profile fields"
    onScroll={onScroll}
  >
    {!proposals.length && <div className="review-empty"><strong>Queue complete</strong>
      <p>No fields match the active queue and filters.</p></div>}
    {proposals.map((proposal) => <article
      ref={(node) => {
        if (node) rowRefs.current.set(proposal.id, node);
        else rowRefs.current.delete(proposal.id);
      }}
      className={[
        "proposal-row", selected?.id === proposal.id ? "selected" : "",
        highlightedId === proposal.id ? "review-updated" : "",
        `state-${proposal.review_status}`,
      ].join(" ")}
      key={proposal.id}
    >
      <label className="row-checkbox">
        <span className="sr-only">Select {proposal.field_label}</span>
        <input
          type="checkbox"
          aria-label={`Select ${proposal.field_label}`}
          checked={selectedIds.has(proposal.id)}
          onChange={() => onToggle(proposal.id)}
        />
      </label>
      <button className="proposal-row-main" onClick={() => onSelect(proposal)}>
        <div><strong>{proposal.field_label}</strong>
          <small>{proposal.field_category.replaceAll("_", " ")}</small></div>
        <b>{showValue(proposal.reviewed_value_json ?? proposal.proposed_value_json)} {proposal.unit}</b>
        <div className="row-statuses">
          <StatusBadge kind="proposal" value={proposal.proposal_status} />
          <StatusBadge kind="review" value={proposal.review_status} />
        </div>
        <span>{Math.round(proposal.confidence * 100)}% · {proposal.evidence.length} source{proposal.evidence.length === 1 ? "" : "s"}</span>
      </button>
    </article>)}
  </section>;
}

function ReviewActions({
  disabled, acceptReason, onAction,
}: {
  disabled: boolean;
  acceptReason: string | null;
  onAction: (action: ReviewAction) => void;
}) {
  return <div className="proposal-actions sticky-field-actions">
    <button disabled={disabled} onClick={() => onAction("accepted")}>✓ Accept</button>
    <button disabled={disabled} onClick={() => onAction("accepted_with_edit")}>✎ Edit and accept</button>
    <button disabled={disabled} onClick={() => onAction("rejected")}>× Reject</button>
    <button disabled={disabled} onClick={() => onAction("deferred")}>↷ Defer</button>
    <button disabled={disabled} onClick={() => onAction("manually_entered")}>+ Enter manually</button>
    <button disabled={disabled} onClick={() => onAction("not_applicable")}>— Not applicable</button>
    {acceptReason && <small>Batch acceptance blocked: {acceptReason}</small>}
  </div>;
}

function EvidenceCards({
  proposal, search, onOpen,
}: {
  proposal: ProfileProposal;
  search: string;
  onOpen: (evidence: ProfileEvidence) => void;
}) {
  if (!proposal.evidence.length) {
    return <div className="no-evidence"><StatusBadge kind="proposal" value="not_found" />
      <p>Not found in the selected documents. An intentional disposition is required.</p></div>;
  }
  return <div className="evidence-cards"><h3>Evidence</h3>
    {proposal.evidence.map((evidence) => <details
      open={evidence.excerpt.length < 360}
      className={`profile-evidence ${evidence.evidence_type}`}
      key={evidence.id}
    >
      <summary>
        <span>[{evidence.citation_number}] {evidence.evidence_type}</span>
        <strong>{evidence.document_title}</strong>
        <small>{evidence.document_type.replaceAll("_", " ")}
          {" · "}Page {evidence.page_start ?? "—"}
          {" · "}{evidence.section_title ?? "Unlabeled"}
          {" · "}{Math.round(evidence.relevance_score * 100)}% relevance</small>
      </summary>
      <p><HighlightText
        text={evidence.excerpt}
        term={evidence.raw_value_text ?? search}
      /></p>
      <dl>
        <div><dt>Exact value</dt><dd>{evidence.raw_value_text ?? "—"}</dd></div>
        <div><dt>Claim scope</dt><dd>{proposal.field_category.replaceAll("_", " ")}</dd></div>
        <div><dt>Variant</dt><dd>{proposal.variant_applicability_json.join(", ") || "General"}</dd></div>
        <div><dt>Option dependent</dt><dd>{proposal.requires_exact_machine_verification ? "Yes" : "No"}</dd></div>
      </dl>
      <button onClick={() => onOpen(evidence)}>Open source in drawer →</button>
    </details>)}
  </div>;
}

function CompactTable({
  proposals, revision, selectedIds, selected, onSelect, onToggle, onReview,
}: {
  proposals: ProfileProposal[];
  revision?: MachineProfileRevision;
  selectedIds: Set<number>;
  selected: ProfileProposal | null;
  onSelect: (proposal: ProfileProposal) => void;
  onToggle: (proposalId: number) => void;
  onReview: (action: ReviewAction) => void;
}) {
  return <div className="compact-review-table-wrap">
    <table className="compact-review-table">
      <thead><tr><th>Select</th><th>Field</th><th>Category</th><th>Current</th>
        <th>Proposed</th><th>Confidence</th><th>Proposal</th><th>Review</th>
        <th>Evidence</th><th>Verification</th><th>Actions</th></tr></thead>
      <tbody>{proposals.map((proposal) => <tr
        key={proposal.id}
        className={selected?.id === proposal.id ? "selected" : ""}
      >
        <td><input
          type="checkbox"
          aria-label={`Select ${proposal.field_label}`}
          checked={selectedIds.has(proposal.id)}
          onChange={() => onToggle(proposal.id)}
        /></td>
        <th><button onClick={() => onSelect(proposal)}>{proposal.field_label}</button></th>
        <td>{proposal.field_category.replaceAll("_", " ")}</td>
        <td>{showValue(currentValue(proposal, revision))}</td>
        <td>{showValue(proposal.reviewed_value_json ?? proposal.proposed_value_json)} {proposal.unit}</td>
        <td>{Math.round(proposal.confidence * 100)}%</td>
        <td><StatusBadge kind="proposal" value={proposal.proposal_status} /></td>
        <td><StatusBadge kind="review" value={proposal.review_status} /></td>
        <td>{proposal.evidence.length}</td>
        <td>{proposal.requires_exact_machine_verification ? "! Required" : "—"}</td>
        <td><button onClick={() => onSelect(proposal)}>Review</button></td>
      </tr>)}</tbody>
    </table>
  </div>;
}

function CategoryChecklist({
  proposals, summary, expanded, onToggleCategory, onSelect, onReview,
}: {
  proposals: ProfileProposal[];
  summary: ProfileReviewSummary;
  expanded: Set<string>;
  onToggleCategory: (category: string) => void;
  onSelect: (proposal: ProfileProposal) => void;
  onReview: (action: ReviewAction) => void;
}) {
  return <section className="category-checklist">
    {summary.category_summaries.map((category) => {
      const items = proposals.filter((item) => item.field_category === category.category);
      if (!items.length) return null;
      const open = expanded.has(category.category);
      return <article key={category.category}>
        <button
          className="category-checklist-heading"
          aria-expanded={open}
          onClick={() => onToggleCategory(category.category)}
        >
          <span>{category.complete ? "✓" : open ? "▾" : "▸"}</span>
          <strong>{category.category.replaceAll("_", " ")}</strong>
          <small>{category.reviewed} / {category.total} reviewed · {category.pending} pending</small>
        </button>
        {open && <div>{items.map((proposal) => <div className="checklist-row" key={proposal.id}>
          <StatusBadge kind="review" value={proposal.review_status} />
          <button onClick={() => onSelect(proposal)}>{proposal.field_label}</button>
          <span>{showValue(proposal.reviewed_value_json ?? proposal.proposed_value_json)} {proposal.unit}</span>
          <button onClick={() => onSelect(proposal)}>Review</button>
        </div>)}</div>}
      </article>;
    })}
  </section>;
}
