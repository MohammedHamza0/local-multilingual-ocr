"""
export_service.py
-----------------
Multi-format exporter for extracted PDF text and diagnosis metadata.
Generates .txt, .md, .json, .html, and in-memory .zip files.
Includes HTML escaping in Markdown generator for security against XSS.
"""

import html
import io
import json
import zipfile
from typing import Dict, Any

from app.core.security import sanitize_filename


def generate_txt(diagnosis: Dict[str, Any]) -> str:
    """Generate plain text output for copyable pages."""
    lines = []
    filename = sanitize_filename(diagnosis.get("file", "document.pdf"))
    lines.append(f"DOCUMENT: {filename}")
    lines.append(f"TOTAL PAGES: {diagnosis.get('total_pages', 0)}")
    lines.append(f"OVERALL STATUS: {diagnosis.get('overall', 'UNKNOWN')}")
    lines.append("=" * 60)
    lines.append("")

    for page in diagnosis.get("pages", []):
        verdict = page.get("verdict")
        page_num = page.get("page")
        script = page.get("dominant_script", "unknown")

        if verdict == "COPY":
            lines.append(f"--- PAGE {page_num} [{script.upper()}] ---")
            lines.append(page.get("text", "").strip())
            lines.append("")
        elif verdict == "REVIEW":
            lines.append(f"--- PAGE {page_num} [REVIEW NEEDED] ---")
            lines.append(f"[Note: {page.get('reason')}]")
            lines.append(page.get("text", "").strip())
            lines.append("")
        else:
            lines.append(f"--- PAGE {page_num} [REQUIRES OCR] ---")
            lines.append(f"[Page skipped from plain text output: {page.get('reason')}]")
            lines.append("")

    return "\n".join(lines)


def generate_md(diagnosis: Dict[str, Any]) -> str:
    """
    Generate Markdown output with structure, meta header, and RTL/LTR blocks.
    Escapes HTML entities inside raw text to prevent XSS.
    """
    raw_filename = diagnosis.get("file", "document.pdf")
    filename = html.escape(sanitize_filename(raw_filename))
    lines = []
    lines.append(f"# Extracted Text: {filename}")
    lines.append("")
    lines.append(f"- **Total Pages**: {diagnosis.get('total_pages', 0)}")
    lines.append(f"- **Overall Status**: `{diagnosis.get('overall', 'UNKNOWN')}`")
    lines.append(f"- **Copyable Pages**: {diagnosis.get('page_counts', {}).get('COPY', 0)}")
    lines.append(f"- **OCR Required**: {diagnosis.get('page_counts', {}).get('OCR', 0)}")
    lines.append(f"- **Review Needed**: {diagnosis.get('page_counts', {}).get('REVIEW', 0)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for page in diagnosis.get("pages", []):
        page_num = page.get("page")
        verdict = page.get("verdict")
        direction = page.get("direction", "ltr")
        script = page.get("dominant_script", "unknown")
        raw_text = page.get("text", "").strip()

        lines.append(f"## Page {page_num}")
        lines.append(f"**Verdict**: `{verdict}` | **Script**: `{script.capitalize()}` | **Direction**: `{direction.upper()}`")
        lines.append("")

        if verdict in ("COPY", "REVIEW"):
            if direction == "rtl":
                # Security Fix (S-03): HTML escape text inserted inside div tag
                safe_text = html.escape(raw_text)
                lines.append('<div dir="rtl" style="font-family: Cairo, Tahoma, sans-serif; text-align: right; white-space: pre-wrap; background: #fdfdfd; padding: 15px; border-right: 4px solid #4f46e5; margin-bottom: 20px;">')
                lines.append(safe_text)
                lines.append("</div>")
            else:
                lines.append("```text")
                lines.append(raw_text)
                lines.append("```")
        else:
            lines.append(f"> ⚠️ **Page Requires OCR**: {html.escape(page.get('reason', ''))}")
        lines.append("")

    return "\n".join(lines)


def generate_json(diagnosis: Dict[str, Any]) -> str:
    """Generate clean formatted JSON string."""
    return json.dumps(diagnosis, ensure_ascii=False, indent=2)


def generate_html(diagnosis: Dict[str, Any]) -> str:
    """Generate standalone styled HTML webpage with sidebar navigation and search."""
    raw_filename = diagnosis.get("file", "document.pdf")
    filename = html.escape(sanitize_filename(raw_filename))
    overall = diagnosis.get("overall", "UNKNOWN")
    counts = diagnosis.get("page_counts", {})

    pages_html = []
    nav_html = []

    for page in diagnosis.get("pages", []):
        page_num = page.get("page")
        verdict = page.get("verdict")
        direction = page.get("direction", "ltr")
        script = page.get("dominant_script", "unknown")
        reason = html.escape(page.get("reason", ""))
        text = html.escape(page.get("text", ""))

        verdict_class = "badge-copy" if verdict == "COPY" else ("badge-ocr" if verdict == "OCR" else "badge-review")

        nav_html.append(f'''
            <a href="#page-{page_num}" class="nav-item">
                <span>Page {page_num}</span>
                <span class="badge {verdict_class}">{verdict}</span>
            </a>
        ''')

        if verdict in ("COPY", "REVIEW"):
            body_content = f'''
                <div class="page-text" dir="{direction}">
                    <pre>{text}</pre>
                </div>
            '''
        else:
            body_content = f'''
                <div class="page-notice">
                    <span class="icon">⚠️</span>
                    <p>{reason}</p>
                </div>
            '''

        pages_html.append(f'''
            <div class="page-card" id="page-{page_num}">
                <div class="page-header">
                    <div class="page-title">
                        <h3>Page {page_num}</h3>
                        <span class="badge {verdict_class}">{verdict}</span>
                    </div>
                    <div class="page-meta">
                        <span class="meta-tag">Script: {html.escape(script.capitalize())}</span>
                        <span class="meta-tag">Dir: {direction.upper()}</span>
                    </div>
                </div>
                <div class="page-body">
                    {body_content}
                </div>
            </div>
        ''')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Extracted PDF Document - {filename}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --primary: #6366f1;
            --copy-color: #10b981;
            --ocr-color: #ef4444;
            --review-color: #f59e0b;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', 'Cairo', sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }}
        .sidebar {{
            width: 300px;
            background: #0f172a;
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            padding: 20px;
        }}
        .sidebar-header {{ margin-bottom: 20px; }}
        .sidebar-header h2 {{ font-size: 1.1rem; color: var(--primary); margin-bottom: 5px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; }}
        .sidebar-header p {{ font-size: 0.85rem; color: var(--text-muted); }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 20px;
        }}
        .stat-box {{
            background: var(--card-bg);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid var(--border);
        }}
        .stat-box .num {{ font-size: 1.2rem; font-weight: 700; }}
        .stat-box .label {{ font-size: 0.7rem; color: var(--text-muted); }}
        .nav-list {{
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .nav-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 12px;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text-main);
            text-decoration: none;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}
        .nav-item:hover {{ border-color: var(--primary); transform: translateX(3px); }}
        .main-content {{
            flex: 1;
            overflow-y: auto;
            padding: 30px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}
        .page-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
        }}
        .page-header {{
            padding: 16px 20px;
            background: #182234;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .page-title {{ display: flex; align-items: center; gap: 12px; }}
        .badge {{
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-copy {{ background: rgba(16, 185, 129, 0.2); color: var(--copy-color); border: 1px solid var(--copy-color); }}
        .badge-ocr {{ background: rgba(239, 68, 68, 0.2); color: var(--ocr-color); border: 1px solid var(--ocr-color); }}
        .badge-review {{ background: rgba(245, 158, 11, 0.2); color: var(--review-color); border: 1px solid var(--review-color); }}
        .page-meta {{ display: flex; gap: 8px; }}
        .meta-tag {{ font-size: 0.75rem; color: var(--text-muted); background: var(--bg); padding: 4px 8px; border-radius: 4px; }}
        .page-body {{ padding: 20px; }}
        .page-text pre {{
            white-space: pre-wrap;
            font-family: inherit;
            font-size: 0.95rem;
            line-height: 1.7;
            color: #e2e8f0;
        }}
        .page-text[dir="rtl"] {{ text-align: right; font-family: 'Cairo', sans-serif; }}
        .page-notice {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px dashed var(--ocr-color);
            padding: 20px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 15px;
            color: #fca5a5;
        }}
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>{filename}</h2>
            <p>Overall Status: <strong>{overall}</strong></p>
        </div>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="num" style="color: var(--copy-color);">{counts.get("COPY", 0)}</div>
                <div class="label">Copy</div>
            </div>
            <div class="stat-box">
                <div class="num" style="color: var(--ocr-color);">{counts.get("OCR", 0)}</div>
                <div class="label">OCR</div>
            </div>
            <div class="stat-box">
                <div class="num" style="color: var(--review-color);">{counts.get("REVIEW", 0)}</div>
                <div class="label">Review</div>
            </div>
        </div>
        <div class="nav-list">
            {"".join(nav_html)}
        </div>
    </div>
    <div class="main-content">
        {"".join(pages_html)}
    </div>
</body>
</html>
'''


def generate_zip(diagnosis: Dict[str, Any]) -> bytes:
    """Generate in-memory ZIP file containing .txt, .md, .json, and .html files."""
    raw_filename = diagnosis.get("file", "document.pdf")
    clean_name = sanitize_filename(raw_filename)
    base_name = clean_name.rsplit(".", 1)[0]

    txt_content = generate_txt(diagnosis)
    md_content = generate_md(diagnosis)
    json_content = generate_json(diagnosis)
    html_content = generate_html(diagnosis)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_name}.txt", txt_content)
        zf.writestr(f"{base_name}.md", md_content)
        zf.writestr(f"{base_name}.json", json_content)
        zf.writestr(f"{base_name}.html", html_content)

    return zip_buffer.getvalue()
