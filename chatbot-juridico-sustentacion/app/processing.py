
import re
from pathlib import Path
import fitz


# ============================================================
# 1. LECTURA DE DOCUMENTOS
# ============================================================

def read_document(path: Path) -> str:

    if path.suffix.lower() == ".pdf":
        with fitz.open(str(path)) as doc:
            return "\n".join(page.get_text() for page in doc).strip()

    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8").strip()

    raise ValueError("Solo PDF o TXT")


# ============================================================
# 2. RECONOCIMIENTO DE ENCABEZADOS JURIDICOS
# ============================================================

ARTICLE_PATTERN = re.compile(
    r"(?im)^[ \t]*ART[IÍ]CULO\s+(\d+[A-Z]?)"
    r"[ \t]*[.°º-]?[ \t]*([^\n]*)$"
)

HISTORICAL_PATTERN = re.compile(
    r"(?im)^[ \t]*(?:"
    r"LEGISLACI[ÓO]N ANTERIOR|"
    r"TEXTO ORIGINAL DEL C[ÓO]DIGO"
    r"(?: SUSTANTIVO(?: DEL TRABAJO)?)?"
    r")[ \t]*:?[ \t]*$"
)


# ============================================================
# 3. FRAGMENTACION DE TEXTOS EXTENSOS
# ============================================================

def split_long_block(
    text: str,
    size: int = 1100,
    overlap: int = 180
) -> list[str]:

    if not 0 <= overlap < size:
        raise ValueError("Solapamiento inválido")

    result = []
    start = 0

    while start < len(text):

        end = min(start + size, len(text))

        if end < len(text):

            boundary = text.rfind(
                "\n",
                start + size // 2,
                end
            )

            if boundary <= start:
                boundary = text.rfind(
                    " ",
                    start + size // 2,
                    end
                )

            if boundary > start:
                end = boundary

        piece = text[start:end].strip()

        if piece:
            result.append(piece)

        if end == len(text):
            break

        start = end - overlap

    return result


# ============================================================
# 4. PROCESAMIENTO JURIDICO ESTRUCTURADO
# ============================================================

def chunk_text(
    text: str,
    size: int = 1100,
    overlap: int = 180
) -> list[str]:

    if not text.strip():
        return []

    if not 0 <= overlap < size:
        raise ValueError("Solapamiento inválido")

    # Normalizar texto sin eliminar saltos de línea
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    matches = list(ARTICLE_PATTERN.finditer(text))

    if not matches:
        return split_long_block(text, size, overlap)

    result = []

    # Contexto de la sección histórica
    historical_pending = False

    for i, match in enumerate(matches):

        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(text)
        )

        article_text = text[match.start():end].strip()

        if not article_text:
            continue

        article_number = match.group(1)
        heading = match.group(0).strip()

        newline = article_text.find("\n")

        if newline == -1:
            body = ""
        else:
            body = article_text[newline + 1:].strip()

        # Determinar si este encabezado pertenece
        # a una sección histórica anterior.
        is_historical = historical_pending

        # Detectar indicadores históricos dentro del bloque
        has_historical_marker = bool(
            HISTORICAL_PATTERN.search(body)
        )

        # Una sección histórica puede comenzar al final
        # del contenido de un artículo.
        if has_historical_marker and not is_historical:

            historical_pending = True

        else:
            historical_pending = False

        # Clasificación documental
        if is_historical:

            section_label = "CONTENIDO HISTÓRICO"

        elif has_historical_marker:

            section_label = (
                "CONTENIDO PRINCIPAL - VIGENCIA POR VERIFICAR"
            )

        else:

            section_label = (
                "CONTENIDO - VIGENCIA POR VERIFICAR"
            )

        prefix = (
            f"{heading}\n"
            f"[ARTÍCULO {article_number}]\n"
            f"[{section_label}]\n"
        )

        if not body:
            body = heading

        available_size = max(300, size - len(prefix))

        pieces = split_long_block(
            body,
            size=available_size,
            overlap=overlap
        )

        for part_number, piece in enumerate(pieces, 1):

            result.append(
                f"{prefix}"
                f"[PARTE {part_number}]\n"
                f"{piece}"
            )

    return result


# ============================================================
# 5. EXTRACCION DE ENTIDADES JURIDICAS
# ============================================================

PATTERNS = {

    "Normas": (
        r"\b(?:Ley|Decreto|Resolución)\s+"
        r"\d+\s+de\s+\d{4}\b"
    ),

    "Artículos": (
        r"\b(?:artículo|art\.?)\s+"
        r"\d+[A-Za-z]?\b"
    ),

    "Sentencias": (
        r"\b(?:Sentencia\s+)?"
        r"(?:T|C|SU|SL|SC|SP)[-– ]\d{1,6}"
        r"(?:[-– ]\d{2,4})?\b"
    ),
}


def extract_entities(text: str) -> dict[str, list[str]]:

    return {
        key: sorted(
            set(
                re.findall(
                    pattern,
                    text,
                    flags=re.IGNORECASE
                )
            )
        )
        for key, pattern in PATTERNS.items()
    }
