
from pathlib import Path
from app.processing import read_document, chunk_text

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

if not archivo.exists():
    print("No se encontró el Código Sustantivo del Trabajo.")
    raise SystemExit

texto = read_document(archivo)
fragmentos = chunk_text(texto)

print("\nDIAGNOSTICO DE FRAGMENTACION")
print("=" * 60)
print("Caracteres originales:", len(texto))
print("Total de fragmentos:", len(fragmentos))

print("\nANALISIS DEL ARTICULO 23")
print("=" * 60)

encontrados = []

for i, fragmento in enumerate(fragmentos, 1):

    if "[ARTÍCULO 23]" in fragmento.upper():

        encontrados.append((i, fragmento))

errores = []

for numero, fragmento in encontrados:

    print(f"\nFRAGMENTO {numero}")
    print("-" * 60)

    if "[CONTENIDO PRINCIPAL" in fragmento.upper():
        categoria = "CONTENIDO PRINCIPAL"

    elif "[CONTENIDO HISTÓRICO]" in fragmento.upper():
        categoria = "CONTENIDO HISTÓRICO"

    else:
        categoria = "SIN CLASIFICAR"

    print("Clasificación:", categoria)

    contiene_historico = (
        "LEGISLACIÓN ANTERIOR" in fragmento.upper()
        or "TEXTO ORIGINAL DEL CODIGO" in fragmento.upper()
    )

    if categoria == "CONTENIDO PRINCIPAL" and contiene_historico:
        errores.append(numero)
        print("ALERTA: contiene un encabezado histórico")

    print(fragmento[:500])

print("\nRESUMEN DE VALIDACION")
print("=" * 60)
print("Fragmentos del artículo 23:", len(encontrados))
print("Posibles errores de clasificación:", len(errores))

if errores:
    print("Fragmentos que requieren revisión:", errores)
else:
    print("No se detectaron estos errores específicos.")
