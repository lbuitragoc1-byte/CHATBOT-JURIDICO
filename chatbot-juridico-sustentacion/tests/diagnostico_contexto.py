
from pathlib import Path
from app.processing import read_document
import re

archivo = Path("data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf")

texto = read_document(archivo)

patron = re.compile(
    r"ART[IÍ]CULO\s+23\b",
    re.IGNORECASE
)

coincidencias = list(patron.finditer(texto))

print("TOTAL DE ENCABEZADOS DEL ARTÍCULO 23:", len(coincidencias))

for i, match in enumerate(coincidencias, 1):

    inicio = max(0, match.start() - 500)
    final = min(len(texto), match.start() + 1800)

    print("\n" + "=" * 70)
    print("COINCIDENCIA:", i)
    print("=" * 70)
    print(texto[inicio:final])
