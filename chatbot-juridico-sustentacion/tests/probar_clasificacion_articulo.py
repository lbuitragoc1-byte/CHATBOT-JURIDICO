
from pathlib import Path
from app.processing_v2 import read_document, chunk_text

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

texto = read_document(archivo)
fragmentos = chunk_text(texto)

articulos = [
    f for f in fragmentos
    if f.get("article") == "23"
]

print("FRAGMENTOS DEL ARTICULO 23:", len(articulos))
print("=" * 65)

for f in articulos:

    print("\nSECCION:", f.get("section"))
    print("VERSION:", f.get("version"))
    print("PARTE:", f.get("part"))
    print("-" * 65)
    print(f.get("text", "")[:500])
