
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("AI_API_KEY")
modelo = "gemini-3.1-flash-lite"

if not api_key:
    print("ERROR: No se encontró la API key.")
    raise SystemExit(1)

url = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{modelo}:generateContent"
)

datos = {
    "contents": [
        {
            "parts": [
                {
                    "text": (
                        "Explica brevemente qué son las "
                        "cesantías en el derecho laboral "
                        "colombiano."
                    )
                }
            ]
        }
    ],
    "generationConfig": {
        "maxOutputTokens": 150
    }
}

try:
    respuesta = requests.post(
        url,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        },
        json=datos,
        timeout=90
    )

    print("Estado HTTP:", respuesta.status_code)

    if respuesta.status_code == 200:
        resultado = respuesta.json()

        for candidato in resultado.get("candidates", []):
            contenido = candidato.get("content", {})

            for parte in contenido.get("parts", []):
                if "text" in parte:
                    print("\nRESPUESTA DE GEMINI:\n")
                    print(parte["text"])
    else:
        error = respuesta.json().get("error", {})
        print("Error:", error.get("message", "Desconocido"))

except requests.exceptions.RequestException as error:
    print("Error de conexión:", type(error).__name__)
