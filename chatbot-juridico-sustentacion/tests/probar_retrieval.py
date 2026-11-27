
from pathlib import Path

from app.processing_v2 import read_document, chunk_text
from app.retrieval import Retriever

archivo = Path(
    "data/biblioteca_juridica/codigo_sustantivo_trabajo.pdf"
)

print("Leyendo documento...")
texto = read_document(archivo)

print("Fragmentando documento...")
fragmentos = chunk_text(texto)

chunks = [
    {
        "source": archivo.name,
        "number": i,
        **fragmento
    }
    for i, fragmento in enumerate(fragmentos, 1)
]

print("Total de fragmentos:", len(chunks))

retriever = Retriever()

print("Indexando...")
retriever.index(chunks)

preguntas = [
    "¿Qué establece el artículo 23 sobre los elementos esenciales del contrato de trabajo?",
    "¿Qué dice el artículo 22 sobre el contrato de trabajo?",
    "¿Qué establece el artículo 24 sobre la presunción del contrato laboral?"
]

for pregunta in preguntas:

    print("\n" + "=" * 65)
    print("PREGUNTA:", pregunta)
    print("=" * 65)

    resultados = retriever.search(pregunta, k=5)

    for resultado in resultados:

        print("\nFragmento:", resultado["number"])
        print("Artículo:", resultado.get("article"))
        print("Sección:", resultado.get("section"))
        print("Versión:", resultado.get("version"))
        print("Puntuación:", round(resultado["score"], 4))
        print(resultado["text"][:700])
