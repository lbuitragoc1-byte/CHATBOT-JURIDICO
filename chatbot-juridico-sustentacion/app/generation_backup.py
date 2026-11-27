
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
Eres un asistente academico especializado en derecho
laboral y legislacion colombiana.

REGLAS:

1. Responde exclusivamente con base en los documentos
   juridicos proporcionados.

2. Cita las fuentes utilizando [1], [2], etc.

3. No inventes leyes, articulos, sentencias ni referencias.

4. Si la informacion es insuficiente, indicalo claramente.

5. Explica los conceptos juridicos con lenguaje claro.

6. No ofrezcas asesoria juridica definitiva.

7. Diferencia las disposiciones legales de las interpretaciones.

8. Respeta las versiones normativas indicadas en los documentos.

9. No mezcles legislacion historica con legislacion vigente.

10. Utiliza conjuntamente los fragmentos que pertenezcan
    al mismo articulo cuando sea necesario.

11. Si existen contradicciones entre documentos,
    informalas expresamente.
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

        source = hit.get(
            "source",
            "Documento no identificado"
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

        number = hit.get(
            "number",
            i
        )

        text = hit.get("text", "").strip()

        if not text:
            continue

        document = f"""
[FUENTE {i}]
Documento: {source}
Articulo: {article}
Seccion: {section}
Version: {version}
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
