
from pathlib import Path
from app.processing_v2 import read_document
import re

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

texto = read_document(archivo)

patron = re.compile(
    r"(?im)^[ \t]*ARTICULO\s+(22|23|24)\b[^\n]*"
)

coincidencias = list(patron.finditer(texto))

print("ENCABEZADOS ENCONTRADOS:", len(coincidencias))

for i, match in enumerate(coincidencias, 1):

    inicio = max(0, match.start() - 1200)
    final = min(len(texto), match.end() + 500)

    print("\n" + "=" * 75)
    print("COINCIDENCIA:", i)
    print("ENCABEZADO:", match.group(0))
    print("=" * 75)

    print(texto[inicio:final])
