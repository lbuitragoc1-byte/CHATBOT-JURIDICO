
from pathlib import Path

from app.processing_v2 import (
    read_document,
    detect_articles,
    ARTICLE_PATTERN
)

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

texto = read_document(archivo)

objetivo = "ARTICULO 24. TRABAJADORES AMPARADOS"

posicion = texto.lower().find(objetivo.lower())

print("POSICION DEL ENCABEZADO:", posicion)
print("=" * 70)

if posicion == -1:
    print("No se encontró el encabezado.")
    raise SystemExit

grupos = detect_articles(texto)

grupo_encontrado = None
indice = None

for i, grupo in enumerate(grupos):

    if grupo["start"] <= posicion < grupo["end"]:
        grupo_encontrado = grupo
        indice = i
        break

if grupo_encontrado:

    print("ARTICULO AL QUE FUE ASIGNADO:")
    print(grupo_encontrado["article"])

    print("\nENCABEZADOS DENTRO DE ESE GRUPO:")
    print("-" * 70)

    segmento = texto[
        grupo_encontrado["start"]:grupo_encontrado["end"]
    ]

    for match in ARTICLE_PATTERN.finditer(segmento):
        print(match.group(0).strip())

    print("\nINICIO DEL GRUPO:")
    print(segmento[:1500])

    print("\nFINAL DEL GRUPO:")
    print(segmento[-1500:])

    print("\nGRUPO ANTERIOR Y SIGUIENTE:")
    print("-" * 70)

    for j in range(
        max(0, indice - 1),
        min(len(grupos), indice + 2)
    ):

        g = grupos[j]

        print(
            f"Artículo {g['article']} | "
            f"Inicio {g['start']} | "
            f"Final {g['end']}"
        )

else:
    print("No se encontró ningún grupo que contenga el encabezado.")

