
from pathlib import Path
from app.processing_v2 import read_document, chunk_text

text = read_document(
    Path("data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf")
)

fragments = [
    x for x in chunk_text(text)
    if x.get("article") == "406"
    and x.get("section") == "legislacion_anterior"
]

print("VERSIONES HISTORICAS DEL ARTICULO 406")
print("=" * 70)

for i, fragment in enumerate(fragments, 1):

    print(f"\nFRAGMENTO {i}")
    print("VERSION:", fragment["version"])
    print("PARTE:", fragment["part"])
    print("-" * 70)

    print(fragment["text"])

    print("\n" + "=" * 70)
