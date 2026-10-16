import io

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from claims_assistant.extraction import local_extract, mask_pii
from claims_assistant.main import app
from claims_assistant.review import review_claim

DOCUMENT = b"Claim ID: C-1\nPatient ID: DEMO-1\nDiagnosis: Sprain\nProcedure: X-ray\nAmount: 400.00\nService Date: 2025-08-04\n"


def test_upload_duplicate_and_stats(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("EXTRACTOR_MODE", "demo")
    with TestClient(app) as client:
        first = client.post("/claims", files={"file": ("claim.txt", DOCUMENT)}).json()
        second = client.post("/claims", files={"file": ("claim.txt", DOCUMENT)}).json()
        assert first["fields"]["patient_id"] == "DEMO-1"
        assert first["flags"] == []
        assert [item["code"] for item in second["flags"]] == ["possible_duplicate"]
        assert client.get("/stats").json()["flagged_in_window"] == 1
        assert len(client.get("/claims").json()) == 2


def test_missing_and_invalid():
    result = local_extract("Patient ID: DEMO-1\nAmount: -3\nService Date: 2025-99-99")
    codes = {flag.code for flag in review_claim(result)}
    assert {"missing_diagnosis", "missing_procedure", "invalid_amount", "invalid_date"} <= codes


def test_pii_masking():
    masked, mapping = mask_pii("Patient ID: DEMO-1\nPatient Name: Test User\nEmail: a@b.com")
    assert "DEMO-1" not in masked and "Test User" not in masked and "a@b.com" not in masked
    assert "DEMO-1" in mapping.values()


def test_reject_unsupported_and_empty_pdf(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    stream = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(stream)
    with TestClient(app) as client:
        assert client.post("/claims", files={"file": ("bad.jpg", b"image")}).status_code == 415
        assert client.post("/claims", files={"file": ("scan.pdf", stream.getvalue())}).status_code == 422
