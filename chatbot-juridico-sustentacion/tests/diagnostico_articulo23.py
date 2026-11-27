
from pathlib import Path
from app.processing import read_document

carpeta = Path("data/biblioteca_juridica")
archivos = list(carpeta.glob("*.pdf"))

if not archivos:
    print("No se encontraron archivos PDF.")
    raise SystemExit

for archivo in archivos:
    print(f"\nDOCUMENTO: {archivo.name}")

    texto = read_document(archivo)
    texto_mayus = texto.upper()

    print("Caracteres extraídos:", len(texto))

    terminos = [
        "ARTÍCULO 23",
        "ARTICULO 23",
        "ELEMENTOS ESENCIALES",
        "PRESTACIÓN PERSONAL DEL SERVICIO",
        "SUBORDINACIÓN",
        "REMUNERACIÓN"
    ]

    for termino in terminos:
        posiciones = []
        inicio = 0

        while True:
            posicion = texto_mayus.find(termino, inicio)

            if posicion == -1:
                break

            posiciones.append(posicion)
            inicio = posicion + len(termino)

        print(f"\n{termino}: {len(posiciones)} coincidencias")

        for posicion in posiciones[:5]:
            fragmento = texto[
                max(0, posicion - 250):
                min(len(texto), posicion + 650)
            ]
            print("\n--- CONTENIDO ENCONTRADO ---")
            print(fragmento)
