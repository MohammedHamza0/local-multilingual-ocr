import pytest
from app.services.normalization_service import (
    clean_arabic_persian_text,
    normalize_quranic_and_hadith_quotes,
)
from app.services.triage_service import analyze_char_ratios


def test_bidi_control_stripping():
    # Includes left-to-right & right-to-left mark controls \u200e and \u200f
    sample = "اختبار\u200e \u200fالنص العربي"
    cleaned = clean_arabic_persian_text(sample)
    assert "\u200e" not in cleaned
    assert "\u200f" not in cleaned
    assert cleaned == "اختبار النص العربي"


def test_quote_normalization():
    sample = "«كُّل فرزندانشان هستند لذا پیامبر فرموده است ُول َعْن»"
    normalized = normalize_quranic_and_hadith_quotes(sample)
    assert "كُلُّكُمْ رَاعٍ وَكُلُّكُمْ مَسْئُولٌ عَنْ رَعِيَّتِهِ" in normalized


def test_script_ratios_arabic():
    text = "بسم الله الرحمن الرحيم هذا نص عربي خالص"
    ratios = analyze_char_ratios(text)
    assert ratios["dominant_script"] == "arabic"
    assert ratios["direction"] == "rtl"
    assert ratios["arabic_ratio"] > 0.8


def test_script_ratios_latin():
    text = "Hello world this is a pure english text sample"
    ratios = analyze_char_ratios(text)
    assert ratios["dominant_script"] == "latin"
    assert ratios["direction"] == "ltr"
    assert ratios["latin_ratio"] > 0.8
