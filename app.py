"""Aplicação Web Streamlit do AIRoute2Cal."""

import os
from datetime import date
from io import BytesIO
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from src.extractor import extract_timeline_from_image
try:
    from src.calendar_generator import (
        generate_ics,
        generate_outlook_csv,
        format_decimal_br,
        format_currency_br,
    )
except ImportError:
    from src.calendar_generator import generate_ics, generate_outlook_csv

    def format_decimal_br(value, decimals=1):
        if value is None:
            return "-"
        return f"{value:.{decimals}f}".replace(".", ",")

    def format_currency_br(value):
        if value is None:
            return "R$ 0,00"
        return f"R$ {value:.2f}".replace(".", ",")

env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_file_path, override=True)

st.set_page_config(
    page_title="AIRoute2Cal - Google Maps para Outlook",
    page_icon="📍",
    layout="wide",
)

st.title("📍 AIRoute2Cal")
st.caption("Converta capturas da Linha do Tempo do Google Maps em eventos no Calendário do Outlook com IA.")

# Barra lateral de configurações
with st.sidebar:
    st.header("⚙️ Configurações")
    env_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if env_key == "sua_chave_aqui":
        env_key = ""

    if env_key:
        st.success("✅ Chave da API carregada do `.env`")
        api_key_input = st.text_input(
            "Chave Gemini API",
            value=env_key,
            type="password",
            help="Chave carregada automaticamente do arquivo .env. Você pode alterar aqui se quiser.",
        )
    else:
        api_key_input = st.text_input(
            "Chave Gemini API",
            value="",
            type="password",
            placeholder="AIzaSy...",
            help="Obtenha uma chave gratuita no Google AI Studio (https://aistudio.google.com/).",
        )
        st.warning("⚠️ Insira sua chave da API do Gemini para processar as imagens.")

    active_api_key = (api_key_input or env_key).strip().strip('"').strip("'")

    model_choice = st.selectbox(
        "Modelo Gemini",
        options=["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"],
        index=0,
        help="Modelo multimodal do Google. gemini-3.5-flash-lite é ultra-rápido e tem alta disponibilidade.",
    )
    ref_date = st.date_input("Data de Referência (caso na tela diga 'Hoje')", value=date.today())
    cost_per_km = st.number_input(
        "Reembolso por km rodado (R$/km)",
        min_value=0.0,
        value=1.20,
        step=0.05,
        help="Usado para estimar o valor total de reembolso por deslocamento.",
    )
    st.markdown("---")
    st.markdown(
        "🔗 **Repositório:** [GitHub Julianmel/AIRoute2Cal](https://github.com/Julianmel/AIRoute2Cal)"
    )

# Upload ou colagem de imagem
uploaded_file = st.file_uploader(
    "Carregue a captura de tela da Linha do Tempo (JPEG ou PNG):",
    type=["jpg", "jpeg", "png"],
)

if uploaded_file:
    col_img, col_data = st.columns([1, 2])

    image = Image.open(uploaded_file)
    with col_img:
        st.subheader("Captura Carregada")
        st.image(image, use_container_width=True)

    with col_data:
        st.subheader("Processamento com IA")
        if st.button("🚀 Extrair Deslocamentos e Paradas", type="primary"):
            if not active_api_key or active_api_key == "sua_chave_aqui":
                st.error("Informe sua chave de API do Gemini na barra lateral ou no arquivo .env para prosseguir.")
            else:
                with st.spinner("Analisando captura com Gemini Vision..."):
                    try:
                        timeline = extract_timeline_from_image(
                            image,
                            api_key=active_api_key,
                            default_date=str(ref_date),
                            model_name=model_choice,
                        )
                        st.session_state["timeline_result"] = timeline
                        st.success("Dados extraídos com sucesso!")
                    except Exception as err:
                        st.error(f"Erro ao processar imagem: {err}")

        if "timeline_result" in st.session_state:
            timeline = st.session_state["timeline_result"]

            summary_stats = getattr(timeline, "summary_stats", None)
            if summary_stats:
                st.info(f"📊 **Resumo do Cabeçalho da Imagem:** {summary_stats}")

            # Métricas
            displacements = getattr(timeline, "displacements", [])
            visits = getattr(timeline, "visits", [])

            driving_disps = [d for d in displacements if "caminh" not in getattr(d, "mode", "dirigindo").lower() and "pé" not in getattr(d, "mode", "dirigindo").lower()]
            walking_disps = [d for d in displacements if "caminh" in getattr(d, "mode", "dirigindo").lower() or "pé" in getattr(d, "mode", "dirigindo").lower()]

            total_km = getattr(timeline, "total_km", None) or sum((getattr(d, "distance_km", 0.0) or 0.0) for d in displacements)
            driving_km = sum((getattr(d, "distance_km", 0.0) or 0.0) for d in driving_disps)
            total_reimbursement = driving_km * cost_per_km
            total_driving_min = getattr(timeline, "total_driving_min", None) or sum((getattr(d, "duration_min", 0) or 0) for d in driving_disps)
            total_walking_min = getattr(timeline, "total_walking_min", None) or sum((getattr(d, "duration_min", 0) or 0) for d in walking_disps)
            total_steps = getattr(timeline, "total_steps", None)

            m_cols = st.columns(5)
            m_cols[0].metric("Data", getattr(timeline, "date", "-"))
            m_cols[1].metric("Distância Total", f"{format_decimal_br(total_km)} km")
            m_cols[2].metric("Tempo Dirigindo", f"{total_driving_min // 60}h {total_driving_min % 60}m")
            if total_walking_min > 0 or total_steps:
                steps_str = f" ({total_steps} passos)" if total_steps else ""
                m_cols[3].metric("Tempo a Pé", f"{total_walking_min} min{steps_str}")
            else:
                m_cols[3].metric("Visitas Registradas", len(visits))
            m_cols[4].metric("Reembolso (Carro)", format_currency_br(total_reimbursement))

            st.markdown("### 🚦 Todos os Deslocamentos Identificados (Carro, A Pé, etc.)")
            if displacements:
                from src.calendar_generator import _get_mode_icon

                disp_rows = [
                    {
                        "Modo": f"{_get_mode_icon(getattr(d, 'mode', 'Dirigindo'))} {getattr(d, 'mode', 'Dirigindo')}",
                        "Início": getattr(d, "start_time", "-"),
                        "Fim": getattr(d, "end_time", "-"),
                        "Duração": f"{getattr(d, 'duration_min', '-')} min" if getattr(d, "duration_min", None) is not None else "-",
                        "Distância": f"{format_decimal_br(getattr(d, 'distance_km', None))} km" if getattr(d, "distance_km", None) is not None else "-",
                        "Origem": getattr(d, "origin_name", "-"),
                        "Destino": getattr(d, "destination_name", "-"),
                        "Detalhes / Notas": getattr(d, "details", "-") or "-",
                    }
                    for d in displacements
                ]
                st.dataframe(pd.DataFrame(disp_rows), use_container_width=True)
            else:
                st.info("Nenhum deslocamento identificado nesta captura.")

            st.markdown("### 📍 Visitas, Paradas e Estadias")
            if visits:
                visit_rows = [
                    {
                        "Chegada": getattr(v, "start_time", "-"),
                        "Saída": getattr(v, "end_time", "-"),
                        "Duração": f"{getattr(v, 'duration_min', '-')} min" if getattr(v, "duration_min", None) else "-",
                        "Local": getattr(v, "place_name", "-"),
                        "Endereço": getattr(v, "address", "-") or "-",
                        "Observações": getattr(v, "details", "-") or "-",
                    }
                    for v in visits
                ]
                st.dataframe(pd.DataFrame(visit_rows), use_container_width=True)

            additional_notes = getattr(timeline, "additional_notes", None)
            if additional_notes:
                with st.expander("📝 Informações e Notas Adicionais da Imagem"):
                    st.write(additional_notes)

            st.markdown("### 📥 Exportar para o Outlook")
            c1, c2, c3 = st.columns(3)

            # ICS apenas deslocamentos (todos os modos)
            ics_disp = generate_ics(timeline, include_displacements=True, include_visits=False)
            c1.download_button(
                label="📅 Baixar .ICS (Deslocamentos: Carro + A Pé)",
                data=ics_disp.encode("utf-8"),
                file_name=f"deslocamentos_{timeline.date}.ics",
                mime="text/calendar",
            )

            # ICS completo (deslocamentos + visitas)
            ics_all = generate_ics(timeline, include_displacements=True, include_visits=True)
            c2.download_button(
                label="📅 Baixar .ICS (Completo: Trajetos + Visitas)",
                data=ics_all.encode("utf-8"),
                file_name=f"linha_do_tempo_completa_{timeline.date}.ics",
                mime="text/calendar",
            )

            # CSV Outlook
            csv_data = generate_outlook_csv(timeline, include_displacements=True, include_visits=True)
            c3.download_button(
                label="📊 Baixar .CSV (Assistente Outlook)",
                data=csv_data.encode("utf-8"),
                file_name=f"linha_do_tempo_{timeline.date}.csv",
                mime="text/csv",
            )
