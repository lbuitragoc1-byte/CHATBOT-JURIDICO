
import re
from pathlib import Path
import fitz


# ============================================================
# 1. LECTURA DE DOCUMENTOS
# ============================================================


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        pages = []

        with fitz.open(str(path)) as doc:
            for page_number, page in enumerate(doc, 1):
                page_text = page.get_text("text").strip()

                if page_text:
                    pages.append(
                        f"\n[PAGINA PDF: {page_number}]\n"
                        f"{page_text}"
                    )

        return "\n".join(pages).strip()

    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8").strip()

    raise ValueError("Solo se admiten documentos PDF o TXT")



# ============================================================
# 2. RECONOCIMIENTO DE ENCABEZADOS
# ============================================================

# Solo reconoce encabezados en mayúsculas al comienzo
# de una línea. No reconoce referencias como:
# "artículo 23 del Decreto 2351 de 1965".

ARTICLE_PATTERN = re.compile(
    r"(?m)^[ \t]*ART[IÍ]CULO[ \t]+"
    r"(\d+[A-Z]?)"
    r"[ \t]*[.°º-]?[ \t]*([^\n]*)"
)


HISTORICAL_PATTERN = re.compile(
    r"(?im)^[ \t]*(?:"
    r"LEGISLACI[ÓO]N ANTERIOR|"
    r"TEXTO ORIGINAL DEL C[ÓO]DIGO"
    r"(?: SUSTANTIVO(?: DEL TRABAJO)?)?"
    r")[ \t]*:?[ \t]*$"
)


# ============================================================
# 3. DETECCION DE SECCIONES
# ============================================================

SECTION_PATTERNS = [
    (
        "notas_vigencia",
        re.compile(
            r"^[ \t]*NOTAS DE VIGENCIA[ \t]*:?[ \t]*$",
            re.IGNORECASE
        ),
        "referencias"
    ),
    (
        "concordancias",
        re.compile(
            r"^[ \t]*CONCORDANCIAS[ \t]*:?[ \t]*$",
            re.IGNORECASE
        ),
        "referencias"
    ),
    (
        "doctrina",
        re.compile(
            r"^[ \t]*DOCTRINA CONCORDANTE[ \t]*:?[ \t]*$",
            re.IGNORECASE
        ),
        "referencias"
    ),
    (
        "legislacion_anterior",
        HISTORICAL_PATTERN,
        "historica"
    ),
]


def detect_section_heading(line: str):

    for section, pattern, version in SECTION_PATTERNS:

        if pattern.match(line):
            return section, version

    return None


# ============================================================
# 4. FRAGMENTACION DE TEXTO
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
# 5. AGRUPACION DE ARTICULOS
# ============================================================

def detect_articles(text: str):

    matches = list(ARTICLE_PATTERN.finditer(text))

    if not matches:
        return []

    groups = []
    current_start = matches[0].start()
    current_number = matches[0].group(1)

    for i in range(1, len(matches)):

        match = matches[i]

        previous_text = text[current_start:match.start()]

        # Si estamos dentro de legislación anterior y aparece
        # nuevamente el mismo artículo, no crear otro artículo.
        historical_context = bool(
            HISTORICAL_PATTERN.search(previous_text)
        )

        same_article = (
            match.group(1) == current_number
        )

        if historical_context and same_article:
            continue

        groups.append({
            "article": current_number,
            "start": current_start,
            "end": match.start()
        })

        current_start = match.start()
        current_number = match.group(1)

    groups.append({
        "article": current_number,
        "start": current_start,
        "end": len(text)
    })

    return groups


# ============================================================
# 6. SEPARACION DE SECCIONES INTERNAS
# ============================================================

def split_article_sections(article_text: str):

    lines = article_text.splitlines()

    sections = []

    current_section = "contenido_principal"
    current_version = "sin_verificar"
    current_lines = []

    for line in lines:

        detected = detect_section_heading(line)

        if detected:

            if current_lines:

                sections.append({
                    "section": current_section,
                    "version": current_version,
                    "text": "\n".join(current_lines).strip()
                })

            current_section, current_version = detected

            current_lines = [line]

        else:
            # Jurisprudencia Vigencia se conserva dentro del
            # contenido porque puede aparecer intercalada
            # con la redacción normativa del artículo.
            current_lines.append(line)

    if current_lines:

        sections.append({
            "section": current_section,
            "version": current_version,
            "text": "\n".join(current_lines).strip()
        })

    return [
        section for section in sections
        if section["text"]
    ]


# ============================================================
# 7. PROCESAMIENTO ESTRUCTURADO
# ============================================================

def chunk_text(
    text: str,
    size: int = 1100,
    overlap: int = 180
) -> list[dict]:

    if not text.strip():
        return []

    if not 0 <= overlap < size:
        raise ValueError("Solapamiento inválido")

    # Normalizacion conservando saltos de linea
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    articles = detect_articles(text)

    results = []

    # Conservar texto anterior al primer artículo
    if articles and articles[0]["start"] > 0:

        preamble = text[:articles[0]["start"]].strip()

        for i, piece in enumerate(
            split_long_block(preamble, size, overlap), 1
        ):

            results.append({
                "article": None,
                "section": "introduccion_documento",
                "version": "sin_verificar",
                "part": i,
                "text": piece
            })

    if not articles:

        for i, piece in enumerate(
            split_long_block(text, size, overlap), 1
        ):

            results.append({
                "article": None,
                "section": "documento_general",
                "version": "sin_verificar",
                "part": i,
                "text": piece
            })

        return results

    for article_data in articles:

        article_number = article_data["article"]

        article_text = text[
            article_data["start"]:article_data["end"]
        ].strip()

        article_heading = article_text.split("\n", 1)[0].strip()

        sections = split_article_sections(article_text)

        for section_data in sections:

            prefix = (
                f"{article_heading}\n"
                f"[ARTICULO {article_number}]\n"
                f"[SECCION: {section_data['section']}]\n"
                f"[VERSION: {section_data['version']}]\n"
            )

            available_size = max(300, size - len(prefix))

            pieces = split_long_block(
                section_data["text"],
                available_size,
                overlap
            )

            for part_number, piece in enumerate(pieces, 1):

                results.append({
                    "article": article_number,
                    "section": section_data["section"],
                    "version": section_data["version"],
                    "part": part_number,
                    "text": (
                        prefix
                        + f"[PARTE {part_number}]\n"
                        + piece
                    )
                })

    return results


# ============================================================
# 8. EXTRACCION DE ENTIDADES JURIDICAS
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
