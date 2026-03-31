import re
from typing import List, Dict, Optional, Tuple

import pandas as pd
import streamlit as st
import pdfplumber
from PIL import Image
import pytesseract


# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Sistema de Fechamento", layout="wide")

st.title("📊 Sistema de Fechamento")


# =========================
# UTILITÁRIOS
# =========================
def limpar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = str(texto).replace("\xa0", " ")
    texto = re.sub(r"[ \t]+", " ", texto)
    return texto.strip()


def normalizar_numero(valor) -> Optional[float]:
    if valor is None:
        return None

    valor = str(valor).strip()
    if not valor:
        return None

    valor = valor.replace("R$", "").replace("r$", "").strip()
    valor = valor.replace(" ", "")

    if "," in valor and "." in valor:
        valor = valor.replace(".", "").replace(",", ".")
    elif "," in valor:
        valor = valor.replace(",", ".")

    valor = re.sub(r"[^0-9\.\-]", "", valor)

    if valor in {"", "-", ".", "-."}:
        return None

    try:
        return float(valor)
    except ValueError:
        return None


def formatar_moeda(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# =========================
# EXTRAÇÃO
# =========================
def extrair_texto_pdf(arquivo_pdf) -> str:
    textos = []

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            txt = pagina.extract_text()
            if txt:
                textos.append(txt)

    return "\n".join(textos)


def extrair_texto_imagem(arquivo_imagem) -> str:
    imagem = Image.open(arquivo_imagem)

    if imagem.mode != "RGB":
        imagem = imagem.convert("RGB")

    try:
        texto = pytesseract.image_to_string(imagem, lang="por")
    except Exception:
        texto = pytesseract.image_to_string(imagem)

    return texto


def extrair_linhas_com_valores(texto: str, origem: str) -> pd.DataFrame:
    registros: List[Dict] = []

    linhas = texto.splitlines()

    for linha in linhas:
        linha = limpar_texto(linha)
        if not linha:
            continue

        # pega todos os possíveis números da linha
        numeros = re.findall(r"-?\d[\d\.,]*", linha)

        if not numeros:
            continue

        valor = normalizar_numero(numeros[-1])

        # remove o último número da linha para tentar obter o nome
        nome = re.sub(r"-?\d[\d\.,]*\s*$", "", linha).strip(" -|:;")

        if not nome:
            nome = re.sub(r"-?\d[\d\.,]*", "", linha).strip(" -|:;")

        if nome and valor is not None:
            registros.append(
                {
                    "Nome": nome,
                    "Valor": valor,
                    "Origem": origem,
                    "Linha original": linha,
                }
            )

    if registros:
        return pd.DataFrame(registros)

    return pd.DataFrame(columns=["Nome", "Valor", "Origem", "Linha original"])


def extrair_dados_pdf(arquivo_pdf) -> Tuple[pd.DataFrame, str]:
    texto_pdf = extrair_texto_pdf(arquivo_pdf)
    df_pdf = extrair_linhas_com_valores(texto_pdf, "PDF")
    return df_pdf, texto_pdf


def extrair_dados_imagem(arquivo_imagem) -> Tuple[pd.DataFrame, str]:
    texto_img = extrair_texto_imagem(arquivo_imagem)
    df_img = extrair_linhas_com_valores(texto_img, "Imagem")
    return df_img, texto_img


# =========================
# PROCESSAMENTO
# =========================
def preparar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()

    if "Nome" in df.columns:
        df["Nome"] = df["Nome"].astype(str).apply(limpar_texto)

    if "Valor" in df.columns:
        df["Valor"] = df["Valor"].apply(normalizar_numero)

    df = df.dropna(subset=["Nome", "Valor"])
    df = df[df["Nome"] != ""]

    return df


def combinar_dados(df_pdf: pd.DataFrame, df_img: pd.DataFrame) -> pd.DataFrame:
    if df_pdf.empty and df_img.empty:
        return pd.DataFrame(columns=["Nome", "Valor", "Ajuste", "Total", "Bonus 5%", "Final"])

    if not df_pdf.empty:
        base_pdf = df_pdf.groupby("Nome", as_index=False)["Valor"].sum()
    else:
        base_pdf = pd.DataFrame(columns=["Nome", "Valor"])

    if not df_img.empty:
        base_img = (
            df_img.groupby("Nome", as_index=False)["Valor"]
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


# =========================
# HTML DAS TABELAS
# =========================
def tabela_html(df: pd.DataFrame, colunas_monetarias: Optional[List[str]] = None) -> str:
    colunas_monetarias = colunas_monetarias or []

    html = """
    <style>
    .tabela-bonita {
        width: 100%;
        border-collapse: collapse;
        border-radius: 14px;
        overflow: hidden;
        font-size: 15px;
        margin-bottom: 18px;
    }
    .tabela-bonita th {
        background: #1f2937;
        color: white;
        padding: 12px;
        text-align: left;
        border: 1px solid #374151;
    }
    .tabela-bonita td {
        padding: 12px;
        border: 1px solid #374151;
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
                classe = ""
                if float(valor) > 0:
                    classe = "pos"
                elif float(valor) < 0:
                    classe = "neg"

                html += f'<td class="{classe}">{formatar_moeda(float(valor))}</td>'
            else:
                if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                    classe = ""
                    if valor > 0:
                        classe = "pos"
                    elif valor < 0:
                        classe = "neg"
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
    st.header("📂 Upload dos arquivos")

    pdf_file = st.file_uploader(
        "Enviar PDF",
        type=["pdf"],
        key="pdf_upload",
    )

    img_file = st.file_uploader(
        "Enviar imagem",
        type=["png", "jpg", "jpeg"],
        key="img_upload",
    )

    st.caption("Envie 1 PDF e 1 imagem para leitura.")


# =========================
# LEITURA DOS ARQUIVOS
# =========================
df_pdf = pd.DataFrame(columns=["Nome", "Valor", "Origem", "Linha original"])
df_img = pd.DataFrame(columns=["Nome", "Valor", "Origem", "Linha original"])
texto_pdf = ""
texto_img = ""

if pdf_file is not None:
    try:
        df_pdf, texto_pdf = extrair_dados_pdf(pdf_file)
        st.success("PDF processado.")
    except Exception as e:
        st.error(f"Erro ao ler PDF: {e}")

if img_file is not None:
    try:
        df_img, texto_img = extrair_dados_imagem(img_file)
        st.success("Imagem processada.")
    except Exception as e:
        st.error(f"Erro ao ler imagem: {e}")


# =========================
# TABS
# =========================
aba1, aba2, aba3 = st.tabs(["Dados extraídos", "Texto bruto", "Resultado"])

with aba1:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Extração do PDF")
        if df_pdf.empty:
            st.warning("Nenhuma linha identificada no PDF.")
        else:
            st.dataframe(df_pdf, use_container_width=True, key="df_pdf_extraido")

    with col2:
        st.subheader("🖼️ Extração da imagem")
        if df_img.empty:
            st.warning("Nenhuma linha identificada na imagem.")
        else:
            st.dataframe(df_img, use_container_width=True, key="df_img_extraido")

with aba2:
    col_texto_1, col_texto_2 = st.columns(2)

    with col_texto_1:
        st.subheader("Texto bruto do PDF")
        st.text_area(
            "Conteúdo do PDF",
            value=texto_pdf,
            height=320,
            key="texto_bruto_pdf",
        )

    with col_texto_2:
        st.subheader("Texto bruto da imagem")
        st.text_area(
            "Conteúdo da imagem",
            value=texto_img,
            height=320,
            key="texto_bruto_img",
        )

with aba3:
    st.subheader("✏️ Ajustes manuais")

    st.markdown("### PDF editável")
    df_pdf_editado = st.data_editor(
        df_pdf,
        use_container_width=True,
        num_rows="dynamic",
        key="editor_pdf",
    )

    st.markdown("### Imagem editável")
    df_img_editado = st.data_editor(
        df_img,
        use_container_width=True,
        num_rows="dynamic",
        key="editor_img",
    )

    gerar = st.button(
        "🚀 Gerar Relatórios",
        key="btn_gerar_relatorios",
    )

    if gerar:
        try:
            df_pdf_proc = preparar_dataframe(df_pdf_editado)
            df_img_proc = preparar_dataframe(df_img_editado)

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