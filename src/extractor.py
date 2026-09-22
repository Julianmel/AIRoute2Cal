"""Módulo de extração de dados de capturas da Linha do Tempo usando IA Multimodal."""

import os
import json
from typing import Optional
from PIL import Image
from .models import TimelineDay

# Prompt de sistema especializado para interpretação da Linha do Tempo do Google Maps
EXTRACTION_PROMPT = """
Você é um especialista em ler capturas de tela do aplicativo Google Maps (seção "Linha do Tempo" / "Timeline").
Analise cuidadosamente a imagem fornecida e extraia todos os dados de deslocamentos e visitas.

Diretrizes:
1. Identifique a data do dia reportado (ex: "Hoje", datas explícitas, ou infira pelo contexto/nome se fornecido). Se não houver data explícita, use a data informada no cabeçalho ou parâmetro.
2. Identifique a quilometragem total e o tempo total dirigindo no resumo superior, se presente.
3. Para cada trecho de carro ("Dirigindo" ou ícone de carro):
   - Local de Origem: o local de onde o veículo partiu imediatamente antes.
   - Local de Destino: o próximo local de parada onde chegou.
   - Horário de início e término no formato HH:MM (ex: 07:03 até 07:25).
   - Distância em km (número decimal, ex: 11.0).
   - Duração em minutos (número inteiro, ex: 22).
4. Para cada parada/visita (ícones de pin, loja, casa, etc.):
   - Nome do local (ex: Casa, Supermercado Portal, etc.).
   - Endereço completo visível.
   - Horário de permanência (início e fim no formato HH:MM).
   - Duração em minutos, se informada.
5. Devolva a resposta estritamente no esquema JSON especificado.
"""


def extract_timeline_from_image(
    image_path_or_bytes,
    api_key: Optional[str] = None,
    default_date: Optional[str] = None,
    model_name: Optional[str] = None,
) -> TimelineDay:
    """Extrai os dados da captura de tela do Google Maps usando a API Gemini.

    Args:
        image_path_or_bytes: Caminho do arquivo ou instância PIL.Image / bytes.
        api_key: Chave da API do Google Gemini (se None, lê de GEMINI_API_KEY).
        default_date: Data padrão no formato YYYY-MM-DD caso a tela mostre apenas "Hoje".
        model_name: Nome do modelo de visão (padrão: gemini-3.6-flash).

    Returns:
        TimelineDay: Instância tipada contendo os deslocamentos e visitas extraídos.
    """
    model_to_use = model_name or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip().strip('"').strip("'")
    if not key or key == "sua_chave_aqui":
        raise ValueError(
            "Chave de API do Gemini não configurada ou contém o texto de exemplo ('sua_chave_aqui').\n"
            "Crie uma chave gratuita no Google AI Studio (https://aistudio.google.com/) e informe no aplicativo."
        )

    # Carrega a imagem via PIL
    if isinstance(image_path_or_bytes, Image.Image):
        img = image_path_or_bytes
    else:
        img = Image.open(image_path_or_bytes)

    # Lista de modelos prioritários com fallback automático em caso de sobrecarga (503) ou descontinuação (404)
    candidate_models = [model_to_use]
    for m in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-3-flash", "gemini-1.5-pro"]:
        if m not in candidate_models:
            candidate_models.append(m)

    last_error = None

    for current_model in candidate_models:
        for attempt in range(2):  # tenta até 2 vezes por modelo antes de passar para o fallback
            try:
                # Tenta usar a biblioteca mais recente google-genai
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=key)
                    prompt_with_date = EXTRACTION_PROMPT
                    if default_date:
                        prompt_with_date += f"\nObservação: A data de referência é {default_date}."

                    response = client.models.generate_content(
                        model=current_model,
                        contents=[img, prompt_with_date],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=TimelineDay,
                        ),
                    )
                    return TimelineDay.model_validate_json(response.text)

                except ImportError:
                    # Fallback para google.generativeai caso instalado
                    import google.generativeai as legacy_genai

                    legacy_genai.configure(api_key=key)
                    model = legacy_genai.GenerativeModel(current_model)

                    prompt_with_date = (
                        EXTRACTION_PROMPT
                        + "\nRetorne um JSON válido correspondente ao seguinte esquema Pydantic:\n"
                        + json.dumps(TimelineDay.model_json_schema(), ensure_ascii=False)
                    )
                    if default_date:
                        prompt_with_date += f"\nObservação: A data de referência é {default_date}."

                    response = model.generate_content(
                        [img, prompt_with_date],
                        generation_config={"response_mime_type": "application/json"},
                    )
                    return TimelineDay.model_validate_json(response.text)

            except Exception as e:
                err_str = str(e)
                last_error = e
                # Se for erro transitório de sobrecarga (503) ou modelo não encontrado (404), aguarda ou tenta o próximo
                if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                    import time
                    time.sleep(1.5)
                    continue
                elif "404" in err_str or "NOT_FOUND" in err_str:
                    break  # passa direto para o próximo modelo candidato
                else:
                    # Se for outro erro (ex: chave inválida), propaga imediatamente
                    raise e

    raise RuntimeError(
        f"Não foi possível processar a imagem após tentar os modelos {candidate_models}.\n"
        f"Último erro recebido: {last_error}"
    )
