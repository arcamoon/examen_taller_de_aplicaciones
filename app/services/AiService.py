import os
import requests
import json


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def preguntar_ia(mensaje: str, contexto_analisis: dict = None):
    """
    Consulta a la IA con un mensaje opcionalmente enriquecido con contexto de análisis.
    
    Args:
        mensaje: La pregunta o solicitud para la IA
        contexto_analisis: Diccionario opcional con datos estadísticos para contextualizar el análisis
    
    Returns:
        La respuesta de la IA como string
    """
    
    # Prompt base mejorado para rol de analista
    system_prompt = """Eres un analista de datos experto integrado en una aplicación Flask-AppBuilder para gestión de restaurantes.

TU ROL PRINCIPAL:
- Analizar datos estadísticos de reservas, ventas, clientes y platos
- Generar insights accionables y recomendaciones basadas en los datos
- Identificar patrones, tendencias y anomalías
- Comunicar hallazgos de manera clara y profesional

CAPACIDADES DE ANÁLISIS:
1. Análisis General del Sistema:
   - Interpretar métricas clave (ventas totales, usuarios, reservas, productos más vendidos)
   - Evaluar el rendimiento general del negocio
   - Identificar fortalezas y áreas de oportunidad

2. Tendencias y Comportamiento:
   - Detectar patrones temporales (horarios pico, días con mayor actividad)
   - Analizar comportamiento de clientes (frecuencia, preferencias)
   - Identificar servicios/productos con crecimiento o disminución
   - Proyectar tendencias futuras basadas en datos históricos

FORMATO DE RESPUESTA:
- Sé conciso pero informativo
- Usa lenguaje profesional pero accesible
- Destaca los puntos más importantes con viñetas cuando sea relevante
- Proporciona recomendaciones prácticas cuando aplique
- Si hay datos preocupantes, menciónalos de manera constructiva"""

    # Si hay contexto de análisis, enriquecer el mensaje
    if contexto_analisis:
        contexto_json = json.dumps(contexto_analisis, indent=2, ensure_ascii=False)
        mensaje_completo = f"""CONTEXTO DE DATOS DEL SISTEMA:
{contexto_json}

SOLICITUD DE ANÁLISIS:
{mensaje}

Por favor, proporciona un análisis detallado basado en estos datos."""
    else:
        mensaje_completo = mensaje

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-OpenRouter-Title": "Flask FAB App - Analista de Datos",
        },
        data=json.dumps(
            {
                "model": "poolside/laguna-xs.2:free",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {"role": "user", "content": mensaje_completo},
                ],
                "temperature": 0.7,
                "max_tokens": 1500,
            }
        ),
    )

    if response.status_code != 200:
        return f"Error IA: {response.text}"

    data = response.json()

    return data["choices"][0]["message"]["content"]
