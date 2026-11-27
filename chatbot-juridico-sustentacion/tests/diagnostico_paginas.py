
from pathlib import Path
import re
import fitz

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

patron = re.compile(
    r"(?im)^[ \t]*ART[IÍ]CULO\s+(22|23|24)\b[^\n]*"
)

with fitz.open(str(archivo)) as documento:

    print("DIAGNOSTICO POR PAGINAS")
    print("=" * 65)

    for numero, pagina in enumerate(documento, 1):

        texto = pagina.get_text("text")

        coincidencias = list(patron.finditer(texto))

        for coincidencia in coincidencias:

            print(f"\nPAGINA PDF: {numero}")
            print("ENCABEZADO:", coincidencia.group(0))

            inicio = max(0, coincidencia.start() - 250)
            final = min(
                len(texto),
                coincidencia.end() + 450
            )

            print(texto[inicio:final])
            print("-" * 65)
