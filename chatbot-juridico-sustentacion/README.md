# Chatbot Jurídico Inteligente — Versión 0.1

Prototipo universitario en Python con Streamlit, extracción PDF, embeddings multilingües, búsqueda semántica y generación mediante Ollama o una API compatible con OpenAI.

## Instalación en Windows (PowerShell)

1. Descomprime el ZIP en `C:\Proyectos\` para obtener `C:\Proyectos\chatbot-juridico`.
2. Abre esa carpeta en VS Code y abre una terminal PowerShell.
3. Si no tienes entorno virtual: `python -m venv .venv`.
4. Activa el entorno: `.\.venv\Scripts\Activate.ps1`. Si está bloqueado, usa primero `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
5. Instala: `python -m pip install -r requirements.txt`.
6. Copia la configuración: `Copy-Item .env.example .env`.

### IA local (predeterminada)

Instala Ollama desde https://ollama.com y ejecuta `ollama pull llama3.2:3b`. Asegúrate de que Ollama esté ejecutándose. Requiere memoria y espacio suficiente. La primera descarga de embeddings también necesita internet.

### IA mediante API (alternativa)

Edita `.env` y configura `AI_PROVIDER=openai_compatible`, `AI_BASE_URL`, `AI_MODEL` y `AI_API_KEY`. No compartas ni publiques la clave.

## Ejecución

`python -m streamlit run main.py`

Carga PDF/TXT en el panel izquierdo, pulsa **Procesar documentos** y haz preguntas. Ejecuta pruebas con `python -m pytest -q`.

## Alcance y limitaciones

- **Sí** usa un modelo de embeddings de IA y un modelo generativo (Ollama/API) para las respuestas.
- Solo busca en **documentos cargados**, no en internet ni automáticamente en tribunales.
- Las citas `[1]`, `[2]` identifican fragmentos recuperados, no verificaciones independientes de jurisprudencia.
- La extracción de entidades usa **reglas**, no NER entrenado. Pendiente implementar/evaluar un modelo NER.
- PDF escaneados requieren OCR (aún no incluido).
- El índice vectorial es temporal en memoria; se pierde al reiniciar.
- No incluye todavía FastAPI, PostgreSQL, seguridad de producción ni despliegue web.
- No se debe utilizar como asesoría jurídica profesional.

## Próximos pasos

Validar instalación en el computador, incorporar sentencias oficiales y metadatos, medir fidelidad/citas, añadir persistencia y preparar sustentación.
