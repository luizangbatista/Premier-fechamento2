import pandas as pd
import streamlit as st

st.set_page_config(page_title="Fechamento", layout="wide")

st.title("📊 Sistema de Fechamento")

# =========================
# CONFIGURAÇÃO
# =========================

tipo = st.selectbox(
    "Tipo de fechamento",
    ["Demetra", "Alex"],
    key="tipo"
)

aplicar_5 = st.checkbox(
    "Aplicar 5%",
    value=(tipo == "Alex"),
    key="aplicar_5"
)

# =========================
# TABELA EDITÁVEL
# =========================

st.subheader("✏️ Dados dos agentes")

df = pd.DataFrame({
    "Nome": [""],
    "ID": [""],
    "Ganhos": [0.0],
    "Rake": [0.0],
    "% RB": [0.30],
})

df_editado = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    key="tabela_principal"
)

# =========================
# PROCESSAMENTO
# =========================

def calcular(df):
    df = df.copy()

    df["Ganhos"] = pd.to_numeric(df["Ganhos"], errors="coerce").fillna(0)
    df["Rake"] = pd.to_numeric(df["Rake"], errors="coerce").fillna(0)
    df["% RB"] = pd.to_numeric(df["% RB"], errors="coerce").fillna(0)

    df["RB"] = df["Rake"] * df["% RB"]
    df["Total"] = df["Ganhos"] + df["RB"]

    return df

# =========================
# BOTÃO
# =========================

if st.button("🚀 Gerar Fechamento", key="gerar"):

    df_final = calcular(df_editado)

    st.subheader("📊 Resultado")

    # estilo
    def estilo(df):
        return df.style.format({
            "Ganhos": "R$ {:.2f}",
            "Rake": "R$ {:.2f}",
            "RB": "R$ {:.2f}",
            "Total": "R$ {:.2f}",
        })

    st.dataframe(estilo(df_final), use_container_width=True)

    total = df_final["Total"].sum()

    st.markdown("---")

    # =========================
    # 5%
    # =========================
    bonus = 0
    if aplicar_5:
        bonus = total * 0.05
        st.write(f"💰 5%: R$ {bonus:.2f}")

    total_final = total + bonus

    st.markdown("### 💵 Total Geral")
    st.success(f"R$ {total_final:.2f}")