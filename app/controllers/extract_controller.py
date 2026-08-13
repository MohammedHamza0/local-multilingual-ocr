import logging
import os
import tempfile
import uuid
from urllib.parse import quote
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import Response

from app.core.config import settings
from app.core.security import sanitize_filename, validate_pdf_bytes
from app.models.session import session_store
from app.services import triage_service, export_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Extraction & Export"])


@router.post("/analyze-and-extract")
async def analyze_and_extract(file: UploadFile = File(...)):
    filename = sanitize_filename(file.filename or "document.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    # Read content in chunks to enforce upload size limit (Security Fix S-02)
    content = bytearray()
    chunk_size = 1024 * 1024  # 1 MB chunk
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed upload size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
            )

    content_bytes = bytes(content)
    validate_pdf_bytes(content_bytes)

    session_id = str(uuid.uuid4())

    # Write to temporary file for Poppler/PyPDF processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content_bytes)
        tmp_path = tmp.name

    try:
        diagnosis = triage_service.diagnose_pdf(tmp_path)
        diagnosis["file"] = filename

        txt_str = export_service.generate_txt(diagnosis)
        md_str = export_service.generate_md(diagnosis)
        json_str = export_service.generate_json(diagnosis)
        html_str = export_service.generate_html(diagnosis)
        zip_bytes = export_service.generate_zip(diagnosis)

        # Store in thread-safe, bounded SessionStore (Refactor R-02 & Memory Protection)
        session_store.set(session_id, {
            "filename": filename,
            "diagnosis": diagnosis,
            "txt": txt_str,
            "md": md_str,
            "json": json_str,
            "html": html_str,
            "zip": zip_bytes
        })

        return {
            "session_id": session_id,
            "filename": filename,
            "diagnosis": diagnosis,
            "previews": {
                "txt": txt_str[:5000],
                "md": md_str[:5000],
                "json": json_str[:5000],
                "html": html_str
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF {filename}: {str(e)}", exc_info=True)
        # Security Fix S-05: Return generic client error message without leaking internal paths
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the PDF document."
        )
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@router.get("/download/{session_id}/{export_format}")
async def download_format(session_id: str, export_format: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session expired or not found."
        )

    filename = sanitize_filename(session["filename"])
    base_name = os.path.splitext(filename)[0]
    quoted_base_name = quote(base_name)
    export_format = export_format.lower()

    if export_format == "txt":
        return Response(
            content=session["txt"],
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted_base_name}.txt"}
        )
    elif export_format == "md":
        return Response(
            content=session["md"],
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted_base_name}.md"}
        )
    elif export_format == "json":
        return Response(
            content=session["json"],
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted_base_name}.json"}
        )
    elif export_format == "html":
        return Response(
            content=session["html"],
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted_base_name}.html"}
        )
    elif export_format == "zip":
        return Response(
            content=session["zip"],
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted_base_name}_extracted.zip"}
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid export format requested."
        )
