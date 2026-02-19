import re
import chardet
from opencc import OpenCC
import pysubs2

cc = OpenCC('s2t')  # Simplified → Traditional


# ---------- Helpers ----------

def _detect_decode(data: bytes) -> str:
    encoding = chardet.detect(data)['encoding'] or 'utf-8'
    return data.decode(encoding, errors='ignore')

def is_end_of_sentence(line):
    return bool(re.search(r'[.?!…]$', line.strip())) or line.strip().endswith("...")

def strip_tags(text):
    return re.sub(r'</?[^>]+>', '', text)

def is_english(line):
    return bool(re.search(r'[a-zA-Z]', line)) and not re.search(r'[\u4e00-\u9fff]', line)

def normalize(text):
    return re.sub(r'\s+', ' ', text).strip()


# ---------- SRT Parsing ----------

def _parse_srt_text(content: str):
    content = content.replace('\ufeff', '')
    blocks = re.split(r'\n\s*\n', content.strip())
    eng_chi_pairs = []

    for block in blocks:
        lines = block.strip().split("\n")
        lines = [strip_tags(line.strip()) for line in lines if line.strip()]
        lines = [line for line in lines if not line.isdigit() and '-->' not in line]
        if not lines:
            continue
        en_lines = [line for line in lines if is_english(line)]
        zh_lines = [cc.convert(line) for line in lines if not is_english(line)]
        if en_lines and zh_lines:
            eng_chi_pairs.append((" ".join(en_lines), " ".join(zh_lines)))

    return eng_chi_pairs


# ---------- ASS → SRT (in-memory) ----------

def _ass_bytes_to_srt_text(data: bytes) -> str:
    text = _detect_decode(data)
    subs = pysubs2.SSAFile.from_string(text)
    return subs.to_string('srt')


# ---------- Script Builder ----------

def _build_script(eng_chi_pairs) -> str:
    final_script = []
    eng_buffer = []
    chi_buffer = []

    for en, zh in eng_chi_pairs:
        eng_buffer.append(en)
        chi_buffer.append(zh)
        if is_end_of_sentence(en):
            final_script.append(normalize(" ".join(eng_buffer)))
            final_script.append(normalize(" ".join(chi_buffer)))
            final_script.append("")
            eng_buffer = []
            chi_buffer = []

    if eng_buffer:
        final_script.append(normalize(" ".join(eng_buffer)))
        final_script.append(normalize(" ".join(chi_buffer)))
        final_script.append("")

    return "\n".join(final_script)


# ---------- Public API ----------

def process_subtitle_bytes(file_bytes: bytes, filename: str) -> str:
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext == 'ass':
        srt_text = _ass_bytes_to_srt_text(file_bytes)
        eng_chi_pairs = _parse_srt_text(srt_text)
    elif ext == 'srt':
        srt_text = _detect_decode(file_bytes)
        eng_chi_pairs = _parse_srt_text(srt_text)
    else:
        raise ValueError(f"Unsupported file type: .{ext}. Must be .srt or .ass")

    return _build_script(eng_chi_pairs)
