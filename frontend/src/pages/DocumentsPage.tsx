import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { DocumentType, MachineProfile, SourceDocument } from "../types";

const types: Array<[DocumentType, string]> = [
  ["machine_manual", "Machine Manual"],
  ["controller_manual", "Controller Manual"],
  ["programming_manual", "Programming Manual"],
  ["specification_document", "Specification"],
  ["company_standard", "Internal Procedure"],
  ["post_processor_document", "Reference"],
  ["other", "Other"],
];

export function DocumentsPage() {
  const [params, setParams] = useSearchParams();
  const [machines, setMachines] = useState<MachineProfile[]>([]);
  const [machineId, setMachineId] = useState(params.get("machine") ?? "");
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [title, setTitle] = useState("");
  const [type, setType] = useState<DocumentType>("controller_manual");
  const [file, setFile] = useState<File | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Awaited<ReturnType<typeof api.searchDocuments>>>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listProfiles().then((items) => {
      setMachines(items);
      if (!machineId && items[0]) setMachineId(String(items[0].id));
    }).catch((cause) => setError(cause.message));
  }, []);
  useEffect(() => {
    if (!machineId) return;
    setParams({ machine: machineId }, { replace: true });
    api.listDocuments(Number(machineId)).then(setDocuments).catch((cause) => setError(cause.message));
  }, [machineId]);

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file || !machineId) return;
    setBusy(true); setError("");
    try {
      await api.uploadDocument(Number(machineId), title || file.name, type, file);
      setDocuments(await api.listDocuments(Number(machineId)));
      setTitle(""); setFile(null);
      const input = document.getElementById("manual-file") as HTMLInputElement | null;
      if (input) input.value = "";
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Upload failed.");
    } finally { setBusy(false); }
  }

  async function search(event: FormEvent) {
    event.preventDefault();
    if (!query.trim() || !machineId) return;
    try { setResults(await api.searchDocuments(Number(machineId), query)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Search failed."); }
  }

  async function remove(item: SourceDocument) {
    if (!confirm(`Delete “${item.title}” and its extracted chunks?`)) return;
    await api.deleteDocument(item.id);
    setDocuments((current) => current.filter((document) => document.id !== item.id));
  }

  return <section className="page">
    <PageHeader eyebrow="Machine references" title="Documents" description="Upload and review machine/controller documentation used to build Machine Knowledge." />
    <div className="reference-toolbar">
      <label>Machine<select aria-label="Machine profile" value={machineId} onChange={(event) => setMachineId(event.target.value)}>
        {!machines.length && <option value="">No machine profiles available</option>}
        {machines.map((machine) => <option value={machine.id} key={machine.id}>{machine.name}</option>)}
      </select></label>
      <Link className="button secondary" to={`/machine-assistant?machine=${machineId}`}>Open Machine Assistant →</Link>
    </div>
    {error && <p role="alert" className="form-error">{error}</p>}
    <div className="documents-grid">
      <form className="panel document-upload" onSubmit={upload}>
        <header><div><span className="eyebrow">Ingest reference</span><h2>Upload document</h2></div></header>
        <div className="panel-body">
          <label>Document title<input required value={title} onChange={(event) => setTitle(event.target.value)} /></label>
          <label>Document type<select value={type} onChange={(event) => setType(event.target.value as DocumentType)}>{types.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
          <label>PDF, TXT, or MD file<input id="manual-file" required type="file" accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>
          <button className="button primary" disabled={busy || !file || !machineId}>{busy ? "Processing document…" : "Upload and process"}</button>
          <p className="field-note">Files remain local. Scanned PDFs require OCR, which is not supported in this phase.</p>
        </div>
      </form>
      <section className="panel">
        <header><div><span className="eyebrow">Transparent lookup</span><h2>Search documents</h2></div></header>
        <form className="document-search" onSubmit={search}><input aria-label="Search machine documents" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search command, requirement, or phrase" /><button className="button secondary">Search</button></form>
        <div className="search-results">{results.map((result) => <Link key={result.chunk_id} to={`/documents/${result.document_id}?page=${result.page_start ?? 1}&highlight=${encodeURIComponent(query)}`}><strong>{result.document_title}</strong><small>Page {result.page_start ?? "—"} · {result.section_title ?? "Unlabeled section"}</small><p>{result.snippet}</p></Link>)}</div>
      </section>
    </div>
    <section className="panel document-library final-document-library">
      <header><div><span className="eyebrow">Selected machine</span><h2>Document library</h2></div><small>{documents.length} documents</small></header>
      {!documents.length ? <div className="compact-empty">No documents uploaded for this machine.</div> :
      <div className="table-wrap"><table><thead><tr><th>Document</th><th>Machine</th><th>Type</th><th>Extraction Status</th><th>AI Use</th><th>Action</th></tr></thead><tbody>{documents.map((item) => <tr key={item.id}><td><strong>{item.title}</strong><small>{item.original_filename}</small>{item.processing_error && <span className="processing-error">{item.processing_error}</span>}</td><td>{machines.find((machine) => machine.id === Number(machineId))?.name || "Selected machine"}</td><td>{item.document_type.replaceAll("_", " ")}</td><td><span className={`document-status ${item.processing_status}`}>{item.processing_status}</span></td><td>{item.ai_post_builder_allowed ? "Reviewed for advisory AI" : "Local / deterministic"}</td><td><div className="document-row-actions"><Link to={`/documents/${item.id}`}>Open</Link><Link to={`/machines/${machineId}/profile-extraction/new`}>Extract Knowledge</Link><Link to={`/machine-assistant?machine=${machineId}`}>Ask Machine Assistant</Link>{item.processing_status === "failed" && <button onClick={() => api.reprocessDocument(item.id).then(() => api.listDocuments(Number(machineId)).then(setDocuments))}>Reprocess</button>}<button className="danger-link" onClick={() => void remove(item)}>Delete</button></div></td></tr>)}</tbody></table></div>}
    </section>
  </section>;
}
