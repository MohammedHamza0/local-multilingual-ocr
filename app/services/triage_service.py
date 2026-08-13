"""
triage_service.py
-----------------
Enhanced Multilingual Pre-OCR Triage Engine for PDF documents.
Inspects PDF structure, fonts, ToUnicode CMap, encryption permissions,
character sanity, dominant language script, and reading direction (RTL vs LTR).
"""

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from pypdf import PdfReader

from app.models.diagnosis import PageVerdict
from app.services.normalization_service import clean_arabic_persian_text

UNICODE_RANGES = {
    "arabic": [
        (0x0600, 0x06FF),  # Arabic / Persian / Urdu
        (0x0750, 0x077F),  # Arabic Supplement
        (0x08A0, 0x08FF),  # Arabic Extended-A
        (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
    ],
    "latin": [
        (0x0041, 0x005A),  # Basic Latin uppercase
        (0x0061, 0x007A),  # Basic Latin lowercase
        (0x00C0, 0x024F),  # Latin Supplement & Extended
    ],
    "cyrillic": [(0x0400, 0x04FF)],
    "hebrew": [(0x0590, 0x05FF)],
    "cjk": [(0x4E00, 0x9FFF)],
    "devanagari": [(0x0900, 0x097F)],
    "greek": [(0x0370, 0x03FF)],
}

GARBLED_RANGES = [
    (0xE000, 0xF8FF),   # Private Use Area -> classic "glyph with no ToUnicode"
    (0xFFFD, 0xFFFD),   # Replacement character
]

RTL_SCRIPTS = {"arabic", "hebrew"}


def _in_ranges(cp: int, ranges: List[tuple]) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def _find_poppler_tool(name: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    appdata_local = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    for candidate in appdata_local.glob(f"**/{name}.exe"):
        return str(candidate)
    return name


def analyze_char_ratios(text: str) -> Dict[str, Any]:
    """Calculate script ratios, garbled ratio, space ratio, dominant script, and direction."""
    letters = [c for c in text if c.isalpha()]
    total_letters = len(letters) or 1

    script_counts = {}
    for script_name, ranges in UNICODE_RANGES.items():
        count = sum(1 for c in letters if _in_ranges(ord(c), ranges))
        script_counts[script_name] = count

    script_ratios = {k: v / total_letters for k, v in script_counts.items()}

    dominant_script = "unknown"
    max_ratio = 0.0
    for script_name, ratio in script_ratios.items():
        if ratio > max_ratio and ratio >= 0.10:
            max_ratio = ratio
            dominant_script = script_name

    direction = "rtl" if dominant_script in RTL_SCRIPTS else "ltr"

    garbled_count = sum(1 for c in text if _in_ranges(ord(c), GARBLED_RANGES))
    non_space_count = len(text.replace(" ", "").replace("\n", "")) or 1
    garbled_ratio = garbled_count / non_space_count
    space_ratio = text.count(" ") / max(len(text), 1)

    return {
        "dominant_script": dominant_script,
        "direction": direction,
        "script_ratios": script_ratios,
        "arabic_ratio": script_ratios["arabic"],
        "latin_ratio": script_ratios["latin"],
        "garbled_ratio": garbled_ratio,
        "space_ratio": space_ratio,
        "char_count": len(text),
        "letter_count": len(letters),
    }


def run_pdffonts(pdf_path: str) -> List[Dict[str, Any]]:
    """Run pdffonts to extract font embedding and ToUnicode information."""
    tool = _find_poppler_tool("pdffonts")
    try:
        out = subprocess.run([tool, pdf_path], capture_output=True, text=True, encoding="utf-8", errors="replace")
        fonts = []
        for line in out.stdout.splitlines()[2:]:
            parts = line.split()
            if len(parts) < 7:
                continue
            fonts.append({
                "name": parts[0],
                "type": parts[1],
                "encoding": parts[2],
                "embedded": parts[3] == "yes",
                "subset": parts[4] == "yes",
                "has_unicode_map": parts[5] == "yes",
            })
        return fonts
    except Exception:
        return []


def extract_page_text(pdf_path: str, page_num_1indexed: int, use_layout: bool = False) -> str:
    """Extract text for a single page via pdftotext or pypdf spatial visitor fallback."""
    tool = _find_poppler_tool("pdftotext")
    cmd = [tool, "-f", str(page_num_1indexed), "-l", str(page_num_1indexed)]
    if use_layout:
        cmd.append("-layout")
    cmd.extend([pdf_path, "-"])

    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        raw_text = out.stdout
    except Exception:
        raw_text = ""

    if not raw_text.strip() and not use_layout:
        try:
            cmd_fallback = [tool, "-layout", "-f", str(page_num_1indexed), "-l", str(page_num_1indexed), pdf_path, "-"]
            out_fb = subprocess.run(cmd_fallback, capture_output=True, text=True, encoding="utf-8", errors="replace")
            raw_text = out_fb.stdout
        except Exception:
            raw_text = ""

    if not raw_text.strip():
        try:
            reader = PdfReader(pdf_path)
            if page_num_1indexed <= len(reader.pages):
                page = reader.pages[page_num_1indexed - 1]
                text_chunks = []
                def visitor_body(text, cm, tm, font_dict, font_size):
                    if text and text.strip():
                        x = tm[4] if tm and len(tm) >= 6 else 0
                        y = tm[5] if tm and len(tm) >= 6 else 0
                        text_chunks.append((y, x, text))
                page.extract_text(visitor_text=visitor_body)
                text_chunks.sort(key=lambda item: (-round(item[0] / 5.0), -item[1]))
                lines = []
                line_buf = []
                cur_y = None
                for y, x, txt in text_chunks:
                    c = round(y / 5.0)
                    if cur_y is None:
                        cur_y = c
                    if c != cur_y:
                        lines.append(" ".join(line_buf))
                        line_buf = [txt]
                        cur_y = c
                    else:
                        line_buf.append(txt)
                if line_buf:
                    lines.append(" ".join(line_buf))
                raw_text = "\n".join(lines)
        except Exception:
            pass

    return raw_text


def check_extraction_permission(pdf_path: str) -> bool:
    """Returns False if PDF security settings explicitly forbid text extraction."""
    try:
        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return False
        perms = reader.trailer.get("/Encrypt")
        if perms is None:
            return True
        p = perms.get("/P")
        if p is None:
            return True
        p_int = int(p)
        return bool(p_int & (1 << 4))
    except Exception:
        return True


def diagnose_page(pdf_path: str, page_index: int, page_text: str, doc_fonts: list) -> PageVerdict:
    stripped = page_text.strip()
    page_num = page_index + 1

    if not stripped:
        return PageVerdict(
            page=page_num,
            verdict="OCR",
            reason="No extractable text on this page (scanned or raster image).",
            dominant_script="unknown",
            direction="ltr",
            metrics={},
            text=""
        )

    analysis = analyze_char_ratios(stripped)
    dom_script = analysis["dominant_script"]
    direction = analysis["direction"]

    if analysis["garbled_ratio"] > 0.02:
        return PageVerdict(
            page=page_num,
            verdict="OCR",
            reason=f"{analysis['garbled_ratio']:.1%} of characters are replacement or Private Use Area symbols -> broken ToUnicode mapping.",
            dominant_script=dom_script,
            direction=direction,
            metrics=analysis,
            text=stripped
        )

    unmapped_fonts = [f for f in doc_fonts if not f["has_unicode_map"] and f["embedded"]]
    if unmapped_fonts and dom_script == "unknown" and analysis["char_count"] > 15:
        return PageVerdict(
            page=page_num,
            verdict="OCR",
            reason=f"Embedded font(s) without ToUnicode CMap ({', '.join(f['name'] for f in unmapped_fonts[:3])}) and text does not match standard scripts.",
            dominant_script=dom_script,
            direction=direction,
            metrics=analysis,
            text=stripped
        )

    if dom_script == "unknown" and analysis["char_count"] > 20:
        return PageVerdict(
            page=page_num,
            verdict="REVIEW",
            reason="Text extracted but no known script dominates — could be unmapped glyphs or rare symbols. Manual review recommended.",
            dominant_script=dom_script,
            direction=direction,
            metrics=analysis,
            text=stripped
        )

    if analysis["space_ratio"] < 0.03 and analysis["char_count"] > 50:
        return PageVerdict(
            page=page_num,
            verdict="REVIEW",
            reason="Extremely low whitespace ratio — words might be glued together due to per-glyph absolute coordinates.",
            dominant_script=dom_script,
            direction=direction,
            metrics=analysis,
            text=stripped
        )

    cleaned_text = clean_arabic_persian_text(page_text)
    return PageVerdict(
        page=page_num,
        verdict="COPY",
        reason=f"Clean text layer detected. Dominant script: {dom_script.capitalize()} ({direction.upper()}).",
        dominant_script=dom_script,
        direction=direction,
        metrics=analysis,
        text=cleaned_text
    )


def diagnose_pdf(pdf_path: str) -> Dict[str, Any]:
    pdf_path_str = str(pdf_path)
    fonts = run_pdffonts(pdf_path_str)
    extraction_allowed = check_extraction_permission(pdf_path_str)

    try:
        reader = PdfReader(pdf_path_str)
        n_pages = len(reader.pages)
    except Exception:
        n_pages = 0

    pages: List[PageVerdict] = []

    if n_pages == 0:
        overall = "ERROR"
    elif not fonts and n_pages > 0:
        pages = [
            PageVerdict(
                page=i + 1,
                verdict="OCR",
                reason="No embedded fonts present in PDF -> page is scanned raster image.",
                dominant_script="unknown",
                direction="ltr",
                metrics={},
                text=""
            ) for i in range(n_pages)
        ]
    else:
        for i in range(n_pages):
            try:
                raw_text = extract_page_text(pdf_path_str, i + 1, use_layout=False)
            except Exception:
                raw_text = ""
            pages.append(diagnose_page(pdf_path_str, i, raw_text, fonts))

    if not extraction_allowed:
        for p in pages:
            p.verdict = "OCR"
            p.reason = "Document permissions forbid text extraction (encryption /P flag). " + p.reason

    counts = {"COPY": 0, "OCR": 0, "REVIEW": 0}
    for p in pages:
        if p.verdict in counts:
            counts[p.verdict] += 1

    if counts["OCR"] == 0 and counts["REVIEW"] == 0:
        overall = "COPY_ALL"
    elif counts["COPY"] == 0:
        overall = "OCR_ALL"
    else:
        overall = "MIXED"

    return {
        "file": Path(pdf_path_str).name,
        "total_pages": n_pages,
        "overall": overall,
        "page_counts": counts,
        "fonts": fonts,
        "extraction_permitted": extraction_allowed,
        "pages": [p.to_dict() for p in pages],
    }
