
from pathlib import Path
from app.processing_v2 import read_document, detect_articles

text = read_document(
    Path("data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf")
)

needle = "ARTICULO 24. TRABAJADORES AMPARADOS"
position = text.find(needle)

print("POSICION:", position)

if position == -1:
    print("No se encontró el encabezado")
    raise SystemExit

groups = detect_articles(text)

for group in groups:

    if group["start"] <= position < group["end"]:

        print("\nARTICULO AL QUE FUE ASIGNADO:")
        print(group["article"])

        print("\nINICIO DEL GRUPO:")
        print(text[group["start"]:group["start"] + 700])

        print("\nCONTEXTO DEL ENCABEZADO HISTORICO:")
        print(text[max(0, position - 1000):position + 1800])

        break
