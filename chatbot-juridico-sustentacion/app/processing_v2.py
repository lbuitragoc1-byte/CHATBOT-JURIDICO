import re
from pathlib import Path

try:
    # PyMuPDF moderno
    import pymupdf as fitz
except ImportError:
    # Compatibilidad con instalaciones anteriores
    import fitz


# ============================================================
# 1. LECTURA DE DOCUMENTOS
# ============================================================

def read_document(path: Path) -> str:
    """
    Lee archivos PDF o TXT y devuelve el texto conservando
    referencias a las páginas del PDF.
    """
    path = Path(path)

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
        return path.read_text(encoding="utf-8-sig").strip()

    raise ValueError("Solo se admiten documentos PDF o TXT")


# ============================================================
# 2. RECONOCIMIENTO DE ENCABEZADOS
# ============================================================

# Reconoce encabezados jurídicos al comienzo de una línea.
# Ejemplos:
# ARTICULO 23. ELEMENTOS ESENCIALES
# ARTÍCULO 33. Requisitos para Obtener la Pensión de Vejez
# ARTICULO 23A. ...

ARTICLE_PATTERN = re.compile(
    r"(?m)^[ \t]*(?i:ART[IÍ]CULO)[ \t]+"
    r"(\d+[A-Z]?)(?:[oº°])?(?![A-Za-z0-9])"
    r"[ \t]*[.°º-]?[ \t]*([^\n]*)"
)


# Encabezados que indican que el texto que sigue pertenece
# a legislación anterior o a una versión normativa específica.
HISTORICAL_PATTERN = re.compile(
    r"(?im)^[ \t]*(?:"
    r"LEGISLACI[ÓO]N ANTERIOR|"
    r"TEXTO ORIGINAL DEL C[ÓO]DIGO"
    r"(?: SUSTANTIVO(?: DEL TRABAJO)?)?|"
    r"TEXTO ORIGINAL (?:DEL|DE LA) (?:LEY|DECRETO(?: LEY)?)"
    r"(?:\s+\d+[A-Za-zº°.]*)?(?:\s+DE\s+\d{4})?|"
    r"TEXTO MODIFICADO POR (?:LA|EL) "
    r"(?:LEY|DECRETO(?: LEY)?) "
    r"\d+[A-Za-zº°.]*(?:\s+DE\s+\d{4})?"
    r")[ \t]*:?[ \t]*$"
)


# Señales de que los encabezados ARTÍCULO que aparezcan
# en el texto pueden ser referencias editoriales y no artículos
# pertenecientes al documento principal.
REFERENCE_CONTEXT_PATTERN = re.compile(
    r"(?:"
    r"^[ \t]*(?:"
    r"NOTAS DE VIGENCIA|"
    r"NOTAS DEL EDITOR|"
    r"JURISPRUDENCIA VIGENCIA|"
    r"CONCORDANCIAS|"
    r"DOCTRINA CONCORDANTE|"
    r"LEGISLACI[ÓO]N ANTERIOR"
    r")[ \t]*:?[ \t]*$"
    r"|"
    r"\b(?:"
    r"El texto referido es el siguiente|"
    r"Los cuales establecen|"
    r"El cual establece"
    r")\s*:"
    r"|"
    r"\bTexto\s+(?:original|modificado)\s+"
    r"(?:del?\s+)?(?:Decreto|Ley|Código)\b"
    r")",
    re.IGNORECASE | re.MULTILINE
)


# ============================================================
# 3. DETECCIÓN Y CLASIFICACIÓN DE SECCIONES
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
    """Identifica si una línea inicia una sección especial."""
    for section, pattern, version in SECTION_PATTERNS:
        if pattern.match(line.strip()):
            return section, version

    return None


def detect_historical_version(line: str):
    """
    Identifica la norma de la que procede una versión histórica.

    Devuelve, por ejemplo:
    ley_50_1990
    ley_797_2003
    decreto_2351_1965
    codigo_sustantivo_original
    """

    line = line.strip()

    modified = re.match(
        r"(?i)^Texto modificado por (?:la|el) "
        r"(Ley|Decreto(?: Ley)?) "
        r"(\d+[A-Za-zº°.]*) de (\d{4})\s*:?\s*$",
        line
    )

    if modified:
        norm_type = modified.group(1).lower().replace(" ", "_")
        number = re.sub(r"[^a-z0-9]", "", modified.group(2).lower())
        year = modified.group(3)
        return f"{norm_type}_{number}_{year}"

    original = re.match(
        r"(?i)^Texto original "
        r"(?:(?:del|de la) )?"
        r"(Ley|Decreto(?: Ley)?) "
        r"(\d+[A-Za-zº°.]*) de (\d{4})\s*:?\s*$",
        line
    )

    if original:
        norm_type = original.group(1).lower().replace(" ", "_")
        number = re.sub(r"[^a-z0-9]", "", original.group(2).lower())
        year = original.group(3)
        return f"{norm_type}_{number}_{year}"

    if re.match(
        r"(?i)^Texto original del C[ÓO]DIGO "
        r"SUSTANTIVO DEL TRABAJO\s*:?\s*$",
        line
    ):
        return "codigo_sustantivo_original"

    return None


# ============================================================
# 4. FRAGMENTACIÓN DE TEXTO
# ============================================================

def split_long_block(
    text: str,
    size: int = 1100,
    overlap: int = 180
) -> list[str]:
    """
    Divide un texto extenso en fragmentos con solapamiento.
    Intenta no cortar palabras ni separar párrafos innecesariamente.
    """

    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Tamaño o solapamiento inválido")

    if not text:
        return []

    result = []
    start = 0
    text_length = len(text)

    while start < text_length:
        target_end = min(start + size, text_length)
        end = target_end

        if target_end < text_length:
            min_boundary = start + size // 2

            newline_boundary = text.rfind(
                "\n",
                min_boundary,
                target_end
            )

            if newline_boundary > start:
                end = newline_boundary
            else:
                spaces = list(
                    re.finditer(
                        r"\s",
                        text[min_boundary:target_end]
                    )
                )

                if spaces:
                    end = (
                        min_boundary
                        + spaces[-1].start()
                    )
                else:
                    next_space = re.search(
                        r"\s",
                        text[target_end:]
                    )

                    if next_space:
                        end = (
                            target_end
                            + next_space.start()
                        )
                    else:
                        end = text_length

        piece = text[start:end].strip()

        if piece:
            result.append(piece)

        if end >= text_length:
            break

        next_start = max(
            start + 1,
            end - overlap
        )

        if text[next_start].isspace():
            while (
                next_start < text_length
                and text[next_start].isspace()
            ):
                next_start += 1

        elif (
            next_start > 0
            and not text[next_start - 1].isspace()
        ):
            next_space = re.search(
                r"\s",
                text[next_start:]
            )

            if next_space:
                next_start += next_space.end()
            else:
                break

        start = next_start

    return result


# ============================================================
# 5. AGRUPACIÓN DE ARTÍCULOS
# ============================================================

def detect_articles(text: str):
    """
    Localiza los encabezados de artículos y delimita su contenido.

    Dentro de notas, concordancias y legislación anterior se exige
    una numeración secuencial para reducir falsos positivos causados
    por referencias a artículos de otras normas.
    """

    matches = list(ARTICLE_PATTERN.finditer(text))

    if not matches:
        return []

    groups = []

    current_start = matches[0].start()
    current_number = matches[0].group(1)

    def is_next_article(previous: str, candidate: str) -> bool:
        prev = re.fullmatch(r"(\d+)([A-Z]?)", previous)
        curr = re.fullmatch(r"(\d+)([A-Z]?)", candidate)

        if not prev or not curr:
            return False

        prev_num = int(prev.group(1))
        prev_suffix = prev.group(2)
        curr_num = int(curr.group(1))
        curr_suffix = curr.group(2)

        if curr_num == prev_num:
            if not prev_suffix and curr_suffix == "A":
                return True

            if prev_suffix and curr_suffix:
                return ord(curr_suffix) == ord(prev_suffix) + 1

        return curr_num == prev_num + 1 and not curr_suffix

    for match in matches[1:]:
        candidate_number = match.group(1)

        preceding_context = text[
            max(0, match.start() - 500):match.start()
        ]

        # No iniciar un artículo del documento cuando el encabezado
        # pertenece a una transcripción explícita de otra norma.
        external_reference = re.search(
            r"(?i)(?:"
            r"\bEl texto referido es el siguiente\s*:|"
            r"\bTexto original\s+(?:de\s+la\s+)?Ley\s+"
            r"[\wº°ª.-]+(?:\s+de\s+\d{4})?\s*:?"
            r")\s*$",
            preceding_context
        )

        if external_reference:
            continue

        # Analizar únicamente el contexto cercano al encabezado.
        # Evita que referencias históricas anteriores afecten
        # la detección de artículos posteriores.

        reference_context = bool(
             HISTORICAL_PATTERN.search(preceding_context)
            or REFERENCE_CONTEXT_PATTERN.search(preceding_context)
        )

        if reference_context and not is_next_article(
            current_number,
            candidate_number
        ):
            continue

        groups.append({
            "article": current_number,
            "start": current_start,
            "end": match.start()
        })

        current_start = match.start()
        current_number = candidate_number

    groups.append({
        "article": current_number,
        "start": current_start,
        "end": len(text)
    })

    return groups


# ============================================================
# 6. SEPARACIÓN DE SECCIONES INTERNAS
# ============================================================

def split_article_sections(article_text: str):
    """
    Separa el contenido principal, las referencias editoriales
    y las versiones históricas de un artículo.
    """

    lines = article_text.splitlines()

    sections = []

    current_section = "contenido_principal"
    current_version = "sin_verificar"
    current_lines = []

    def save_current_section():
        if current_lines:
            section_text = "\n".join(current_lines).strip()

            if section_text:
                sections.append({
                    "section": current_section,
                    "version": current_version,
                    "text": section_text
                })

    for line in lines:
        historical_version = detect_historical_version(line)

        # Si ya estamos dentro de legislación anterior y aparece
        # otra etiqueta de versión, cerrar la versión anterior.
        if (
            historical_version
            and current_section == "legislacion_anterior"
        ):
            save_current_section()
            current_version = historical_version
            current_lines = [line]
            continue

        detected = detect_section_heading(line)

        if detected:
            save_current_section()

            current_section, current_version = detected

            if current_section == "legislacion_anterior":
                # Si el propio encabezado identifica la norma,
                # conservar esa identificación como versión.
                specific_version = detect_historical_version(line)

                if specific_version:
                    current_version = specific_version
                    current_lines = [line]
                else:
                    current_lines = []
            else:
                current_lines = [line]

        else:
            current_lines.append(line)

    save_current_section()

    return [
        section
        for section in sections
        if section["text"]
    ]


# ============================================================
# 7. EXTRACCIÓN E INTEGRACIÓN DE LITERALES
# ============================================================

# Reconoce literales como:
# a. La actividad personal...
# b) La subordinación...
CLAUSE_MARKER_PATTERN = re.compile(
    r"(?im)^[ \t]*([a-z])[.)][ \t]+"
)


def extract_lettered_clauses(text: str) -> dict:
    """Extrae literales alfabéticos y su contenido."""

    matches = list(CLAUSE_MARKER_PATTERN.finditer(text))
    clauses = {}

    for index, match in enumerate(matches):
        start = match.start()

        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        clause = text[start:end].strip()

        # Evitar que notas editoriales queden dentro del literal.
        clause = re.split(
            r"(?im)^[ \t]*(?:"
            r"Jurisprudencia Vigencia|"
            r"Notas de Vigencia|"
            r"Concordancias|"
            r"Doctrina Concordante|"
            r"Legislación anterior"
            r")[ \t]*$",
            clause,
            maxsplit=1
        )[0].strip()

        clauses[match.group(1).lower()] = clause

    return clauses


def merge_unmodified_literals(sections: list[dict]) -> list[dict]:
    """
    Recupera literales que no aparecen en el contenido principal
    desde la versión modificada anterior más reciente.

    Nunca reemplaza un literal presente en el contenido principal.
    Tampoco recupera un literal que las notas identifiquen como
    expresamente modificado.
    """

    principal_sections = [
        section
        for section in sections
        if section["section"] == "contenido_principal"
    ]

    if not principal_sections:
        return sections

    principal = principal_sections[0]

    principal_text = "\n".join(
        section["text"]
        for section in principal_sections
    )

    current_clauses = extract_lettered_clauses(principal_text)

    # Buscar versiones anteriores identificadas por norma y año.
    previous_versions = []

    for section in sections:
        version = section.get("version", "")

        if (
            section["section"] == "legislacion_anterior"
            and version not in {
                "historica",
                "codigo_sustantivo_original"
            }
            and re.search(r"_\d{4}$", version)
        ):
            previous_versions.append(section)

    previous_versions.sort(
        key=lambda section: int(
            re.search(r"(\d{4})$", section["version"]).group(1)
        ),
        reverse=True
    )

    principal["merged_literals"] = {}

    notes_text = "\n".join(
        section["text"]
        for section in sections
        if section["section"] == "notas_vigencia"
    )

    for previous in previous_versions:
        previous_clauses = extract_lettered_clauses(
            previous["text"]
        )

        for letter, clause in previous_clauses.items():
            letter = letter.lower()

            # No recuperar un literal que ya esté presente.
            if letter in current_clauses:
                continue

            # Comprobación adicional para evitar duplicados si el
            # PDF dejó el literal en una línea con formato irregular.
            current_marker = re.search(
                rf"(?im)^[ \t]*{re.escape(letter)}[.)][ \t]+",
                principal_text
            )

            if current_marker:
                current_clauses[letter] = current_marker.group(0)
                continue

            # No recuperar literales expresamente modificados.
            modification_pattern = re.compile(
                rf"(?i)\bliteral\s+{re.escape(letter)}"
                rf"\s*(?:\)|\.)?\s+modificad[oa]"
            )

            if modification_pattern.search(notes_text):
                continue

            principal["text"] += "\n" + clause
            principal_text += "\n" + clause

            current_clauses[letter] = clause
            principal["merged_literals"][letter] = previous["version"]

    return sections


# ============================================================
# 8. PROCESAMIENTO ESTRUCTURADO
# ============================================================

def chunk_text(
    text: str,
    size: int = 1100,
    overlap: int = 180
) -> list[dict]:
    """
    Convierte el documento en fragmentos jurídicos estructurados.

    Cada fragmento conserva:
    - Número de artículo.
    - Sección.
    - Versión identificada.
    - Estado normativo.
    - Indicador de verificación de vigencia.
    - Literales recuperados desde versiones anteriores.
    """

    if not text or not text.strip():
        return []

    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Tamaño o solapamiento inválido")

    # Normalización básica sin eliminar saltos de línea.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    articles = detect_articles(text)
    results = []

    # Conservar texto anterior al primer artículo.
    if articles and articles[0]["start"] > 0:
        preamble = text[:articles[0]["start"]].strip()

        for part_number, piece in enumerate(
            split_long_block(preamble, size, overlap),
            1
        ):
            results.append({
                "article": None,
                "section": "introduccion_documento",
                "version": "sin_verificar",
                "estado_normativo": "sin_clasificar",
                "vigencia_verificada": False,
                "literales_integrados": {},
                "part": part_number,
                "text": piece
            })

    # Si no se detectan artículos, fragmentar el documento completo.
    if not articles:
        for part_number, piece in enumerate(
            split_long_block(text, size, overlap),
            1
        ):
            results.append({
                "article": None,
                "section": "documento_general",
                "version": "sin_verificar",
                "estado_normativo": "sin_clasificar",
                "vigencia_verificada": False,
                "literales_integrados": {},
                "part": part_number,
                "text": piece
            })

        return results

    for article_data in articles:
        article_number = article_data["article"]

        article_text = text[
            article_data["start"]:article_data["end"]
        ].strip()

        if not article_text:
            continue

        article_heading = article_text.split("\n", 1)[0].strip()

        sections = split_article_sections(article_text)

        # Recuperar literales no modificados, si corresponde.
        sections = merge_unmodified_literals(sections)

        for section_data in sections:
            section_name = section_data["section"]

            prefix = (
                f"{article_heading}\n"
                f"[ARTICULO {article_number}]\n"
                f"[SECCION: {section_name}]\n"
                f"[VERSION: {section_data['version']}]\n"
            )

            available_size = max(300, size - len(prefix))

            pieces = split_long_block(
                section_data["text"],
                available_size,
                overlap
            )

            # Clasificar la sección sin afirmar que el contenido
            # principal está vigente si no se ha verificado.
            if section_name == "legislacion_anterior":
                estado_normativo = "historico"

            elif section_name in {
                "notas_vigencia",
                "concordancias",
                "doctrina"
            }:
                estado_normativo = "referencia"

            elif section_name == "contenido_principal":
                estado_normativo = "pendiente_verificacion"

            else:
                estado_normativo = "sin_clasificar"

            merged_literals = section_data.get(
                "merged_literals",
                {}
            )

            for part_number, piece in enumerate(pieces, 1):
                integrated_in_piece = {
                    letter: source_version
                    for letter, source_version in merged_literals.items()
                    if re.search(
                        rf"(?im)^[ \t]*{re.escape(letter)}[.)][ \t]+",
                        piece
                    )
                }

                results.append({
                    "article": article_number,
                    "section": section_name,
                    "version": section_data["version"],
                    "estado_normativo": estado_normativo,
                    "vigencia_verificada": False,
                    "literales_integrados": integrated_in_piece,
                    "part": part_number,
                    "text": (
                        prefix
                        + f"[PARTE {part_number}]\n"
                        + piece
                    )
                })

    return results


# ============================================================
# 9. EXTRACCIÓN DE ENTIDADES JURÍDICAS
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
    """Extrae normas, artículos y sentencias mediante expresiones regulares."""

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
