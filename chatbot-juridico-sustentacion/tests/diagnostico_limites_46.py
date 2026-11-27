from pathlib import Path
from app.processing_v2 import read_document, ARTICLE_PATTERN

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

texto = read_document(archivo)

inicio = texto.find("ARTICULO 46. CONTRATO A TERMINO FIJO")
final = texto.find("ARTICULO 48.", inicio)

if inicio == -1:
    print("No se encontró el artículo 46.")
    raise SystemExit

if final == -1:
    final = inicio + 18000

fragmento = texto[inicio:final]

for i, match in enumerate(ARTICLE_PATTERN.finditer(fragmento), 1):
    print("\n" + "=" * 65)
    print("COINCIDENCIA:", i)
    print("ENCABEZADO:", match.group(0))
    print("-" * 65)
    print(fragmento[max(0, match.start()-180):match.end()+250])