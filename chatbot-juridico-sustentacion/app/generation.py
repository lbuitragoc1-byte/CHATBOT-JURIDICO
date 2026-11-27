
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 1. CONFIGURACION DE MODELOS
# ============================================================

PRIMARY_MODEL = os.getenv(
    "GEMINI_MODEL_PRIMARY",
    "gemini-3.5-flash-lite"
)

FALLBACK_MODEL = os.getenv(
    "GEMINI_MODEL_FALLBACK",
    "gemini-3.8-flash"
)

TERTIARY_MODEL = os.getenv(
    "GEMINI_MODEL_TERTIARY",
    "gemini-3.1-flash-lite"
)

MODELS = list(dict.fromkeys([
    PRIMARY_MODEL,
    FALLBACK_MODEL,
    TERTIARY_MODEL
]))

MAX_RETRIES = 1
BASE_DELAY_SECONDS = 2

RETRYABLE_STATUS_CODES = {
    408, 429, 500, 502, 503, 504
}


# ============================================================
# 2. INSTRUCCIONES DEL ASISTENTE
# ============================================================


SYSTEM_PROMPT = """
Eres un asistente academico especializado en derecho laboral
individual y legislacion colombiana.

Tu funcion es responder preguntas juridicas utilizando
exclusivamente la informacion de los fragmentos documentales
proporcionados en cada consulta.

REGLAS OBLIGATORIAS:

1. FUENTES:
Utiliza exclusivamente la informacion contenida en los
fragmentos recuperados. No completes respuestas con
conocimientos externos ni inventes informacion.

2. CITAS:
Cita las fuentes utilizando [1], [2], etc.
Cada numero corresponde a la fuente identificada
en el contexto documental.
Toda afirmacion juridica relevante debe estar respaldada
por una cita.

3. VIGENCIA NORMATIVA:
Nunca afirmes que una disposicion esta vigente si su
vigencia no ha sido verificada.

Si el estado es "pendiente_verificacion" o el campo
"vigencia_verificada" indica que no esta verificada,
advierte expresamente esta limitacion.

No confundas una norma pendiente de verificacion
con una norma derogada.

4. LEGISLACION HISTORICA:
Diferencia claramente el texto original, las modificaciones
legislativas y el contenido principal de los documentos.

Nunca presentes una disposicion historica como si fuera
automaticamente la legislacion vigente.

Si el usuario solicita una version historica, responde
utilizando esa version y aclara su caracter historico.

5. REFERENCIAS JURIDICAS:
Diferencia el contenido de los articulos de las notas
de vigencia, concordancias y referencias jurisprudenciales.

No presentes una interpretacion judicial como si fuera
el texto literal de una disposicion legal.

6. LITERALES INTEGRADOS:
Cuando encuentres literales recuperados de versiones
normativas anteriores, identifica su procedencia.

Su integracion documental no significa que su vigencia
este juridicamente comprobada.

7. INFORMACION INSUFICIENTE:
Si los fragmentos no contienen informacion suficiente,
indicalo expresamente.

No inventes articulos, leyes, decretos, sentencias,
fechas ni interpretaciones para completar una respuesta.

8. COMPARACIONES:
Cuando se solicite comparar versiones normativas,
explica las diferencias utilizando las fuentes de cada
version y sin mezclarlas.

9. LENGUAJE:
Explica los conceptos juridicos de manera clara,
ordenada y comprensible para estudiantes.

10. LIMITACIONES:
No ofrezcas asesoria juridica definitiva.
Diferencia las disposiciones legales de las interpretaciones
y advierte cuando no sea posible confirmar su vigencia.

La precision juridica y la fidelidad documental tienen
prioridad sobre la extension de las respuestas.
"""



# ============================================================
# 3. EXCEPCIONES
# ============================================================

class ModelRequestError(Exception):
    pass


class ModelUnavailableError(Exception):
    pass


# ============================================================
# 4. DETALLES DE ERRORES
# ============================================================

def get_error_detail(response):

    try:
        data = response.json()

        return data.get(
            "error", {}
        ).get(
            "message",
            response.text[:1000]
        )

    except ValueError:

        return response.text[:1000]


# ============================================================
# 5. TIEMPO DE ESPERA
# ============================================================

def retry_delay(response, attempt):

    retry_after = response.headers.get("Retry-After")

    if retry_after:

        try:
            return min(max(float(retry_after), 1), 30)

        except ValueError:
            pass

    return BASE_DELAY_SECONDS * (2 ** attempt)


# ============================================================
# 6. CONSTRUIR CONTEXTO JURIDICO
# ============================================================


def build_context(hits):

    documents = []

    for i, hit in enumerate(hits, 1):

        source = (
            hit.get("source")
            or hit.get("document")
            or "Documento no identificado"
        )

        article = hit.get(
            "article",
            "No identificado"
        )

        section = hit.get(
            "section",
            "No identificada"
        )

        version = hit.get(
            "version",
            "No identificada"
        )

        estado_normativo = hit.get(
            "estado_normativo",
            "sin_clasificar"
        )

        vigencia_verificada = hit.get(
            "vigencia_verificada",
            False
        )

        # Normalizar el indicador de verificacion
        if isinstance(vigencia_verificada, str):

            vigencia_verificada = (
                vigencia_verificada.strip().lower()
                in {"true", "1", "si", "sí", "verificado"}
            )

        else:
            vigencia_verificada = bool(
                vigencia_verificada
            )

        # Identificar los literales integrados
        literales = hit.get(
            "literales_integrados",
            {}
        )

        if isinstance(literales, dict) and literales:

            literales_text = "; ".join(
                f"{literal}: recuperado de {origin}"
                for literal, origin in literales.items()
            )

        elif literales:

            literales_text = str(literales)

        else:

            literales_text = "Ninguno identificado"

        number = hit.get(
            "number",
            i
        )

        text = str(
            hit.get("text") or ""
        ).strip()

        if not text:
            continue

        document = f"""
[FUENTE {i}]

Documento: {source}

Articulo: {article}

Seccion: {section}

Version normativa: {version}

Estado normativo: {estado_normativo}

Vigencia verificada: {
    "SI" if vigencia_verificada else "NO VERIFICADA"
}

Literales integrados: {literales_text}

Fragmento: {number}


CONTENIDO JURIDICO:

{text}

"""

        documents.append(document)

    return "\n\n".join(documents)



# ============================================================
# 7. SOLICITUD A GEMINI
# ============================================================

def request_model(model, payload, headers):

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    for attempt in range(MAX_RETRIES + 1):

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(15, 120)
            )

        except requests.RequestException as error:

            if attempt < MAX_RETRIES:

                time.sleep(
                    BASE_DELAY_SECONDS * (2 ** attempt)
                )

                continue

            raise ModelRequestError(
                f"Error de conexion con {model}: {error}"
            ) from error

        # Modelo inexistente o no disponible

        if response.status_code == 404:

            raise ModelUnavailableError(
                f"Modelo {model} no disponible: "
                f"{get_error_detail(response)}"
            )

        # Errores temporales

        if response.status_code in RETRYABLE_STATUS_CODES:

            if attempt < MAX_RETRIES:

                wait = retry_delay(response, attempt)

                time.sleep(wait)

                continue

            raise ModelRequestError(
                f"{model}: HTTP {response.status_code}. "
                f"{get_error_detail(response)}"
            )

        # Otros errores

        if response.status_code >= 400:

            raise ModelRequestError(
                f"{model}: HTTP {response.status_code}. "
                f"{get_error_detail(response)}"
            )

        return response.json()

    raise ModelRequestError(
        f"No se pudo completar la solicitud a {model}."
    )


# ============================================================
# 8. EXTRAER RESPUESTA
# ============================================================

def extract_answer(result, model):

    candidates = result.get("candidates", [])

    if not candidates:

        raise ValueError(
            f"{model} no genero candidatos. "
            f"Detalle: {result.get('promptFeedback', {})}"
        )

    candidate = candidates[0]

    content = candidate.get("content") or {}

    parts = content.get("parts", [])

    answer = "\n".join(
        part["text"]
        for part in parts
        if "text" in part
    )

    if not answer:

        raise ValueError(
            f"{model} devolvio una respuesta vacia. "
            f"Motivo: {candidate.get('finishReason', 'Desconocido')}"
        )

    return answer.strip()


# ============================================================
# 9. GENERAR RESPUESTA JURIDICA
# ============================================================

def generate_answer(question: str, hits: list[dict]) -> str:

    if not hits:

        return (
            "No hay documentos juridicos disponibles "
            "para fundamentar la respuesta."
        )
    
    # ------------------------------------------------
    # FILTRO DE RELEVANCIA DOCUMENTAL
    # ------------------------------------------------

    MIN_RELEVANCE_SCORE = 0.72

    scores = []

    for hit in hits:

        try:
            scores.append(
                float(hit.get("score", 0))
            )

        except (TypeError, ValueError):
            continue

    best_score = max(scores, default=0.0)

    print(
        f"Puntuacion maxima de relevancia: {best_score:.4f}"
    )

    if best_score < MIN_RELEVANCE_SCORE:

        return (
            "No se encontraron fragmentos con suficiente "
            "relevancia para fundamentar una respuesta "
            "juridica a esta pregunta. "
            "La biblioteca documental disponible no "
            "permite responder con suficiente evidencia."
        )


    api_key = os.getenv("AI_API_KEY")

    if not api_key:

        raise ValueError(
            "No se encontro AI_API_KEY en el archivo .env"
        )

    # Construir contexto

    context = build_context(hits)

    if not context:

        return (
            "Los fragmentos recuperados no contienen "
            "texto juridico utilizable."
        )

    # Construir prompt

    prompt = f"""
DOCUMENTOS JURIDICOS RECUPERADOS:

{context}


PREGUNTA DEL USUARIO:

{question}


INSTRUCCIONES:

Responde fundamentandote exclusivamente
en los documentos recuperados.

Incluye citas [1], [2], etc.

Utiliza conjuntamente los fragmentos relacionados.

No inventes informacion que no aparezca
en los documentos.

No mezcles versiones historicas y actuales.

Si se consulta una version original,
respeta estrictamente su contenido.

Si la informacion es insuficiente,
explica que datos hacen falta.

Presenta una respuesta organizada,
clara y facil de comprender.
"""

    payload = {

        "systemInstruction": {
            "parts": [
                {"text": SYSTEM_PROMPT}
            ]
        },

        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt}
                ]
            }
        ],

        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1600
        }
    }

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }

    # Intentar los tres modelos

    errors = []

    for model in MODELS:

        try:

            print(f"Generando respuesta con {model}...")

            result = request_model(
                model,
                payload,
                headers
            )

            answer = extract_answer(
                result,
                model
            )

            print(
                f"Respuesta generada correctamente con {model}."
            )

            return answer

        except (
            ModelRequestError,
            ModelUnavailableError,
            ValueError
        ) as error:

            errors.append(
                f"{model}: {error}"
            )

            print(
                f"Fallo en {model}. Intentando siguiente modelo..."
            )

            continue

    # Ningun modelo disponible

    detail = "\n".join(errors)

    raise RuntimeError(
        "No fue posible generar la respuesta "
        "con ninguno de los modelos disponibles.\n\n"
        f"Detalles:\n{detail}"
    )
