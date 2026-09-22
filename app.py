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

load_dotenv()

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

    api_key_input = st.text_input(
        "Chave Gemini API",
        value=env_key,
        type="password",
        placeholder="AIzaSy...",
        help="Obtenha uma chave gratuita no Google AI Studio (https://aistudio.google.com/).",
    )
    if not api_key_input:
        st.warning("⚠️ Insira sua chave da API do Gemini para processar as imagens.")

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
            if not api_key_input:
                st.error("Informe sua chave de API do Gemini na barra lateral para prosseguir.")
            else:
                with st.spinner("Analisando captura com Gemini Vision..."):
                    try:
                        timeline = extract_timeline_from_image(
                            image,
                            api_key=api_key_input,
                            default_date=str(ref_date),
                            model_name=model_choice,
                        )
                        st.session_state["timeline_result"] = timeline
                        st.success("Dados extraídos com sucesso!")
                    except Exception as err:
                        st.error(f"Erro ao processar imagem: {err}")

        if "timeline_result" in st.session_state:
            timeline = st.session_state["timeline_result"]

            if timeline.summary_stats:
                st.info(f"📊 **Resumo do Cabeçalho da Imagem:** {timeline.summary_stats}")

            # Métricas
            driving_disps = [d for d in timeline.displacements if "caminh" not in (d.mode or "").lower() and "pé" not in (d.mode or "").lower()]
            walking_disps = [d for d in timeline.displacements if "caminh" in (d.mode or "").lower() or "pé" in (d.mode or "").lower()]

            total_km = timeline.total_km or sum((d.distance_km or 0.0) for d in timeline.displacements)
            driving_km = sum((d.distance_km or 0.0) for d in driving_disps)
            total_reimbursement = driving_km * cost_per_km
            total_driving_min = timeline.total_driving_min or sum((d.duration_min or 0) for d in driving_disps)
            total_walking_min = timeline.total_walking_min or sum((d.duration_min or 0) for d in walking_disps)

            m_cols = st.columns(5)
            m_cols[0].metric("Data", timeline.date)
            m_cols[1].metric("Distância Total", f"{format_decimal_br(total_km)} km")
            m_cols[2].metric("Tempo Dirigindo", f"{total_driving_min // 60}h {total_driving_min % 60}m")
            if total_walking_min > 0 or timeline.total_steps:
                steps_str = f" ({timeline.total_steps} passos)" if timeline.total_steps else ""
                m_cols[3].metric("Tempo a Pé", f"{total_walking_min} min{steps_str}")
            else:
                m_cols[3].metric("Visitas Registradas", len(timeline.visits))
            m_cols[4].metric("Reembolso (Carro)", format_currency_br(total_reimbursement))

            st.markdown("### 🚦 Todos os Deslocamentos Identificados (Carro, A Pé, etc.)")
            if timeline.displacements:
                from src.calendar_generator import _get_mode_icon

                disp_rows = [
                    {
                        "Modo": f"{_get_mode_icon(d.mode)} {d.mode}",
                        "Início": d.start_time,
                        "Fim": d.end_time,
                        "Duração": f"{d.duration_min} min" if d.duration_min is not None else "-",
                        "Distância": f"{format_decimal_br(d.distance_km)} km" if d.distance_km is not None else "-",
                        "Origem": d.origin_name,
                        "Destino": d.destination_name,
                        "Detalhes / Notas": d.details or "-",
                    }
                    for d in timeline.displacements
                ]
                st.dataframe(pd.DataFrame(disp_rows), use_container_width=True)
            else:
                st.info("Nenhum deslocamento identificado nesta captura.")

            st.markdown("### 📍 Visitas, Paradas e Estadias")
            if timeline.visits:
                visit_rows = [
                    {
                        "Chegada": v.start_time,
                        "Saída": v.end_time,
                        "Duração": f"{v.duration_min} min" if v.duration_min else "-",
                        "Local": v.place_name,
                        "Endereço": v.address or "-",
                        "Observações": v.details or "-",
                    }
                    for v in timeline.visits
                ]
                st.dataframe(pd.DataFrame(visit_rows), use_container_width=True)

            if timeline.additional_notes:
                with st.expander("📝 Informações e Notas Adicionais da Imagem"):
                    st.write(timeline.additional_notes)

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
