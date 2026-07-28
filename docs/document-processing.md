# Document processing

- Formats: PDF, TXT, Markdown.
- Default limit: 50 MB.
- PDF text and page boundaries are preserved; a malformed page does not abort other pages.
- Image-only PDFs fail with an OCR-required explanation. OCR is not included.
- Chunks target 900 characters with 150-character overlap and never combine separate pages.
- Reprocessing replaces chunks and embeddings.
- Deletion removes database chunks and the controlled local file.

Controls include sanitized display names, generated stored names, path containment, allowed extensions, size checks, non-execution, and React-escaped text. Malware scanning, content disarm, access control, revision control, and encrypted storage remain limitations.

