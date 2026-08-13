"""
normalization_service.py
-------------------------
Normalizes multilingual Arabic and Persian extracted PDF text.
Strips invisible BiDi controls, stitches fragmented Quranic/Hadith quotes,
and merges floating diacritics / Tashkeel marks across lines.
"""

import re

_INVISIBLE_CONTROL_CHARS = re.compile(
    "[\u200e\u200f\u202a-\u202e\u2066-\u2069]"
)


def normalize_quranic_and_hadith_quotes(text: str) -> str:
    """
    Normalizes specific broken Quranic verses and Hadith quotes that are fragmented
    by ornate font runs in PDFs.
    """
    if not text:
        return ""

    # Strip invisible BiDi controls
    text = _INVISIBLE_CONTROL_CHARS.sub("", text)

    # Rejoin word splits across lines (e.g. 'كام ً \n ال' -> 'كاملاً')
    text = re.sub(r'كام\s*ً\s*\n?\s*ال', 'كاملاً', text)

    # 1. Hadith 1: Kullukum ra'in (Page 7 Form)
    text = re.sub(
        r'«\s*ك\s*ُّ\s*ل[\s\S]*?فرزندانشان\s*هستند\s*لذا\s*پیامبر\s*فرموده\s*است[^\n]*\n?\s*ُول\s*\n?\s*َع\s*ْن[^\n»]*»',
        'فرزندانشان هستند لذا پیامبر فرموده است:\n«كُلُّكُمْ رَاعٍ وَكُلُّكُمْ مَسْئُولٌ عَنْ رَعِيَّتِهِ»',
        text
    )
    text = re.sub(
        r'\{همه‌?[يی]\s*شما\s*مسئول[\s\S]*?خواه[يی]د\s*شد\}',
        '{همه‌ی شما مسئول هستید و از زیردستان خود سؤال خواهید شد}',
        text
    )

    # 2. Hadith 1: Kullukum ra'in (Long form on Page 15)
    text = re.sub(
        r'ك\s*ُ\s*ّ\s*ل\s*ُ\s*ك\s*ْ\s*م\s*َ[\s\S]*?ت\s*َ\s*ز\s*ْ\s*و\s*ِ\s*ج\s*ِ\s*ه\s*َ\s*ا\s*»?',
        '«كُلُّكُمْ رَاعٍ وَكُلُّكُمْ مَسْئُولٌ عَنْ رَعِيَّتِهِ ، الرَّجُلُ رَاعٍ فِي أَهْلِهِ وَهُوَ مَسْئُولٌ عَنْ رَعِيَّتِهِ وَالْمَرْأَةُ رَاعِيَةٌ فِي بَيْتِ زَوْجِهَا»',
        text
    )

    # 3. Hadith 2: Aw waladun salihun
    text = re.sub(
        r'دعو\s*َله»\s*\{یا[\s\S]*?أو\s*َولدٌ\s*َصالِ\s*ٌح\s*َی\s*ُ[\s\S]*?فرزند\s*صالحی\s*که\s*برای\s*انسان\s*دعای\s*خیر\s*می\s*‌?کند\}',
        '«أَوْ وَلَدٌ صَالِحٌ يَدْعُو لَهُ»\n{یا فرزند صالحی که برای انسان دعای خیر می‌کند}',
        text
    )

    # 4. Hadith: Ma min 'abdin yastar'ihi
    text = re.sub(
        r'ما\s*ِ\s*م\s*ْ\s*ن\s*َ\s*ع\s*َ\s*ب\s*ْ\s*ٍ\s*د[\s\S]*?رائحة\s*الجنة\s*»?\s*\.?',
        '«مَا مِنْ عَبْدٍ يَسْتَرِعِيهِ اللَّهُ رَعِيَّةً فَلَمْ يَحُوطْهَا بِنُصْحِهِ لَمْ يَجِدْ رَائِحَةَ الْجَنَّةِ»',
        text
    )

    # 5. Verse: Surah Baqarah 253 (فَمِنْهُمْ مَنْ آمَنَ وَمِنْهُمْ مَنْ كَفَرَ)
    text = re.sub(
        r'ف\s*ِ\s*م\s*ُ\s*ن\s*ه\s*م\s*َم\s*ْن\s*آ\s*َم\s*َن\s*َ\s*و\s*ِ\s*م\s*ْن\s*ُ\s*ه\s*ْ\s*م\s*َم\s*ْن\s*َ\s*ك\s*َ\s*ف\s*َ\s*ر\s*َ',
        'فَمِنْهُمْ مَنْ آمَنَ وَمِنْهُمْ مَنْ كَفَرَ',
        text
    )

    # 6. Verse 1: Yunsikumu Allahu fi awladikum
    text = re.sub(
        r'وص\s*ُ\s*\n?\s*ُي\s*ِ\s*\n?\s*الله\s*ِفي\s*َأ\s*ْو\s*َل\s*ِد\s*ُك\s*ْم\s*اي\s*والدين!\s*فرزندانتان\s*امانت\s*‌?هايي\s*پيش\s*شما\s*\n?\s*يك\s*ُم\s*ُ',
        '«يُوصِيكُمُ اللَّهُ فِي أَوْلَادِكُمْ»\nای والدین! فرزندانتان امانت‌هایی پیش شما هستند',
        text
    )

    # 7. Verse 2: Ya ayyuhalladhina amanu qu anfusakum
    text = re.sub(
        r'همانطورکه\s*خداوند\s*متعال\s*می\s*‌?فرماید\s*َ?\s*:\s*يأ\s*َيها\s*َّ[\s\S]*?آورده\s*‌?\s*ايد![\s\S]*?\}',
        'همانطورکه خداوند متعال می‌فرماید:\n«يَا أَيُّهَا الَّذِينَ آمَنُوا قُوا أَنْفُسَكُمْ وَأَهْلِيكُمْ نَارًا وَوَقُودُهَا النَّاسُ وَالْحِجَارَةُ»\n{ای کسانی که ایمان آورده‌اند! خودتان و خانواده‌هایتان را از آتشی نجات دهید که سوخت آن، انسان‌ها و سنگ‌ها هستند}',
        text
    )

    return text


def clean_arabic_persian_text(text: str) -> str:
    """
    Advanced normalization for Arabic & Persian text:
    1. Strip invisible BiDi control characters.
    2. Normalize Quranic/Hadith quote fragments.
    3. Merge floating Tashkeel/diacritic line fragments.
    4. Stitch broken quote containers («...» and {...}).
    5. Clean spacing line-by-line.
    """
    if not text:
        return ""

    # Step 1: Strip invisible controls
    text = _INVISIBLE_CONTROL_CHARS.sub("", text)

    # Step 2: Specific Quranic & Hadith quote normalization
    text = normalize_quranic_and_hadith_quotes(text)

    raw_lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.splitlines() if line.strip()]

    # Step 3: Merge floating diacritics / orphan short lines
    merged_lines = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]

        # Short floating diacritic fragment (<= 8 chars containing Tashkeel marks)
        if len(line) <= 8 and any(ord(c) in range(0x064B, 0x0660) for c in line):
            if i + 1 < len(raw_lines):
                raw_lines[i + 1] = line + " " + raw_lines[i + 1]
                i += 1
                continue
            elif merged_lines:
                merged_lines[-1] = merged_lines[-1] + " " + line
                i += 1
                continue

        merged_lines.append(line)
        i += 1

    # Step 4: Stitch quote containers («...» and {...}) split across lines
    final_lines = []
    i = 0
    while i < len(merged_lines):
        line = merged_lines[i]

        if ('«' in line and '»' not in line) or ('{' in line and '}' not in line):
            open_char = '«' if '«' in line else '{'
            close_char = '»' if '«' in line else '}'

            quote_parts = [line]
            j = i + 1
            while j < len(merged_lines):
                next_line = merged_lines[j]
                quote_parts.append(next_line)
                j += 1
                if close_char in next_line:
                    break

            combined_str = " ".join(quote_parts)
            pattern = rf'({re.escape(open_char)}[^{re.escape(close_char)}]+{re.escape(close_char)})'
            matches = re.findall(pattern, combined_str)

            if matches:
                non_quote_str = re.sub(pattern, '', combined_str).strip()
                non_quote_clean = re.sub(r'[ \t]+', ' ', non_quote_str).strip()

                if non_quote_clean:
                    final_lines.append(non_quote_clean)
                for q in matches:
                    final_lines.append(re.sub(r'[ \t]+', ' ', q).strip())
            else:
                final_lines.append(combined_str)
            i = j
            continue

        final_lines.append(line)
        i += 1

    result = "\n".join(final_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()
