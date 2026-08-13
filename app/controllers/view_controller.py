import os
from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(tags=["View Controller"])

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

@router.get("/")
async def read_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Multilingual PDF Triage & Text Extractor API is Running</h1>")
