export function GPostCodeViewer({ code, title = "Generated R&D G-code" }: { code: string; title?: string }) {
  const lines = code.split("\n");
  return <section className="gpost-code-viewer" aria-label={title}>
    <header><h3>{title}</h3><span>{lines.length} lines</span></header>
    <ol>{lines.map((line, index) => <li key={`${index}-${line}`}><code>{line || " "}</code></li>)}</ol>
  </section>;
}
