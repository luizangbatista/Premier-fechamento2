import re
import math
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Fechamento Premier", layout="wide")

st.title("📊 Sistema de Fechamento")

# =========================
# FUNÇÕES DE EXTRAÇÃO (placeholder)
# =========================

def extrair_dados_pdf(file) -> pd.DataFrame:
    """
    Aqui você vai implementar a leitura real do PDF
    """
    # MOCK (substituir depois)
    data = {
        "Nome": ["A", "B"],
        "Valor": [100, -50]
    }
    return pd.DataFrame(data)


def extrair_dados_imagem(file) -> pd.DataFrame:
    """
    Aqui você vai implementar OCR ou parsing da imagem
    """
    # MOCK (substituir depois)
    data = {
        "Nome": ["A", "B"],
        "Ajuste": [10, 5]
    }
    return pd.DataFrame(data)


# =========================
# PROCESSAMENTO
# =========================

def combinar_dados(df_pdf: pd.DataFrame, df_img: pd.DataFrame) -> pd.DataFrame:
    df = pd.merge(df_pdf, df_img, on="Nome", how="left")
    df["Ajuste"] = df["Ajuste"].fillna(0)

    df["Total"] = df["Valor"] + df["Ajuste"]

    # Aplicar 5% se positivo
    df["Bonus 5%"] = df["Total"].apply(lambda x: x * 0.05 if x > 0 else 0)

    df["Final"] = df["Total"] + df["Bonus 5%"]

    return df


# =========================
# UI - Upload
# =========================

col1, col2 = st.columns(2)

with col1:
    pdf_file = st.file_uploader("📄 Enviar PDF", type=["pdf"])

with col2:
    img_file = st.file_uploader("🖼️ Enviar Imagem", type=["png", "jpg", "jpeg"])


# =========================
# PROCESSO PRINCIPAL
# =========================

if pdf_file and img_file:
    st.success("Arquivos carregados!")

    df_pdf = extrair_dados_pdf(pdf_file)
    df_img = extrair_dados_imagem(img_file)

    st.subheader("📌 Dados PDF")
    st.dataframe(df_pdf, use_container_width=True)

    st.subheader("📌 Dados Imagem")
    st.dataframe(df_img, use_container_width=True)

    # =========================
    # COMPLEMENTO MANUAL
    # =========================
    st.subheader("✏️ Ajustes manuais")

    df_pdf_editado = st.data_editor(df_pdf, use_container_width=True)

    # =========================
    # BOTÃO GERAR
    # =========================
    if st.button("🚀 Gerar Relatórios"):

        df_final = combinar_dados(df_pdf_editado, df_img)

        st.subheader("📊 Resultado Final")

        # =========================
        # TABELA ESTILIZADA
        # =========================
        def estilo(df):
            return df.style \
                .format({"Valor": "R$ {:.2f}", "Total": "R$ {:.2f}", "Final": "R$ {:.2f}"}) \
                .applymap(lambda x: "color: green" if isinstance(x, (int, float)) and x > 0 else "color: red")

        st.dataframe(estilo(df_final), use_container_width=True)

        # =========================
        # SEGUNDA TABELA (RESUMO)
        # =========================
        resumo = pd.DataFrame({
            "Métrica": ["Total Geral", "Total Positivos", "Total Negativos"],
            "Valor": [
                df_final["Final"].sum(),
                df_final[df_final["Final"] > 0]["Final"].sum(),
                df_final[df_final["Final"] < 0]["Final"].sum()
            ]
        })

        st.subheader("📈 Resumo")
        st.dataframe(resumo, use_container_width=True)

else:
    st.info("Envie o PDF e a imagem para começar.")