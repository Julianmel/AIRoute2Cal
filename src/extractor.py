"""Módulo de extração de dados de capturas da Linha do Tempo usando IA Multimodal."""

import os
import json
from typing import Optional
from PIL import Image
from dotenv import load_dotenv
from .models import TimelineDay

# Carrega as variáveis do .env garantindo atualização
load_dotenv(override=True)

# Prompt de sistema especializado para interpretação da Linha do Tempo do Google Maps
EXTRACTION_PROMPT = """
Você é um especialista em ler e extrair TODAS as informações de capturas de tela do aplicativo Google Maps (seção "Linha do Tempo" / "Timeline").
Analise minuciosamente a imagem fornecida e extraia absolutamente tudo que estiver visível na captura, sem omitir nenhum evento.

DIRETRIZES FUNDAMENTAIS:
1. DATA E RESUMO DO TOPO:
   - Identifique a data do dia informado:
     * Se a tela indicar "Ontem", calcule a data (YYYY-MM-DD) subtraindo 1 dia da data de referência.
     * Se indicar "Hoje", utilize a data de referência.
   - Extraia as estatísticas gerais do topo: quilometragem total de carro e a pé, tempo total dirigindo e caminhando, total de visitas e passos (se houver).
   - summary_stats: copie o resumo completo do cabeçalho (ex: "43 km, 1h 6 min, 5 km, 35 min, 7 visitas").

2. CONFERÊNCIA OBRIGATÓRIA COM OS TOTAIS DO TOPO:
   - ATENÇÃO CRÍTICA: Observe atentamente os ícones e números no resumo no topo da tela.
     * Se houver o ícone de pedestre 🚶 com quilometragem e tempo (ex: "5 km, 35 min"), SIGNIFICA QUE HÁ OBRIGATORIAMENTE UM OU MAIS DESLOCAMENTOS A PÉ NA TELA (ex: "A pé 4,9 km · 35 min" das 17:52 às 18:28).
     * Se houver o ícone de carro 🚗 (ex: "43 km, 1h 6 min"), a soma dos deslocamentos de carro deve bater com esse total.
     * Role visualmente até o fim absoluto da imagem para extrair essa caminhada! NUNCA pare de analisar antes de chegar ao último item do rodapé.

3. TODOS OS DESLOCAMENTOS (NUNCA IGNORE NENHUM MODO):
   - A imagem é uma captura de tela longa de celular (rolagem vertical). VOCÊ DEVE LER DO INÍCIO AO FIM, até a última linha no rodapé da imagem. NUNCA pare no meio!
   - Extraia TODOS os trajetos de movimentação entre locais:
     * A pé / Caminhando (ícone de pedestre 🚶, texto "A pé" ou "Caminhando"). ATENÇÃO: Mesmo que a caminhada seja de ida e volta saindo e voltando para o mesmo ponto (ex: Casa -> Casa), EXTRAIA SEMPRE este deslocamento! É muito comum o trecho "A pé" estar próximo ao final da tela.
     * Não há modo de trajeto (ícone de ponto de interrogação ❓ ou texto "Não há modo de trajeto"). Extraia exatamente com mode="Não há modo de trajeto".
     * Dirigindo / Carro / Moto (ícone de veículo, texto "Dirigindo").
     * Bicicleta / Pedalando.
     * Transporte público (ônibus, metrô, trem).
   - Para CADA deslocamento:
     * mode: informe o modo exato ("A pé", "Caminhando", "Dirigindo", "Não há modo de trajeto", "Bicicleta", etc.).
     * origin_name: local de partida imediatamente anterior.
     * destination_name: próximo local onde chegou.
     * start_time: horário de partida no formato HH:MM (ex: 17:52).
     * end_time: horário de término no formato HH:MM (ex: 18:28).
     * distance_km: distância em km (ex: 4.9). Se estiver em metros, converta para km.
     * duration_min: duração em minutos (ex: 35).
     * details: qualquer nota ou dado visível (ex: passos, calorias, observações).

4. TODAS AS PARADAS, VISITAS E ESTADIAS:
   - Extraia todos os locais visitados (residências, empresas, supermercados, órgãos públicos, etc.).
   - place_name: nome do estabelecimento ou local.
   - address: endereço exibido na tela.
   - start_time e end_time: horário de entrada e saída (HH:MM).
   - duration_min: duração da permanência em minutos, se informada.
   - details: notas ou eventos associados (ex: "Saiu às 07:03", "Chegou às 19:33", etc.).

5. ANOTAÇÕES ADICIONAIS:
   - additional_notes: registre qualquer outro detalhe, nota de viagem ou contexto textual presente na captura.

Devolva a resposta estritamente conforme o esquema JSON especificado.
"""


def extract_timeline_from_image(
    image_path_or_bytes,
    api_key: Optional[str] = None,
    default_date: Optional[str] = None,
    model_name: Optional[str] = None,
) -> TimelineDay:
    """Extrai os dados da linha do tempo da imagem informada usando a API Gemini."""
    model_to_use = model_name or "gemini-3.5-flash-lite"
    key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip().strip('"').strip("'")
    if not key or key == "sua_chave_aqui":
        raise ValueError(
            "Chave de API do Gemini não configurada ou contém o texto de exemplo ('sua_chave_aqui').\n"
            "Crie uma chave gratuita no Google AI Studio (https://aistudio.google.com/) e informe no aplicativo."
        )

    # Carrega a imagem via PIL
    if isinstance(image_path_or_bytes, Image.Image):
        img = image_path_or_bytes
    elif isinstance(image_path_or_bytes, (bytes, bytearray)):
        import io
        img = Image.open(io.BytesIO(image_path_or_bytes))
    else:
        img = Image.open(image_path_or_bytes)

    # Lista de modelos prioritários com fallback automático em caso de sobrecarga temporária (503)
    candidate_models = [model_to_use]
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"]:
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
