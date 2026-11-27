
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("AI_API_KEY")

if not api_key:
    print("No se encontró la clave de API.")
    raise SystemExit(1)

url = "https://generativelanguage.googleapis.com/v1beta/models"

try:
    response = requests.get(
        url,
        headers={"x-goog-api-key": api_key},
        timeout=30
    )

    print("Estado HTTP:", response.status_code)

    if response.status_code == 200:
        modelos = response.json().get("models", [])

        print("\nMODELOS DISPONIBLES PARA GENERAR TEXTO:\n")

        for modelo in modelos:
            metodos = modelo.get(
                "supportedGenerationMethods", []
            )

            if "generateContent" in metodos:
                print(modelo["name"])
    else:
        print("No fue posible consultar los modelos.")
        print("Revisa la configuración de tu clave.")

except requests.exceptions.RequestException as error:
    print("Error de conexión:", type(error).__name__)
