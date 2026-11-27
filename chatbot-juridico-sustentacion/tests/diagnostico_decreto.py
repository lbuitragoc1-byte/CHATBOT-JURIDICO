
from pathlib import Path
from app.processing_v2 import read_document
import re

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

texto = read_document(archivo)

coincidencias = list(re.finditer(r"2351", texto, re.IGNORECASE))

print("TOTAL DE MENCIONES A 2351:", len(coincidencias))

for i, match in enumerate(coincidencias[:20], 1):

    inicio = max(0, match.start() - 250)
    final = min(len(texto), match.end() + 500)

    contexto = texto[inicio:final]

    paginas = re.findall(
        r"\[PAGINA PDF: (\d+)\]",
        texto[:match.start()]
    )

    pagina = paginas[-1] if paginas else "No identificada"

    print("\n" + "=" * 70)
    print("COINCIDENCIA:", i)
    print("PAGINA PDF:", pagina)
    print("=" * 70)
    print(contexto)
