
import re
from pathlib import Path

from app.processing_v2 import (
    read_document,
    detect_articles,
    ARTICLE_PATTERN
)

text = read_document(
    Path("data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf")
)

target = text.find("ARTICULO 24. TRABAJADORES AMPARADOS")

groups = detect_articles(text)

group = next(
    g for g in groups
    if g["start"] <= target < g["end"]
)

start = group["start"]

print("GRUPO DETECTADO:", group["article"])
print("POSICION INICIAL:", start)

print("\nCONTEXTO ANTERIOR AL INICIO DEL GRUPO")
print("=" * 65)

print(text[max(0, start - 1000):start + 700])

preceding = text[max(0, start - 800):start]

print("\nCOMPROBACION DE REFERENCIA EXTERNA")
print("=" * 65)

pattern = r"(?i)El texto referido es el siguiente\s*:\s*$"

print(
    "¿Encuentra la frase inmediatamente anterior?",
    bool(re.search(pattern, preceding))
)

print("\nENCABEZADO RECONOCIDO:")
match = next(
    m for m in ARTICLE_PATTERN.finditer(text)
    if m.start() == start
)

print(match.group(0))
