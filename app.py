import re
import pandas as pd
import streamlit as st
import pdfplumber
import pytesseract
from PIL import Image

st.set_page_config(layout="wide")

st.title("📊 Relatório de Fechamento")

# =========================
# FUNÇÕES
# =========================
def limpar(txt):
    return re.sub(r"\s+", " ", str(txt)).strip()

def numero(v):
    if v is None:
        return 0
    v = str(v).replace("R$", "").replace(" ", "")
    v = v.replace(".", "").replace(",", ".")
    try:
        return float(re.sub(r"[^\d\.\-]", "", v))
    except:
        return 0

def extrair_pdf(file):
    texto = ""
    with pdfplumber.open(file) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                texto += t + "\n"
    return texto

def extrair_img(file):
    img = Image.open(file)
    try:
        return pytesseract.image_to_string(img, lang="por")
    except:
        return pytesseract.image_to_string(img)

def extrair_tabela(texto):
    dados = []
    for linha in texto.split("\n"):
        nums = re.findall(r"\d[\d\.,]*", linha)
        if nums:
            nome = limpar(re.sub(r"\d[\d\.,]*", "", linha))
            ganhos = numero(nums[0]) if len(nums) > 0 else 0
            rake = numero(nums[1]) if len(nums) > 1 else 0

            dados.append({
                "Nome": nome,
                "ID": "",
                "Ganhos": ganhos,
                "Rake": rake,
                "% RB": 0.30
            })
    return pd.DataFrame(dados)

def calcular(df):
    df = df.copy()

    df["Ganhos"] = pd.to_numeric(df["Ganhos"], errors="coerce").fillna(0)
    df["Rake"] = pd.to_numeric(df["Rake"], errors="coerce").fillna(0)
    df["% RB"] = pd.to_numeric(df["% RB"], errors="coerce").fillna(0)

    df["Rakeback"] = df["Rake"] * df["% RB"]
    df["Total"] = df["Ganhos"] + df["Rakeback"]

    return df

def formatar(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def tabela_html(df):
    html = """
    <style>
    .tbl {
        width:100%;
        border-collapse: collapse;
        border-radius:12px;
        overflow:hidden;
        font-size:14px;
    }
    .tbl th {
        background:#111827;
        color:white;
        padding:10px;
        text-align:left;
    }
    .tbl td {
        padding:10px;
        border-bottom:1px solid #2d3748;
    }
    .tbl tr:nth-child(even){
        background:rgba(255,255,255,0.03);
    }
    .pos {color:#22c55e;font-weight:600;}
    .neg {color:#ef4444;font-weight:600;}
    </style>
    """

    html += "<table class='tbl'><tr>"

    for col in df.columns:
        html += f"<th>{col}</th>"

    html += "</tr>"

    for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            val = row[col]

            if isinstance(val, float):
                classe = "pos" if val > 0 else "neg" if val < 0 else ""
                html += f"<td class='{classe}'>{formatar(val)}</td>"
            else:
                html += f"<td>{val}</td>"

        html += "</tr>"

    html += "</table>"

    return html

# =========================
# UPLOAD
# =========================
st.markdown("### 📂 Arquivos")

col1, col2 = st.columns(2)

with col1:
    pdf_file = st.file_uploader("PDF (Demetra)", type=["pdf"])

with col2:
    img_file = st.file_uploader("Imagem (Alex)", type=["png","jpg","jpeg"])

# =========================
# EXTRAÇÃO
# =========================
df_base = pd.DataFrame(columns=["Nome","ID","Ganhos","Rake","% RB"])

if pdf_file:
    df_base = extrair_tabela(extrair_pdf(pdf_file))

if img_file:
    df_img = extrair_tabela(extrair_img(img_file))
    df_base = pd.concat([df_base, df_img], ignore_index=True)

# =========================
# CONTROLE
# =========================
st.markdown("---")

tipo = st.selectbox("Tipo de fechamento", ["Alex","Demetra"])

# =========================
# TABELA EDITÁVEL
# =========================
st.subheader("✏️ Ajuste os dados")

df_edit = st.data_editor(
    df_base if not df_base.empty else pd.DataFrame({
        "Nome":[""],
        "ID":[""],
        "Ganhos":[0],
        "Rake":[0],
        "% RB":[0.30]
    }),
    num_rows="dynamic",
    use_container_width=True
)

# =========================
# RESULTADO
# =========================
if st.button("📊 Gerar Relatório"):

    df_final = calcular(df_edit)

    st.markdown("## 📄 Relatório Final")

    st.markdown(tabela_html(df_final), unsafe_allow_html=True)

    subtotal = df_final["Total"].sum()

    ajuste = 0

    if tipo == "Alex":
        ajuste = subtotal * -0.05

    elif tipo == "Demetra" and subtotal > 0:
        ajuste = subtotal * -0.05

    total_final = subtotal + ajuste

    # =========================
    # RESUMO ESTILO RELATÓRIO
    # =========================
    resumo = pd.DataFrame([
        {"Descrição":"Subtotal","Valor":subtotal},
        {"Descrição":"Ajuste (-5%)","Valor":ajuste},
        {"Descrição":"Total Final","Valor":total_final}
    ])

    st.markdown("### 💰 Resumo")

    st.markdown(tabela_html(resumo), unsafe_allow_html=True)