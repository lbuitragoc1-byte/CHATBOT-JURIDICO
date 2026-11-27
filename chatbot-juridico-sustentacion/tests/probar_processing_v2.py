
from pathlib import Path
from app.processing_v2 import read_document, chunk_text

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

texto = read_document(archivo)
fragmentos = chunk_text(texto)

articulos = ["22", "23", "24"]

print("TOTAL DE FRAGMENTOS:", len(fragmentos))

for articulo in articulos:

    encontrados = [
        f for f in fragmentos
        if f["article"] == articulo
    ]

    print("\n" + "=" * 60)
    print("ARTICULO", articulo)
    print("=" * 60)

    print("Total de fragmentos:", len(encontrados))

    for fragmento in encontrados:

        print(
            "Sección:", fragmento["section"],
            "| Versión:", fragmento["version"],
            "| Parte:", fragmento["part"]
        )

    principales = [
        f for f in encontrados
        if f["section"] == "contenido_principal"
    ]

    print("\nMUESTRA DEL CONTENIDO PRINCIPAL:")

    for fragmento in principales[:2]:
        print(fragmento["text"][:700])
        print("-" * 40)
