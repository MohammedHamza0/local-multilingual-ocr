import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_read_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_upload_non_pdf_fails():
    file_bytes = b"Hello world text content"
    files = {"file": ("test.txt", io.BytesIO(file_bytes), "text/plain")}
    response = client.post("/api/analyze-and-extract", files=files)
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


def test_upload_invalid_pdf_header_fails():
    file_bytes = b"NOT_A_PDF_CONTENT"
    files = {"file": ("test.pdf", io.BytesIO(file_bytes), "application/pdf")}
    response = client.post("/api/analyze-and-extract", files=files)
    assert response.status_code == 400
    assert "Invalid PDF file header" in response.json()["detail"]


def test_cors_headers():
    response = client.get("/", headers={"Origin": "http://localhost:8000"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8000"
