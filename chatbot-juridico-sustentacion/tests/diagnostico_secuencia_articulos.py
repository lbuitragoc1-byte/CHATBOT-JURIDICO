
from pathlib import Path
from app.processing_v2 import read_document, ARTICLE_PATTERN

text = read_document(
    Path("data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf")
)

position = 1103933

start = max(0, position - 15000)

matches = list(
    ARTICLE_PATTERN.finditer(text, start, position + 1000)
)

print("ENCABEZADOS ANTERIORES AL ARTICULO 24")
print("=" * 70)

for match in matches[-18:]:

    print("\nPOSICION:", match.start())
    print("NUMERO:", match.group(1))
    print("ENCABEZADO:", match.group(0).strip())

    previous = text[max(0, match.start() - 350):match.start()]

    print("CONTEXTO ANTERIOR:")
    print(previous[-250:].strip())

print("\n" + "=" * 70)
print("FIN DEL DIAGNOSTICO")

