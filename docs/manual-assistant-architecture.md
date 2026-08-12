# Manual assistant architecture

> **Revised role:** Manual Assistant is internal document Q&A and technical-evidence retrieval. It answers what controlled documentation says about commands, parameters, capabilities, and limits. Its answers are not proof of how the organization's Creo post actually emits G-code and are not a translation-learning corpus.

Multipart uploads are validated, hashed, assigned UUID filenames, and stored beneath `DOCUMENT_STORAGE_PATH`. PDF extraction uses `pypdf` page by page; TXT/MD decoding falls back safely. Page-scoped chunks retain section, page, index, hash, and token estimate.

Chat and embedding providers are independently configured. Mock embeddings are deterministic. Retrieval filters by machine and optional document type, ranks in application code, and applies top-k and minimum-score limits. The answer provider sees only retrieved excerpts; citations are validated against retrieved chunk IDs and stored with the historical answer.

No evidence, invalid citations, forbidden safety claims, or undocumented commands produce `insufficient_evidence`. Manual answers cannot change deterministic findings. OCR, machine connectivity, automatic execution, and autonomous production G-code generation are excluded.
