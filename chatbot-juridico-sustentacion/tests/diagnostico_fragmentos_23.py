
from pathlib import Path
from app.processing_v2 import read_document, chunk_text

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

texto = read_document(archivo)
fragmentos = chunk_text(texto)

articulo_23 = [
    fragmento
    for fragmento in fragmentos
    if fragmento.get("article") == "23"
]

print("FRAGMENTOS DEL ARTICULO 23:", len(articulo_23))

for i, fragmento in enumerate(articulo_23, 1):
    print("\n" + "=" * 65)
    print(
        f"FRAGMENTO {i} | "
        f"{fragmento['section']} | "
        f"{fragmento['version']} | "
        f"PARTE {fragmento['part']}"
    )
    print("=" * 65)

    print("ULTIMOS 500 CARACTERES:")
    print(fragmento["text"][-500:])
