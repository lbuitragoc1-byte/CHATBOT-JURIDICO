
from pathlib import Path

from app.generation import generate_answer
from app.processing_v2 import read_document, chunk_text
from app.retrieval import Retriever


# ============================================================
# 1. CONFIGURACION DE LA BIBLIOTECA
# ============================================================

CARPETA = Path("data/biblioteca_juridica")

archivos = sorted(
    CARPETA.glob("*.pdf"),
    key=lambda archivo: archivo.name.lower()
)

if not archivos:
    print("No se encontraron documentos PDF.")
    raise SystemExit(1)


# ============================================================
# 2. PROCESAMIENTO DE TODOS LOS DOCUMENTOS
# ============================================================

chunks = []

print("\nPROCESANDO BIBLIOTECA JURIDICA\n")

for archivo in archivos:

    print(f"Documento: {archivo.name}")

    try:

        texto = read_document(archivo)

        fragmentos = chunk_text(texto)

        for i, fragmento in enumerate(fragmentos, 1):

            chunk = dict(fragmento)

            # Identificacion de la fuente
            chunk["source"] = archivo.name
            chunk["document"] = archivo.name

            # Numero de fragmento dentro del documento
            chunk["number"] = i

            chunks.append(chunk)

        print(
            f"Fragmentos generados: {len(fragmentos)}"
        )

    except Exception as error:

        print(
            f"ERROR procesando {archivo.name}: {error}"
        )


# ============================================================
# 3. RESUMEN DE LA BIBLIOTECA
# ============================================================

print("\n" + "=" * 60)

print("RESUMEN DE LA BIBLIOTECA")

print("=" * 60)

print("Documentos encontrados:", len(archivos))
print("Fragmentos preparados:", len(chunks))

if not chunks:
    print("No hay fragmentos para indexar.")
    raise SystemExit(1)


# ============================================================
# 4. CREACION E INDEXACION DEL BUSCADOR
# ============================================================

retriever = Retriever()

print("\nINDEXANDO DOCUMENTOS...")

retriever.index(chunks)

print("Indexacion terminada correctamente.")


# ============================================================
# 5. CONSULTA DE PRUEBA
# ============================================================



pregunta = (
    "¿Qué trabajadores estaban amparados por "
    "el fuero sindical según el texto original "
    "del artículo 406 del Código Sustantivo "
    "del Trabajo?"
)



print("\n" + "=" * 60)

print("PREGUNTA:", pregunta)

print("=" * 60)

resultados = retriever.search(
    pregunta,
    k=20
)


# ============================================================
# 6. PRESENTACION DE RESULTADOS
# ============================================================

if not resultados:

    print("\nNO SE ENCONTRARON RESULTADOS.")

else:

    print("\nRESULTADOS ENCONTRADOS:", len(resultados))

    for i, resultado in enumerate(resultados, 1):

        print("\n" + "-" * 60)

        print("RESULTADO:", i)

        print("DOCUMENTO:", resultado.get("source"))

        print("ARTICULO:", resultado.get("article"))

        print("SECCION:", resultado.get("section"))

        print("VERSION:", resultado.get("version"))

        print("FRAGMENTO:", resultado.get("number"))

        print(
            "PUNTUACION:",
            round(resultado.get("score", 0), 4)
        )

        print("\nCONTENIDO:\n")

        print(resultado["text"])

        print("-" * 60)

        print("\n" + "=" * 60)
print("RESPUESTA GENERADA POR GEMINI")
print("=" * 60)

try:
    respuesta = generate_answer(pregunta, resultados)
    print(respuesta)

except Exception as e:
    print("ERROR AL GENERAR RESPUESTA:")
    print(e)
