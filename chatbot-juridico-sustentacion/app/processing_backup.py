import re
from pathlib import Path
import fitz

def read_document(path: Path) -> str:
    if path.suffix.lower() == '.pdf':
        with fitz.open(str(path)) as doc:
            return '\n'.join(page.get_text() for page in doc).strip()
    if path.suffix.lower() == '.txt':
        return path.read_text(encoding='utf-8').strip()
    raise ValueError('Solo PDF o TXT')

def chunk_text(text: str, size: int = 1100, overlap: int = 180) -> list[str]:
    if not text.strip(): return []
    if not 0 <= overlap < size: raise ValueError('Solapamiento inválido')
    text = re.sub(r'\s+', ' ', text).strip()
    result, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(' ', start + size // 2, end)
            if boundary > start: end = boundary
        result.append(text[start:end].strip())
        if end == len(text): break
        start = end - overlap
    return result

PATTERNS = {
    'Normas': r'\b(?:Ley|Decreto|Resolución)\s+\d+\s+de\s+\d{4}\b',
    'Artículos': r'\b(?:artículo|art\.?)\s+\d+[A-Za-z]?\b',
    'Sentencias': r'\b(?:Sentencia\s+)?(?:T|C|SU|SL|SC|SP)[-– ]\d{1,6}(?:[-– ](?:de\s+)?\d{2,4})?\b',
}
def extract_entities(text: str) -> dict[str, list[str]]:
    return {k: sorted(set(re.findall(v, text, flags=re.IGNORECASE))) for k,v in PATTERNS.items()}
