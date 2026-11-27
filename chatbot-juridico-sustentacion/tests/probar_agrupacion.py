
from pathlib import Path
from app.processing_v2 import read_document, chunk_text

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

texto = read_document(archivo)
fragmentos = chunk_text(texto)

print("TOTAL DE FRAGMENTOS:", len(fragmentos))

print("\nARTICULOS PRINCIPALES")
print("=" * 60)

for numero in ["22", "23", "24", "46", "47"]:

    encontrados = [
        f for f in fragmentos
        if f.get("article") == numero
        and f.get("section") == "contenido_principal"
    ]

    print(f"\nARTICULO {numero}: {len(encontrados)} fragmentos")

    for f in encontrados:
        print(
            "Parte:", f["part"],
            "| Versión:", f["version"]
        )

print("\nCOMPROBACION DE ENCABEZADOS HISTORICOS")
print("=" * 60)

marcadores = [
    "ARTICULO 4o. CONTRATO A TERMINO FIJO",
    "ARTICULO 24. TRABAJADORES AMPARADOS",
    "ARTICULO 46. CONTRATO POR TIEMPO DETERMINADO",
    "ARTICULO 47. DURACIÓN INDEFINIDA",
    "ARTÍCULO 47. PLAZO PRESUNTIVO"
]

for marcador in marcadores:

    coincidencias = [
        f for f in fragmentos
        if marcador in f["text"]
    ]

    print(f"\n{marcador}")

    if not coincidencias:
        print("NO ENCONTRADO")
        continue

    for f in coincidencias:
        print(
            "Agrupado como artículo:",
            f["article"],
            "| Sección:",
            f["section"],
            "| Versión:",
            f["version"]
        )
