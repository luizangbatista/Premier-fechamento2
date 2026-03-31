import re
from io import BytesIO
from typing import List, Dict, Optional

import pandas as pd
import streamlit as st
import pdfplumber
from PIL import Image
import pytesseract


st.set_page_config(page_title="Fechamento Premier", layout="wide")

st.title("📊 Sistema de Fechamento")


# =========================
# UTILITÁRIOS
# =========================
def limpar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.replace("\xa0", " ")
    texto = re.sub(r"[ \t]+", " ", texto)
    return texto.strip()


def normalizar_numero(valor: str) -> Optional[float]:
    if valor is None:
        return None

    valor = str(valor).strip()
    valor = valor.replace("R$", "").replace("r$", "").strip()

    # Remove espaços
    valor = valor.replace(" ", "")

    # Caso formato brasileiro: 1.234,56
    if "," in valor and "." in valor:
        valor = valor.replace(".", "").replace(",", ".")
    # Caso formato 123,45
    elif "," in valor:
        valor = valor.replace(",", ".")

    # Remove caracteres que não sejam número, ponto ou sinal
    valor = re.sub(r"[^0-9\.\-]", "", valor)

    try:
        return float(valor)
    except ValueError:
        return None


def extrair_linhas_com_valores(texto: str, origem: str) -> pd.DataFrame:
    """
    Tenta encontrar linhas do tipo:
    NOME 123,45
    NOME -50,00
    NOME R$ 1.234,56
    """
    registros: List[Dict] = []

    linhas = texto.splitlines()
    padrao = re.compile(
        r"^\s*([A-Za-zÀ-ÿ0-9\.\-/&() ]+?)\s+(R?\$?\s*-?\d[\d\.\,]*)\s*$"
    )

    for linha in linhas:
        linha_limpa = limpar_texto(linha)
        if not linha_limpa:
            continue

        m = padrao.match(linha_limpa)
        if m:
            nome = limpar_texto(m.group(1))
            valor = normalizar_numero(m.group(2))

            if nome and valor is not None:
                registros.append(
                    {
                        "Nome": nome,
                        "Valor": valor,
                        "Origem": origem,
                        "Linha original": linha_limpa,
                    }
                )

    return pd.DataFrame(registros)


# =========================
# PDF
# =========================
def extrair_texto_pdf(arquivo_pdf) -> str:
    textos = []

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            txt = pagina.extract_text()
            if txt:
                textos.append(txt)

    return "\n".join(textos)


def extrair_dados_pdf(arquivo_pdf) -> tuple[pd.DataFrame, str]:
    texto_pdf = extrair_texto_pdf(arquivo_pdf)
    df_pdf = extrair_linhas_com_valores(texto_pdf, "PDF")
    return df_pdf, texto_pdf


# =========================
# IMAGEM
# =========================
def extrair_texto_imagem(arquivo_imagem) -> str:
    imagem = Image.open(arquivo_imagem)

    if imagem.mode != "RGB":
        imagem = imagem.convert("RGB")

    texto = pytesseract.image_to_string(imagem, lang="por")
    return texto


def extrair_dados_imagem(arquivo_imagem) -> tuple[pd.DataFrame, str]:
    texto_img = extrair_texto_imagem(arquivo_imagem)
    df_img = extrair_linhas_com_valores(texto_img, "Imagem")
    return df_img, texto_img


# =========================
# PROCESSAMENTO
# =========================
def combinar_dados(df_pdf: pd.DataFrame, df_img: pd.DataFrame) -> pd.DataFrame:
    """
    Junta por Nome.
    PDF -> coluna Valor
    Imagem -> coluna Ajuste
    """
    if df_pdf.empty and df_img.empty:
        return pd.DataFrame()

    base_pdf = df_pdf.copy()
    base_img = df_img.copy()

    if not base_pdf.empty:
        base_pdf = (
            base_pdf.groupby("Nome", as_index=False)["Valor"]
            .sum()
        )
    else:
        base_pdf = pd.DataFrame(columns=["Nome", "Valor"])

    if not base_img.empty:
        base_img = (
            base_img.groupby("Nome", as_index=False)["Valor"]
            .sum()
            .rename(columns={"Valor": "Ajuste"})
        )
    else:
        base_img = pd.DataFrame(columns=["Nome", "Ajuste"])

    df = pd.merge(base_pdf, base_img, on="Nome", how="outer")

    df["Valor"] = df["Valor"].fillna(0.0)
    df["Ajuste"] = df["Ajuste"].fillna(0.0)

    df["Total"] = df["Valor"] + df["Ajuste"]
    df["Bonus 5%"] = df["Total"].apply(lambda x: x * 0.05 if x > 0 else 0.0)
    df["Final"] = df["Total"] + df["Bonus 5%"]

    return df.sort_values("Nome").reset_index(drop=True)


def formatar_moeda(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tabela_html(df: pd.DataFrame, colunas_monetarias: Optional[List[str]] = None) -> str:
    colunas_monetarias = colunas_monetarias or []

    html = """
    <style>
    .tabela-bonita {
        width: 100%;
        border-collapse: collapse;
        overflow: hidden;
        border-radius: 14px;
        font-size: 15px;
    }
    .tabela-bonita th {
        background: #1f2937;
        color: white;
        padding: 12px;
        text-align: left;
    }
    .tabela-bonita td {
        padding: 12px;
        border-bottom: 1px solid #2d3748;
    }
    .tabela-bonita tr:nth-child(even) {
        background: rgba(255,255,255,0.03);
    }
    .pos {
        color: #22c55e;
        font-weight: 600;
    }
    .neg {
        color: #ef4444;
        font-weight: 600;
    }
    </style>
    """

    html += '<table class="tabela-bonita">'
    html += "<thead><tr>"
    for col in df.columns:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"

    for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            valor = row[col]

            if col in colunas_monetarias and pd.notna(valor):
                classe = "pos" if float(valor) > 0 else "neg" if float(valor) < 0 else ""
                html += f'<td class="{classe}">{formatar_moeda(float(valor))}</td>'
            else:
                if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                    classe = "pos" if valor > 0 else "neg" if valor < 0 else ""
                    html += f'<td class="{classe}">{valor}</td>'
                else:
                    html += f"<td>{valor}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("📂 Upload")
    pdf_file = st.file_uploader("Enviar PDF", type=["pdf"])
    img_file = st.file_uploader("Enviar imagem", type=["png", "jpg", "jpeg"])

    st.caption("O sistema tenta extrair linhas com nome + valor.")


# =========================
# LEITURA
# =========================
df_pdf = pd.DataFrame()
df_img = pd.DataFrame()
texto_pdf = ""
texto_img = ""

if pdf_file is not None:
    try:
        df_pdf, texto_pdf = extrair_dados_pdf(pdf_file)
        st.success("PDF lido.")
    except Exception as e:
        st.error(f"Erro ao ler PDF: {e}")

if img_file is not None:
    try:
        df_img, texto_img = extrair_dados_imagem(img_file)
        st.success("Imagem lida.")
    except Exception as e:
        st.error(f"Erro ao ler imagem: {e}")


# =========================
# EXIBIÇÃO DA EXTRAÇÃO
# =========================
aba1, aba2, aba3 = st.tabs(["Dados extraídos", "Texto bruto", "Resultado"])

with aba1:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Extração do PDF")
        if df_pdf.empty:
            st.warning("Nenhuma linha identificada no PDF.")
        else:
            st.dataframe(df_pdf, use_container_width=True)

    with col2:
        st.subheader("🖼️ Extração da imagem")
        if df_img.empty:
            st.warning("Nenhuma linha identificada na imagem.")
        else:
            st.dataframe(df_img, use_container_width=True)

with aba2:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Texto bruto do PDF")
        st.text_area("PDF", texto_pdf, height=300)

    with c2:
        st.subheader("Texto bruto da imagem")
        st.text_area("Imagem", texto_img, height=300)

with aba3:
    st.subheader("✏️ Ajustes manuais")

    st.markdown("### PDF editável")
    df_pdf_editado = st.data_editor(
        df_pdf if not df_pdf.empty else pd.DataFrame(columns=["Nome", "Valor", "Origem", "Linha original"]),
        use_container_width=True,
        num_rows="dynamic",
    )

    st.markdown("### Imagem editável")
    df_img_editado = st.data_editor(
        df_img if not df_img.empty else pd.DataFrame(columns=["Nome", "Valor", "Origem", "Linha original"]),
        use_container_width=True,
        num_rows="dynamic",
    )

    if st.button("🚀 Gerar Relatórios", use_container_width=False):
        try:
            df_pdf_proc = df_pdf_editado.copy()
            df_img_proc = df_img_editado.copy()

            if "Valor" in df_pdf_proc.columns:
                df_pdf_proc["Valor"] = df_pdf_proc["Valor"].apply(normalizar_numero)

            if "Valor" in df_img_proc.columns:
                df_img_proc["Valor"] = df_img_proc["Valor"].apply(normalizar_numero)

            df_pdf_proc = df_pdf_proc.dropna(subset=["Nome", "Valor"]) if not df_pdf_proc.empty else df_pdf_proc
            df_img_proc = df_img_proc.dropna(subset=["Nome", "Valor"]) if not df_img_proc.empty else df_img_proc

            df_final = combinar_dados(df_pdf_proc, df_img_proc)

            if df_final.empty:
                st.warning("Nenhum dado suficiente para gerar relatório.")
            else:
                st.markdown("## 📊 Resultado Final")
                st.markdown(
                    tabela_html(
                        df_final,
                        colunas_monetarias=["Valor", "Ajuste", "Total", "Bonus 5%", "Final"],
                    ),
                    unsafe_allow_html=True,
                )

                resumo = pd.DataFrame(
                    {
                        "Métrica": ["Total Geral", "Total Positivos", "Total Negativos"],
                        "Valor": [
                            df_final["Final"].sum(),
                            df_final.loc[df_final["Final"] > 0, "Final"].sum(),
                            df_final.loc[df_final["Final"] < 0, "Final"].sum(),
                        ],
                    }
                )

                st.markdown("## 📈 Resumo")
                st.markdown(
                    tabela_html(resumo, colunas_monetarias=["Valor"]),
                    unsafe_allow_html=True,
                )

        except Exception as e:
            st.error(f"Erro ao gerar relatório: {e}")