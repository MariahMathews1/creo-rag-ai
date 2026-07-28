# Retrieval and citations

Serialized embedding vectors live in SQLite; similarity and keyword ranking run in application code. Defaults are top 6 and a 0.30 threshold. Retrieval always filters by machine and may filter by document type.

Citation markers and cited IDs must map to retrieved chunks. Stored citation snapshots retain excerpts and page metadata. Missing, conflicting, or weak evidence produces `insufficient_evidence`.

The deterministic hash embedder is suitable for local tests, not production semantics. Extraction quality, printed-versus-PDF page numbering, incomplete manuals, and retrieval ranking remain known RAG limitations.

