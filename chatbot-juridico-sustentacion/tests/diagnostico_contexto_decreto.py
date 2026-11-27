from pathlib import Path
from app.processing_v2 import read_document

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

texto = read_document(archivo)

busqueda = "ARTICULO 24. TRABAJADORES AMPARADOS"

posicion = texto.find(busqueda)

if posicion == -1:
    print("No se encontró el encabezado.")
else:
    inicio = max(0, posicion - 3000)
    final = min(len(texto), posicion + 1500)

    contexto = texto[inicio:final]

    print("POSICION:", posicion)
    print("=" * 70)
    print(contexto)
    print("=" * 70)