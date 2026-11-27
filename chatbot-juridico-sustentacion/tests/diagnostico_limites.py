
from pathlib import Path
from app.processing_v2 import read_document

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

texto = read_document(archivo)

inicio = texto.find("ARTICULO 23. ELEMENTOS ESENCIALES.")
final = texto.find(
    "ARTICULO 24. PRESUNCION.",
    inicio + 1
)

if inicio == -1 or final == -1:
    print("No se encontraron los límites.")
else:
    contenido = texto[inicio:final]

    print("INICIO DEL ARTICULO 23")
    print("=" * 70)
    print(contenido[:1200])

    print("\nULTIMAS LINEAS DEL ARTICULO 23")
    print("=" * 70)
    print(contenido[-2500:])
