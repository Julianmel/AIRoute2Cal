"""Aplicação Web Streamlit do AIRoute2Cal."""

import os
from datetime import date
from io import BytesIO
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from src.extractor import extract_timeline_from_image
from src.calendar_generator import generate_ics, generate_outlook_csv

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
                        )
                        st.session_state["timeline_result"] = timeline
                        st.success("Dados extraídos com sucesso!")
                    except Exception as err:
                        st.error(f"Erro ao processar imagem: {err}")

        if "timeline_result" in st.session_state:
            timeline = st.session_state["timeline_result"]

            # Métricas
            total_km = timeline.total_km or sum(d.distance_km for d in timeline.displacements)
            total_reimbursement = total_km * cost_per_km
            total_duration = timeline.total_driving_min or sum(d.duration_min for d in timeline.displacements)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Data", timeline.date)
            m2.metric("Distância Total", f"{total_km:.1f} km")
            m3.metric("Tempo Dirigindo", f"{total_duration // 60}h {total_duration % 60}m")
            m4.metric("Reembolso Estimado", f"R$ {total_reimbursement:.2f}")

            st.markdown("### 🚗 Deslocamentos Identificados")
            if timeline.displacements:
                disp_rows = [
                    {
                        "Início": d.start_time,
                        "Fim": d.end_time,
                        "Duração": f"{d.duration_min} min",
                        "Distância": f"{d.distance_km:.1f} km",
                        "Origem": d.origin_name,
                        "Destino": d.destination_name,
                    }
                    for d in timeline.displacements
                ]
                st.dataframe(pd.DataFrame(disp_rows), use_container_width=True)
            else:
                st.info("Nenhum deslocamento de carro identificado nesta captura.")

            st.markdown("### 📍 Visitas e Permanências")
            if timeline.visits:
                visit_rows = [
                    {
                        "Chegada": v.start_time,
                        "Saída": v.end_time,
                        "Duração": f"{v.duration_min} min" if v.duration_min else "-",
                        "Local": v.place_name,
                        "Endereço": v.address or "-",
                    }
                    for v in timeline.visits
                ]
                st.dataframe(pd.DataFrame(visit_rows), use_container_width=True)

            st.markdown("### 📥 Exportar para o Outlook")
            c1, c2, c3 = st.columns(3)

            # ICS apenas deslocamentos
            ics_disp = generate_ics(timeline, include_displacements=True, include_visits=False)
            c1.download_button(
                label="📅 Baixar .ICS (Apenas Deslocamentos)",
                data=ics_disp.encode("utf-8"),
                file_name=f"deslocamentos_{timeline.date}.ics",
                mime="text/calendar",
            )

            # ICS completo
            ics_all = generate_ics(timeline, include_displacements=True, include_visits=True)
            c2.download_button(
                label="📅 Baixar .ICS (Completo: Trajetos + Visitas)",
                data=ics_all.encode("utf-8"),
                file_name=f"linha_do_tempo_completa_{timeline.date}.ics",
                mime="text/calendar",
            )

            # CSV Outlook
            csv_data = generate_outlook_csv(timeline, include_displacements=True, include_visits=False)
            c3.download_button(
                label="📊 Baixar .CSV (Assistente Outlook)",
                data=csv_data.encode("utf-8"),
                file_name=f"deslocamentos_{timeline.date}.csv",
                mime="text/csv",
            )
