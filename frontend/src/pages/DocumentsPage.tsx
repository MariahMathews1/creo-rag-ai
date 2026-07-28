import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { DocumentType, MachineProfile, SourceDocument } from "../types";

const types: Array<[DocumentType, string]> = [
  ["controller_manual", "Controller manual"],
  ["machine_manual", "Machine manual"],
  ["programming_manual", "Programming manual"],
  ["company_standard", "Company standard"],
  ["approved_program", "Approved reference program"],
  ["setup_document", "Setup document"],
  ["post_processor_document", "Post-processor document"],
  ["operator_manual", "Operator manual"],
  ["specification_document", "Specification document"],
  ["maintenance_manual", "Maintenance manual"],
  ["parameter_list", "Parameter list"],
  ["machine_configuration_document", "Machine configuration document"],
  ["purchase_specification", "Purchase specification"],
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
    <PageHeader eyebrow="Machine knowledge" title="Documents" description="Controlled local reference material for citation-grounded technical answers." />
    <div className="reference-toolbar">
      <label>Machine profile<select value={machineId} onChange={(event) => setMachineId(event.target.value)}>
        {!machines.length && <option value="">No machine profiles available</option>}
        {machines.map((machine) => <option value={machine.id} key={machine.id}>{machine.name}</option>)}
      </select></label>
      <Link className="button secondary" to={`/manual-assistant?machine=${machineId}`}>Open Manual Assistant →</Link>
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
    <section className="panel document-library">
      <header><div><span className="eyebrow">Selected machine</span><h2>Document library</h2></div><small>{documents.length} documents</small></header>
      {!documents.length ? <div className="compact-empty">No documents uploaded for this machine.</div> :
      <div className="document-table">{documents.map((item) => <article key={item.id}>
        <div><span className={`document-status ${item.processing_status}`}>{item.processing_status === "ready" ? "✓" : item.processing_status === "failed" ? "!" : "○"} {item.processing_status}</span><h3><Link to={`/documents/${item.id}`}>{item.title}</Link></h3><p>{item.original_filename} · {item.document_type.replaceAll("_", " ")}</p></div>
        <dl><div><dt>Size</dt><dd>{item.file_size_bytes ? `${Math.ceil(item.file_size_bytes / 1024)} KB` : "—"}</dd></div><div><dt>Pages</dt><dd>{item.page_count ?? "—"}</dd></div><div><dt>Uploaded</dt><dd>{new Date(item.uploaded_at).toLocaleDateString()}</dd></div></dl>
        {item.processing_error && <p className="processing-error">{item.processing_error}</p>}
        <div className="card-actions">{item.processing_status === "failed" && <button onClick={() => api.reprocessDocument(item.id).then(() => api.listDocuments(Number(machineId)).then(setDocuments))}>Reprocess</button>}<button className="danger-link" onClick={() => void remove(item)}>Delete</button></div>
      </article>)}</div>}
    </section>
  </section>;
}
