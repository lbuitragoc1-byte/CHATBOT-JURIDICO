
from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st
from dotenv import load_dotenv

from app.processing_v2 import (
    read_document,
    chunk_text,
    extract_entities
)

from app.retrieval import Retriever
from app.generation import generate_answer


load_dotenv()


# ----------------------------------------------------
# 1. CONFIGURACION GENERAL
# ----------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

LIBRARY_DIR = (
    BASE_DIR / "data" / "biblioteca_juridica"
)

st.set_page_config(
    page_title="Chatbot Jurídico Inteligente",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ Chatbot Jurídico Inteligente")

st.caption(
    "Prototipo universitario · Colombia · "
    "Consultas fundamentadas en documentos jurídicos"
)


# ----------------------------------------------------
# 2. INICIALIZAR RETRIEVER
# ----------------------------------------------------

@st.cache_resource
def retriever():
    return Retriever()


# ----------------------------------------------------
# 3. CARGAR DOCUMENTOS DE LA BIBLIOTECA
# ----------------------------------------------------

def load_library_documents():

    chunks = []

    LIBRARY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    for path in sorted(LIBRARY_DIR.iterdir()):

        if path.suffix.lower() not in [".pdf", ".txt"]:
            continue

        text = read_document(path)

        if not text:
            continue

        for i, piece in enumerate(
            chunk_text(text),
            1
        ):

            chunk = dict(piece)

            chunk["source"] = path.name
            chunk["document"] = path.name
            chunk["number"] = i

            chunks.append(chunk)

    return chunks


# ----------------------------------------------------
# 4. SINCRONIZAR RETRIEVER CON LA BIBLIOTECA
# ----------------------------------------------------

def get_indexed_retriever():

    searcher = retriever()

    current_chunks = st.session_state.chunks

    needs_indexing = (
        len(searcher.chunks) != len(current_chunks)
        or (
            bool(current_chunks)
            and searcher.vectors is None
        )
    )

    if needs_indexing:

        print(
            "\nSincronizando biblioteca con Retriever..."
        )

        searcher.index(current_chunks)

    return searcher


# ----------------------------------------------------
# 5. INICIALIZAR SESSION STATE
# ----------------------------------------------------

if "chunks" not in st.session_state:
    st.session_state.chunks = []

if "messages" not in st.session_state:
    st.session_state.messages = []


# ----------------------------------------------------
# 6. CARGAR BIBLIOTECA PERMANENTE
# ----------------------------------------------------

if "library_initialized" not in st.session_state:

    with st.spinner(
        "Cargando biblioteca jurídica permanente..."
    ):

        permanent_chunks = load_library_documents()

        searcher = retriever()

        if permanent_chunks:
            searcher.index(permanent_chunks)

        st.session_state.chunks = permanent_chunks

        st.session_state.library_initialized = True


# ----------------------------------------------------
# 7. BARRA LATERAL
# ----------------------------------------------------

with st.sidebar:

    st.header("Biblioteca jurídica")

    uploads = st.file_uploader(
        "Sube documentos adicionales",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )

    if st.button(
        "Procesar documentos",
        use_container_width=True
    ):

        if not uploads:

            st.warning(
                "Selecciona al menos un documento."
            )

        else:

            new_chunks = []

            for file in uploads:

                with TemporaryDirectory() as tmp:

                    path = (
                        Path(tmp) /
                        Path(file.name).name
                    )

                    path.write_bytes(
                        file.getvalue()
                    )

                    text = read_document(path)

                if not text:

                    st.warning(
                        f"{file.name}: "
                        "no contiene texto extraíble."
                    )

                    continue

                for i, piece in enumerate(
                    chunk_text(text),
                    1
                ):

                    chunk = dict(piece)

                    chunk["source"] = file.name
                    chunk["document"] = file.name
                    chunk["number"] = i

                    new_chunks.append(chunk)

            if new_chunks:

                all_chunks = (
                    st.session_state.chunks
                    + new_chunks
                )

                with st.spinner(
                    "Actualizando biblioteca y embeddings..."
                ):

                    searcher = retriever()

                    searcher.index(all_chunks)

                st.session_state.chunks = all_chunks

                st.success(
                    f"{len(new_chunks)} nuevos "
                    "fragmentos incorporados."
                )

    st.metric(
        "Fragmentos cargados",
        len(st.session_state.chunks)
    )

    if st.button("Limpiar conversación"):

        st.session_state.messages = []

        st.rerun()

    st.info(
        "No cargues datos personales o expedientes "
        "confidenciales sin autorización."
    )


# ----------------------------------------------------
# 8. PESTAÑAS PRINCIPALES
# ----------------------------------------------------

chat, entities = st.tabs([
    "Chat jurídico",
    "Entidades jurídicas"
])


# ----------------------------------------------------
# 9. CHAT JURIDICO
# ----------------------------------------------------

with chat:

    # Mostrar conversaciones anteriores.

    for msg in st.session_state.messages:

        with st.chat_message(msg["role"]):

            st.markdown(msg["content"])

            if msg.get("hits"):

                with st.expander(
                    "Fragmentos consultados"
                ):

                    for i, h in enumerate(
                        msg["hits"],
                        1
                    ):

                        st.markdown(
                            f"**[{i}] "
                            f"{h.get('source', 'Documento')} · "
                            f"fragmento {h.get('number', '?')}**"
                        )

                        st.caption(
                            h.get("text", "")
                        )

    # Entrada de preguntas.

    question = st.chat_input(
        "Pregunta sobre los documentos..."
    )

    if question:

        st.session_state.messages.append({
            "role": "user",
            "content": question
        })

        with st.chat_message("user"):

            st.markdown(question)

        with st.chat_message("assistant"):

            # Comprobar disponibilidad de documentos.

            if not st.session_state.chunks:

                hits = []

                answer = (
                    "No hay documentos jurídicos "
                    "en la biblioteca."
                )

            else:

                with st.spinner(
                    "Consultando documentos y Gemini..."
                ):

                    # --------------------------------
                    # 9.1 SINCRONIZAR BUSCADOR
                    # --------------------------------

                    searcher = get_indexed_retriever()

                    # --------------------------------
                    # 9.2 DIAGNOSTICO DEL BUSCADOR
                    # --------------------------------

                    print(
                        "\n========== ESTADO DEL BUSCADOR =========="
                    )

                    print(
                        "Fragmentos en Streamlit:",
                        len(st.session_state.chunks)
                    )

                    print(
                        "Fragmentos en Retriever:",
                        len(searcher.chunks)
                    )

                    print(
                        "Vectores cargados:",
                        searcher.vectors is not None
                    )

                    print(
                        "Cantidad de vectores:",
                        len(searcher.vectors)
                        if searcher.vectors is not None
                        else 0
                    )

                    # --------------------------------
                    # 9.3 EJECUTAR BUSQUEDA
                    # --------------------------------

                    hits = searcher.search(question)

                    print(
                        "Resultados recuperados:",
                        len(hits)
                    )

                    print(
                        "=========================================\n"
                    )

                    # --------------------------------
                    # 9.4 ORDENAR PARTES DEL ARTICULO
                    # --------------------------------

                    same_article = False

                    if hits:

                        first_key = (
                            hits[0].get("source"),
                            hits[0].get("article"),
                            hits[0].get("section"),
                            hits[0].get("version")
                        )

                        same_article = all(

                            (
                                h.get("source"),
                                h.get("article"),
                                h.get("section"),
                                h.get("version")

                            ) == first_key

                            for h in hits
                        )

                        if same_article:

                            hits.sort(
                                key=lambda h: int(
                                    h.get("part") or 0
                                )
                            )

                    # --------------------------------
                    # 9.5 GENERAR RESPUESTA
                    # --------------------------------

                    try:

                        answer = generate_answer(
                            question,
                            hits
                        )

                    except Exception as e:

                        answer = (
                            f"No se pudo generar "
                            f"la respuesta: {e}. "
                            "Revisa la conexión con Gemini."
                        )

                # ------------------------------------
                # 9.6 MOSTRAR FRAGMENTOS CONSULTADOS
                # ------------------------------------

                if hits:

                    with st.expander(
                        "Fragmentos consultados"
                    ):

                        for i, h in enumerate(
                            hits,
                            1
                        ):

                            st.markdown(
                                f"**[{i}] "
                                f"{h.get('source', 'Documento')} · "
                                f"fragmento {h.get('number', '?')}**"
                            )

                            st.caption(
                                h.get("text", "")
                            )

            # Mostrar respuesta.

            st.markdown(answer)

        # Guardar respuesta y fragmentos.

        st.session_state.messages.append({

            "role": "assistant",

            "content": answer,

            "hits": hits

        })


# ----------------------------------------------------
# 10. ENTIDADES JURIDICAS
# ----------------------------------------------------

with entities:

    st.caption(
        "Extracción inicial basada en reglas; "
        "todavía no es NER entrenado."
    )

    if not st.session_state.chunks:

        st.info(
            "No hay documentos para analizar."
        )

    else:

        all_text = " ".join(
            x["text"]
            for x in st.session_state.chunks
        )

        for label, items in extract_entities(
            all_text
        ).items():

            st.markdown(
                f"**{label} ({len(items)})**"
            )

            st.write(

                ", ".join(items[:50])
                if items
                else "Sin coincidencias"

            )


# ----------------------------------------------------
# 11. PIE DE PAGINA
# ----------------------------------------------------

st.divider()

st.caption(
    "Sistema experimental: verifica las citas y "
    "la vigencia normativa en fuentes oficiales."
)
