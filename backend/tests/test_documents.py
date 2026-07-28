from pathlib import Path

from app.core.config import get_settings
from app.documents.chunking import chunk_pages
from app.documents.embeddings import MockEmbeddingProvider
from app.documents.extractors.base import ExtractedPage, ExtractionError
from app.documents.extractors.pdf_extractor import PDFExtractor


def configure_storage(tmp_path):
    settings = get_settings()
    settings.document_storage_path = str(tmp_path / "documents")
    settings.max_document_upload_mb = 1
    settings.retrieval_min_score = 0.30
    settings.ai_provider = "mock"
    settings.embedding_provider = "mock"
    return settings


def test_markdown_upload_processing_duplicate_search_and_delete(
    client, machine_profile, tmp_path
):
    settings = configure_storage(tmp_path)
    content = (
        b"# FICTIONAL SAMPLE DOCUMENT\n\n## G84 Rigid Tapping\n"
        b"G84 performs rigid tapping when spindle synchronization is enabled. "
        b"G80 cancels the cycle."
    )
    response = client.post(
        f"/api/machines/{machine_profile.id}/documents",
        data={"title": "Controller Manual", "document_type": "controller_manual"},
        files={"file": ("manual.md", content, "text/markdown")},
    )
    assert response.status_code == 201
    document = response.json()
    assert document["processing_status"] == "ready"
    stored_files = list(settings.document_storage_dir.glob("*"))
    assert len(stored_files) == 1
    assert stored_files[0].name != "manual.md"

    duplicate = client.post(
        f"/api/machines/{machine_profile.id}/documents",
        data={"title": "Duplicate", "document_type": "controller_manual"},
        files={"file": ("../manual.md", content, "text/markdown")},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["existing_document_id"] == document["id"]

    result = client.get(
        f"/api/machines/{machine_profile.id}/documents/search", params={"q": "G84"}
    )
    assert result.status_code == 200
    assert result.json()[0]["page_start"] == 1

    assert client.delete(f"/api/documents/{document['id']}").status_code == 204
    assert not list(settings.document_storage_dir.glob("*"))


def test_txt_upload_and_content(client, machine_profile, tmp_path):
    configure_storage(tmp_path)
    response = client.post(
        f"/api/machines/{machine_profile.id}/documents",
        data={"title": "Standard", "document_type": "company_standard"},
        files={"file": ("standard.txt", b"G49 is required before M30.", "text/plain")},
    )
    assert response.status_code == 201
    content = client.get(f"/api/documents/{response.json()['id']}/content").json()
    assert content["pages"][0]["page_number"] == 1
    assert content["chunks"][0]["content_hash"]


def test_upload_validation(client, machine_profile, tmp_path):
    settings = configure_storage(tmp_path)
    unsupported = client.post(
        f"/api/machines/{machine_profile.id}/documents",
        data={"title": "Bad", "document_type": "other"},
        files={"file": ("bad.exe", b"no", "application/octet-stream")},
    )
    assert unsupported.status_code == 422
    empty = client.post(
        f"/api/machines/{machine_profile.id}/documents",
        data={"title": "Empty", "document_type": "other"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty.status_code == 422
    settings.max_document_upload_mb = 0
    oversized = client.post(
        f"/api/machines/{machine_profile.id}/documents",
        data={"title": "Large", "document_type": "other"},
        files={"file": ("large.txt", b"x", "text/plain")},
    )
    assert oversized.status_code == 422
    missing = client.post(
        "/api/machines/999/documents",
        data={"title": "Missing", "document_type": "other"},
        files={"file": ("file.txt", b"text", "text/plain")},
    )
    assert missing.status_code == 404


def test_chunking_preserves_page_overlap_heading_order_and_hashes():
    pages = [
        ExtractedPage(1, "# G84 Rigid Tapping\n\n" + "Parameter details. " * 30, 570),
        ExtractedPage(2, "SECOND PAGE\n\nCancellation uses G80.", 36),
    ]
    chunks = chunk_pages(pages, target_size=180, overlap=30)
    assert chunks
    assert [item.chunk_index for item in chunks] == list(range(len(chunks)))
    assert chunks[0].page_start == chunks[0].page_end == 1
    assert chunks[-1].page_start == 2
    assert chunks[0].section_title == "G84 Rigid Tapping"
    assert all(item.content and len(item.content_hash) == 64 for item in chunks)
    assert chunks[0].content[-20:] in chunks[1].content or len(chunks[0].content) < 180


def test_mock_embeddings_are_deterministic():
    provider = MockEmbeddingProvider()
    assert provider.embed_texts(["G84 rigid tapping"]) == provider.embed_texts(
        ["G84 rigid tapping"]
    )
    assert provider.embed_texts(["G84"])[0] != provider.embed_texts(["M06"])[0]


def test_pdf_no_text_reports_ocr_requirement(monkeypatch, tmp_path):
    class Page:
        def extract_text(self):
            return ""
    class Reader:
        pages = [Page()]
    monkeypatch.setattr("app.documents.extractors.pdf_extractor.PdfReader", lambda _: Reader())
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF")
    try:
        PDFExtractor().extract(path)
        assert False, "Expected extraction failure"
    except ExtractionError as exc:
        assert "OCR" in str(exc)


def test_pdf_extracts_text_with_page_metadata(monkeypatch, tmp_path):
    class Page:
        def extract_text(self):
            return "G84 commands rigid tapping."

    class Reader:
        pages = [Page()]

    monkeypatch.setattr(
        "app.documents.extractors.pdf_extractor.PdfReader", lambda _: Reader()
    )
    path = tmp_path / "controller.pdf"
    path.write_bytes(b"%PDF")
    pages = PDFExtractor().extract(path)
    assert pages[0].page_number == 1
    assert pages[0].text == "G84 commands rigid tapping."


def test_pdf_upload_ready_and_processing_failure_status(
    client, machine_profile, monkeypatch, tmp_path
):
    configure_storage(tmp_path)
    monkeypatch.setattr(
        PDFExtractor,
        "extract",
        lambda self, path: [ExtractedPage(1, "G84 commands rigid tapping.", 27)],
    )
    ready = client.post(
        f"/api/machines/{machine_profile.id}/documents",
        data={"title": "PDF Manual", "document_type": "controller_manual"},
        files={"file": ("manual.pdf", b"%PDF-valid-test", "application/pdf")},
    )
    assert ready.status_code == 201
    assert ready.json()["processing_status"] == "ready"
    assert ready.json()["page_count"] == 1

    def fail_extract(self, path):
        raise ExtractionError("No extractable text was found. OCR may be required.")

    monkeypatch.setattr(PDFExtractor, "extract", fail_extract)
    failed = client.post(
        f"/api/machines/{machine_profile.id}/documents",
        data={"title": "Scanned PDF", "document_type": "machine_manual"},
        files={"file": ("scan.pdf", b"%PDF-scanned-test", "application/pdf")},
    )
    assert failed.status_code == 201
    assert failed.json()["processing_status"] == "failed"
    assert "OCR" in failed.json()["processing_error"]
