from app.core.config import get_settings
from app.documents.answering import GroundedAnswer, validate_grounded_answer
from app.documents.embeddings import MockEmbeddingProvider
from app.documents.retrieval import RetrievedChunk, retrieve
from app.models.entities import DocumentType


def upload_manual(client, machine_id, tmp_path, content=None, document_type="controller_manual"):
    settings = get_settings()
    settings.document_storage_path = str(tmp_path / "manuals")
    settings.max_document_upload_mb = 50
    settings.ai_provider = "mock"
    settings.embedding_provider = "mock"
    settings.retrieval_min_score = 0.20
    text = content or (
        b"# G84 Rigid Tapping\n\nG84 commands rigid tapping when the fictional "
        b"controller synchronization option is enabled. G80 cancels G84."
    )
    return client.post(
        f"/api/machines/{machine_id}/documents",
        data={"title": "Fictional Controller Manual", "document_type": document_type},
        files={"file": ("manual.md", text, "text/markdown")},
    ).json()


def test_grounded_question_citations_storage_and_insufficient_evidence(
    client, machine_profile, tmp_path
):
    document = upload_manual(client, machine_profile.id, tmp_path)
    session = client.post(
        "/api/manual-sessions",
        json={"machine_profile_id": machine_profile.id, "title": "Cycle questions"},
    ).json()
    supported = client.post(
        f"/api/manual-sessions/{session['id']}/questions",
        json={"question": "Does this controller support G84 rigid tapping?"},
    )
    assert supported.status_code == 201
    answer = supported.json()
    assert answer["answer_status"] == "answered"
    assert answer["citations"][0]["document_id"] == document["id"]
    assert "[1]" in answer["answer"]
    assert "rigid tapping" in answer["answer"].lower()
    assert answer["advisory_only"] is True
    assert answer["grounded_in_uploaded_documents"] is True
    assert answer["production_approval_required"] is True
    assert "production ready" not in answer["answer"].lower()

    stored = client.get(f"/api/manual-questions/{answer['id']}").json()
    assert stored["citations"] == answer["citations"]

    unsupported = client.post(
        f"/api/manual-sessions/{session['id']}/questions",
        json={"question": "What laser probing cycle is installed?"},
    ).json()
    assert unsupported["answer_status"] == "insufficient_evidence"
    assert unsupported["citations"] == []


def test_command_explanation_normalizes_g1_and_preserves_context(
    client, machine_profile, tmp_path
):
    upload_manual(
        client, machine_profile.id, tmp_path,
        b"# G01 Linear Interpolation\n\nG01 performs linear feed motion using F.",
        "programming_manual",
    )
    response = client.post(
        f"/api/machines/{machine_profile.id}/explain-command",
        json={"command": "g1", "context": "g1 x1.0 f10.0"},
    )
    assert response.status_code == 200
    assert "G01" in response.json()["question"]
    assert "g1 x1.0 f10.0" in response.json()["question"]


def test_undocumented_command_is_insufficient(client, machine_profile, tmp_path):
    upload_manual(client, machine_profile.id, tmp_path)
    response = client.post(
        f"/api/machines/{machine_profile.id}/explain-command",
        json={"command": "G65", "context": "G65 P9000"},
    )
    assert response.json()["answer_status"] == "insufficient_evidence"


def test_invalid_citation_markers_fail_closed():
    evidence = [
        RetrievedChunk(1, "Manual", "controller_manual", 10, 1, 1, "G84", "G84 rigid tapping.", 0.9)
    ]
    answer = GroundedAnswer("answered", "G84 rigid tapping. [2]", [10], [])
    validated = validate_grounded_answer(answer, evidence)
    assert validated.answer_status == "insufficient_evidence"
    assert validated.cited_chunk_ids == []


def test_conflicting_documents_fail_closed(client, machine_profile, tmp_path):
    upload_manual(
        client,
        machine_profile.id,
        tmp_path,
        b"# G84\nG84 is supported and commands rigid tapping.",
    )
    upload_manual(
        client,
        machine_profile.id,
        tmp_path,
        b"# G84 restriction\nG84 rigid tapping is not supported.",
        "company_standard",
    )
    get_settings().retrieval_min_score = 0.0
    session = client.post(
        "/api/manual-sessions",
        json={"machine_profile_id": machine_profile.id, "title": "Conflict"},
    ).json()
    answer = client.post(
        f"/api/manual-sessions/{session['id']}/questions",
        json={"question": "Is G84 rigid tapping supported?"},
    ).json()
    assert answer["answer_status"] == "insufficient_evidence"
    assert "conflicting" in answer["unresolved_questions"][0].lower()


def test_retrieval_filters_top_k_threshold_and_citation_metadata(
    client, db_session, machine_profile, tmp_path
):
    document = upload_manual(client, machine_profile.id, tmp_path)
    settings = get_settings()
    settings.retrieval_top_k = 1
    settings.retrieval_min_score = 0.0
    results, _ = retrieve(
        db_session,
        machine_profile.id,
        "G84 rigid tapping",
        MockEmbeddingProvider(),
        settings,
    )
    assert len(results) == 1
    assert results[0].document_id == document["id"]
    assert results[0].page_start == 1

    filtered, _ = retrieve(
        db_session,
        machine_profile.id,
        "G84 rigid tapping",
        MockEmbeddingProvider(),
        settings,
        [DocumentType.COMPANY_STANDARD],
    )
    assert filtered == []
    other_machine, _ = retrieve(
        db_session, 999, "G84 rigid tapping", MockEmbeddingProvider(), settings
    )
    assert other_machine == []
    settings.retrieval_min_score = 1.0
    below_threshold, _ = retrieve(
        db_session,
        machine_profile.id,
        "G84 rigid tapping",
        MockEmbeddingProvider(),
        settings,
    )
    assert below_threshold == []
