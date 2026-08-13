import os
import re
from fastapi import HTTPException, status

FILENAME_WHITELIST_REGEX = re.compile(r'[^a-zA-Z0-9_\-\.\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes user-supplied filenames to prevent path traversal, header injection,
    and zip slip vulnerabilities. Retains safe Arabic/Persian and Latin characters.
    """
    if not filename:
        return "document.pdf"
    
    # Take basename only (strip directory paths)
    base = os.path.basename(filename)
    
    # Separate name and extension
    name, ext = os.path.splitext(base)
    if not ext:
        ext = ".pdf"
        
    # Replace dangerous characters with underscore
    clean_name = FILENAME_WHITELIST_REGEX.sub('_', name)
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    
    if not clean_name:
        clean_name = "document"
        
    return f"{clean_name}{ext.lower()}"

def validate_pdf_bytes(content: bytes):
    """
    Validates that uploaded bytes start with the standard PDF magic header (%PDF-).
    """
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file header. Uploaded file is not a valid PDF document."
        )
