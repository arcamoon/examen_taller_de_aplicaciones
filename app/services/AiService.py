import os
import requests
import json


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def preguntar_ia(mensaje: str):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            # opcionales (no obligatorios, pero recomendados)
            "HTTP-Referer": "http://localhost:5000",
            "X-OpenRouter-Title": "Flask FAB App",
        },
        data=json.dumps(
            {
                "model": "poolside/laguna-xs.2:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "Eres un asistente dentro de una app Flask-AppBuilder.",
                    },
                    {"role": "user", "content": mensaje},
                ],
            }
        ),
    )

    if response.status_code != 200:
        return f"Error IA: {response.text}"

    data = response.json()

    return data["choices"][0]["message"]["content"]
