
from pathlib import Path
from app.processing_v2 import read_document, chunk_text

text = read_document(
    Path("data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf")
)

fragments = [
    x for x in chunk_text(text)
    if x.get("article") == "406"
]

print("FRAGMENTOS DEL ARTICULO 406:", len(fragments))
print("=" * 65)

for i, fragment in enumerate(fragments, 1):

    print(
        f"\nFRAGMENTO {i} | "
        f"SECCION: {fragment['section']} | "
        f"VERSION: {fragment['version']} | "
        f"PARTE: {fragment['part']}"
    )

    if "ARTICULO 24. TRABAJADORES AMPARADOS" in fragment["text"]:
        print("\nENCONTRADO ARTICULO 24 HISTORICO:")
        print(fragment["text"][-700:])

    elif fragment["section"] == "contenido_principal":
        print("\nMUESTRA DEL CONTENIDO VIGENTE:")
        print(fragment["text"][-350:])
