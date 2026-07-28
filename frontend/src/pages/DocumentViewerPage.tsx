import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { DocumentContent } from "../types";

export function DocumentViewerPage() {
  const { documentId } = useParams();
  const [params] = useSearchParams();
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [page, setPage] = useState(Number(params.get("page") ?? 1));
  const [query, setQuery] = useState(params.get("highlight") ?? "");
  const [error, setError] = useState("");
  useEffect(() => {
    api.getDocumentContent(Number(documentId)).then(setContent).catch((cause) => setError(cause.message));
  }, [documentId]);
  const current = content?.pages.find((item) => item.page_number === page);
  const shownText = useMemo(() => {
    if (!current || !query.trim()) return current?.text ?? "";
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return current.text.split(new RegExp(`(${escaped})`, "ig"));
  }, [current, query]);
  if (error) return <section className="page"><p className="form-error">{error}</p></section>;
  if (!content) return <section className="page"><p className="loading">Loading extracted document…</p></section>;
  return <section className="page">
    <PageHeader eyebrow="Extracted source" title={content.document.title} description={`${content.document.document_type.replaceAll("_", " ")} · ${content.document.original_filename}`} action={<Link className="button secondary" to={`/documents?machine=${content.document.machine_profile_id}`}>← Document library</Link>} />
    <div className="viewer-meta"><span className={`document-status ${content.document.processing_status}`}>{content.document.processing_status}</span><span>{content.document.page_count ?? 0} pages</span><label>Find in page<input value={query} onChange={(event) => setQuery(event.target.value)} /></label></div>
    <div className="viewer-grid">
      <aside className="page-nav" aria-label="Document pages">{content.pages.map((item) => <button className={item.page_number === page ? "active" : ""} key={item.page_number} onClick={() => setPage(item.page_number)}>Page {item.page_number}<small>{item.character_count.toLocaleString()} characters</small></button>)}</aside>
      <article className="extracted-page"><header><strong>Page {page}</strong><small>Extracted text view</small></header><pre>{Array.isArray(shownText) ? shownText.map((part, index) => part.toLowerCase() === query.toLowerCase() ? <mark key={index}>{part}</mark> : part) : shownText}</pre></article>
      <aside className="chunk-inspector"><h2>Supporting chunks</h2>{content.chunks.filter((chunk) => chunk.page_start === page).map((chunk) => <article id={`chunk-${chunk.id}`} key={chunk.id}><strong>Chunk {chunk.chunk_index + 1}</strong><small>{chunk.section_title ?? "No section title"} · ~{chunk.token_estimate} tokens</small><p>{chunk.content}</p></article>)}</aside>
    </div>
  </section>;
}

