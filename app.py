
import re import math from io import BytesIO from typing import Dict, List, Optional, Tuple

import pandas as pd import pdfplumber import streamlit as st

=========================

CONFIGURAÇÃO DO APP

=========================

st.set_page_config(page_title="Fechamento Alex e Demetra", layout="wide")

=========================

REGRAS FIXAS

=========================

ID_MAP_DEFAULT = { "12970177": {"cliente": "Alex", "percentual": 70.0}, "12968708": {"cliente": "Demetra", "percentual": 70.0}, "13019559": {"cliente": "Alex", "percentual": 50.0}, "1607968": {"cliente": "Demetra", "percentual": 65.0}, "1527106": {"cliente": "Demetra", "percentual": 65.0}, "13018880": {"cliente": "Alex", "percentual": 45.0}, "13213751": {"cliente": "Alex", "percentual": 70.0}, "13265647": {"cliente": "Alex", "percentual": 50.0}, "13319248": {"cliente": "Alex", "percentual": 70.0}, "13357678": {"cliente": "Demetra", "percentual": 65.0}, "13379845": {"cliente": "Alex", "percentual": 60.0}, "13104440": {"cliente": "Alex", "percentual": 50.0}, }

=========================

CSS

=========================

CUSTOM_CSS = """

<style>
.block-title {
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: 0.2rem;
    color: #0f172a;
}
.helper {
    color: #475569;
    margin-bottom: 1rem;
}
.report-card {
    background: linear-gradient(180deg, #f8fbff 0%, #eef5ff 100%);
    border: 1px solid #dbe7ff;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 22px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}
.report-heading {
    background: #0f172a;
    color: white;
    font-weight: 800;
    border-radius: 12px 12px 0 0;
    padding: 14px 16px;
    font-size: 1.25rem;
    letter-spacing: 0.4px;
}
.total-box {
    background: #fff8c5;
    border: 1px solid #f6e05e;
    border-radius: 12px;
    padding: 16px;
    font-size: 1.2rem;
    font-weight: 800;
    color: #111827;
}
.status-pay {
    margin-top: 12px;
    font-size: 1.7rem;
    font-weight: 900;
    color: #111827;
}
.status-receive {
    margin-top: 12px;
    font-size: 1.7rem;
    font-weight: 900;
    color: #111827;
}
.small-note {
    color: #64748b;
    font-size: 0.92rem;
}
</style>""" st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

=========================

FUNÇÕES UTILITÁRIAS

=========================

def br_str_to_float(value: Optional[str]) -> float: if value is None: return 0.0 s = str(value).strip() if not s: return 0.0 s = s.replace("R$", "").replace(" ", "").replace(")", "") s = s.replace(".", "").replace(",", ".") s = s.replace("−", "-") try: return float(s) except ValueError: return 0.0

def float_to_br(value: float) -> str: neg = value < 0 value = abs(value) s = f"{value:,.2f}" s = s.replace(",", "X").replace(".", ",").replace("X", ".") return f"-{s}" if neg else s

def safe_percent_to_float(value) -> float: if value is None or (isinstance(value, float) and math.isnan(value)): return 0.0 s = str(value).replace("%", "").replace(",", ".").strip() try: return float(s) except ValueError: return 0.0

def calcular_rb(rake: float, percentual: float) -> float: return round(rake * (percentual / 100.0), 2)

def calcular_total_linha(ganhos: float, rb: float) -> float: return round(ganhos + rb, 2)

def normalizar_nome_agente(nome: str) -> str: return re.sub(r"\s+", " ", (nome or "").strip())

=========================

LEITURA DA IMAGEM

=========================

def extrair_texto_imagem_com_ocr(uploaded_file) -> str: """ Usa EasyOCR se estiver instalado. Se não estiver, mostra orientação para instalar. """ try: import easyocr from PIL import Image except ImportError: raise RuntimeError( "Para ler a imagem, instale as dependências: pip install easyocr pillow" )

image = Image.open(uploaded_file)
reader = easyocr.Reader(["pt", "en"], gpu=False)
result = reader.readtext(image)
linhas = [item[1] for item in result]
return "\n".join(linhas)

def extrair_dados_imagem(texto_ocr: str) -> Dict[str, float]: """ Espera algo como: Killuminatti 2689,40 -672,35 -3710,30 -1693,25

O que será usado:
- agente = primeiro texto relevante
- rake = primeiro número monetário da linha principal
- ganhos = terceiro número monetário da linha principal
- cliente fixo = Demetra
- percentual fixo = 70
"""
linhas = [l.strip() for l in texto_ocr.splitlines() if l.strip()]

money_pattern = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2}")

linha_principal = None
for linha in linhas:
    nums = money_pattern.findall(linha)
    if len(nums) >= 3 and not any(x in linha.upper() for x in ["TOTAL", "ADIANTAMENTO", "RAKEBACK"]):
        linha_principal = linha
        break

if not linha_principal:
    raise ValueError("Não consegui identificar a linha principal da imagem.")

nums = money_pattern.findall(linha_principal)
rake = br_str_to_float(nums[0])
ganhos = br_str_to_float(nums[2])

nome = linha_principal
for n in nums:
    nome = nome.replace(n, "")
nome = normalizar_nome_agente(nome)

if not nome:
    nome = "Killuminatti"

percentual = 70.0
rb = calcular_rb(rake, percentual)
total = calcular_total_linha(ganhos, rb)

return {
    "origem": "Imagem",
    "agente": nome,
    "clube": "",
    "id": "",
    "cliente": "Demetra",
    "ganhos": ganhos,
    "rake": rake,
    "percentual": percentual,
    "rb": rb,
    "total": total,
}

=========================

LEITURA DO PDF

=========================

def extrair_texto_pdf(uploaded_pdf) -> str: all_text = [] with pdfplumber.open(uploaded_pdf) as pdf: for page in pdf.pages: txt = page.extract_text() or "" all_text.append(txt) return "\n".join(all_text)

def parse_linha_pdf(line: str) -> Optional[Dict]: """ Tenta parsear linhas do tipo: AG Kiritoro diamond VENEZA l 2 12968708 R$188,80) R$1.882,45) R$0,00) 75% R$1.600,64)

Captura:
- nome agente
- id
- ganhos
- rake
Ignora rebate/rakeback do PDF para cálculo final.
"""
if "R$" not in line:
    return None
if any(chave in line.upper() for chave in ["ACERTO SEMANAL", "ACERTO FINAL", "AGENTES CLUBE ID GANHOS", "RESULTADO POR AG"]):
    return None

id_match = re.search(r"\b(\d{7,8})\b", line)
if not id_match:
    return None

agent_id = id_match.group(1)
before_id = line[: id_match.start()].strip()
after_id = line[id_match.end() :].strip()

valores = re.findall(r"R\$\s*-?[\d\.]+,\d+\)?", after_id)
percent_match = re.search(r"(\d{1,3})%", after_id)

if len(valores) < 2:
    return None

ganhos = br_str_to_float(valores[0])
rake = br_str_to_float(valores[1])
percentual_pdf = float(percent_match.group(1)) if percent_match else 0.0

nome_agente = normalizar_nome_agente(before_id)
if not nome_agente:
    return None

return {
    "origem": "PDF",
    "agente": nome_agente,
    "clube": "",
    "id": agent_id,
    "cliente": "",
    "ganhos": ganhos,
    "rake": rake,
    "percentual": percentual_pdf,
    "rb": 0.0,
    "total": 0.0,
}

def extrair_linhas_pdf(texto_pdf: str, id_map: Dict[str, Dict]) -> pd.DataFrame: registros = [] for line in texto_pdf.splitlines(): parsed = parse_linha_pdf(line.strip()) if not parsed: continue

agent_id = parsed["id"]
    if agent_id in id_map:
        parsed["cliente"] = id_map[agent_id]["cliente"]
        parsed["percentual"] = id_map[agent_id]["percentual"]

    parsed["rb"] = calcular_rb(parsed["rake"], parsed["percentual"])
    parsed["total"] = calcular_total_linha(parsed["ganhos"], parsed["rb"])
    registros.append(parsed)

if not registros:
    return pd.DataFrame(columns=["origem", "agente", "clube", "id", "cliente", "ganhos", "rake", "percentual", "rb", "total"])

return pd.DataFrame(registros)

=========================

CÁLCULOS FINAIS

=========================

def recalcular_dataframe(df: pd.DataFrame) -> pd.DataFrame: df = df.copy() df["ganhos"] = pd.to_numeric(df["ganhos"], errors="coerce").fillna(0.0) df["rake"] = pd.to_numeric(df["rake"], errors="coerce").fillna(0.0) df["percentual"] = pd.to_numeric(df["percentual"], errors="coerce").fillna(0.0) df["rb"] = (df["rake"] * (df["percentual"] / 100.0)).round(2) df["total"] = (df["ganhos"] + df["rb"]).round(2) return df

def fechamento_demetra(df_revisao: pd.DataFrame) -> Tuple[pd.DataFrame, float, float, float]: df_dem = df_revisao[df_revisao["cliente"] == "Demetra"].copy() df_dem = recalcular_dataframe(df_dem) base = round(df_dem["total"].sum(), 2) desconto = round(base * 0.05, 2) if base > 0 else 0.0 final = round(base - desconto, 2) return df_dem, base, desconto, final

def fechamento_alex(df_revisao: pd.DataFrame) -> Tuple[pd.DataFrame, float, float, float]: df_alex = df_revisao[df_revisao["cliente"] == "Alex"].copy() df_alex = recalcular_dataframe(df_alex) base = round(df_alex["total"].sum(), 2) desconto = round(base * 0.05, 2) final = round(base - desconto, 2) return df_alex, base, desconto, final

=========================

FORMATAÇÃO PARA EXIBIÇÃO

=========================

def preparar_tabela_final(df: pd.DataFrame) -> pd.DataFrame: exibir = df[["agente", "ganhos", "rake", "percentual", "rb", "total"]].copy() exibir.columns = ["Agente", "Ganhos", "Rake", "%", "RB", "Resultado"] exibir["Ganhos"] = exibir["Ganhos"].apply(float_to_br) exibir["Rake"] = exibir["Rake"].apply(float_to_br) exibir["%"] = exibir["%"].apply(lambda x: f"{safe_percent_to_float(x):.0f}%") exibir["RB"] = exibir["RB"].apply(float_to_br) exibir["Resultado"] = exibir["Resultado"].apply(float_to_br) return exibir

def style_table(df: pd.DataFrame): return ( df.style.hide(axis="index") .set_table_styles( [ {"selector": "thead th", "props": [("background-color", "#0f172a"), ("color", "white"), ("font-weight", "800"), ("text-align", "center")]}, {"selector": "tbody td", "props": [("padding", "10px"), ("border", "1px solid #dbe4f0")]}, {"selector": "table", "props": [("border-collapse", "collapse"), ("width", "100%")]}, ] ) .set_properties(subset=["Agente"], **{"text-align": "left", "font-weight": "700"}) .set_properties(subset=["Ganhos", "Rake", "%", "RB", "Resultado"], **{"text-align": "right"}) )

=========================

INTERFACE

=========================

st.markdown('<div class="block-title">Fechamento Alex e Demetra</div>', unsafe_allow_html=True) st.markdown( '<div class="helper">Envie uma imagem e um PDF, revise os dados editáveis e clique em <b>Gerar relatórios</b>.</div>', unsafe_allow_html=True, )

col1, col2 = st.columns(2) with col1: imagem_file = st.file_uploader("Imagem do fechamento", type=["png", "jpg", "jpeg", "webp"]) with col2: pdf_file = st.file_uploader("PDF semanal", type=["pdf"])

if "df_revisao" not in st.session_state: st.session_state.df_revisao = None

if st.button("Ler arquivos", type="primary"): if not imagem_file or not pdf_file: st.error("Selecione a imagem e o PDF antes de continuar.") else: try: texto_imagem = extrair_texto_imagem_com_ocr(imagem_file) dados_imagem = extrair_dados_imagem(texto_imagem)

pdf_file.seek(0)
        texto_pdf = extrair_texto_pdf(pdf_file)
        df_pdf = extrair_linhas_pdf(texto_pdf, ID_MAP_DEFAULT)

        df_img = pd.DataFrame([dados_imagem])
        df_revisao = pd.concat([df_img, df_pdf], ignore_index=True)
        df_revisao = recalcular_dataframe(df_revisao)
        st.session_state.df_revisao = df_revisao
        st.success("Arquivos lidos com sucesso. Revise os dados abaixo.")
    except Exception as e:
        st.error(f"Erro ao ler arquivos: {e}")

if st.session_state.df_revisao is not None: st.subheader("Revisão antes do fechamento") st.caption("Cliente e % são editáveis. RB e Total recalculam automaticamente.")

df_edit = st.session_state.df_revisao.copy()

df_edit["cliente"] = df_edit["cliente"].replace("", None)

edited = st.data_editor(
    df_edit,
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "origem": st.column_config.TextColumn("Origem", disabled=True),
        "agente": st.column_config.TextColumn("Agente", disabled=True),
        "clube": st.column_config.TextColumn("Clube", disabled=True),
        "id": st.column_config.TextColumn("ID", disabled=True),
        "cliente": st.column_config.SelectboxColumn("Cliente", options=["Alex", "Demetra"], required=False),
        "ganhos": st.column_config.NumberColumn("Ganhos", format="%.2f", disabled=True),
        "rake": st.column_config.NumberColumn("Rake", format="%.2f", disabled=True),
        "percentual": st.column_config.NumberColumn("%", format="%.2f"),
        "rb": st.column_config.NumberColumn("RB", format="%.2f", disabled=True),
        "total": st.column_config.NumberColumn("Total", format="%.2f", disabled=True),
    },
)

edited = recalcular_dataframe(edited)
st.session_state.df_revisao = edited

faltando = edited[(edited["origem"] == "PDF") & ((edited["cliente"].isna()) | (edited["cliente"] == "") | (edited["percentual"] <= 0))]
if not faltando.empty:
    st.warning("Existem linhas do PDF sem Cliente definido ou sem % válido. Complete antes de gerar os relatórios.")

if st.button("Gerar relatórios"):
    faltando = edited[(edited["origem"] == "PDF") & ((edited["cliente"].isna()) | (edited["cliente"] == "") | (edited["percentual"] <= 0))]
    if not faltando.empty:
        st.error("Preencha Cliente e % de todas as linhas do PDF antes de gerar os relatórios.")
    else:
        df_dem, base_dem, desconto_dem, final_dem = fechamento_demetra(edited)
        df_alex, base_alex, desconto_alex, final_alex = fechamento_alex(edited)

        st.divider()
        st.subheader("Relatórios finais")

        # DEMETRA
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.markdown('<div class="report-heading">DEMETRA</div>', unsafe_allow_html=True)
        tabela_dem = preparar_tabela_final(df_dem)
        st.dataframe(style_table(tabela_dem), use_container_width=True)
        st.markdown(
            f'''
            <div class="total-box">
                Total base: {float_to_br(base_dem)}<br>
                -5%: {float_to_br(desconto_dem)}<br>
                Total final: {float_to_br(final_dem)}
            </div>
            ''',
            unsafe_allow_html=True,
        )
        status_dem = "PREMIER TEM A PAGAR" if final_dem > 0 else "PREMIER TEM A RECEBER"
        cls_dem = "status-pay" if final_dem > 0 else "status-receive"
        st.markdown(f'<div class="{cls_dem}">{status_dem}<br>{float_to_br(abs(final_dem))}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ALEX
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.markdown('<div class="report-heading">ALEX</div>', unsafe_allow_html=True)
        tabela_alex = preparar_tabela_final(df_alex)
        st.dataframe(style_table(tabela_alex), use_container_width=True)
        st.markdown(
            f'''
            <div class="total-box">
                Total base: {float_to_br(base_alex)}<br>
                -5%: {float_to_br(desconto_alex)}<br>
                Total final: {float_to_br(final_alex)}
            </div>
            ''',
            unsafe_allow_html=True,
        )
        status_alex = "PREMIER TEM A PAGAR" if final_alex > 0 else "PREMIER TEM A RECEBER"
        cls_alex = "status-pay" if final_alex > 0 else "status-receive"
        st.markdown(f'<div class="{cls_alex}">{status_alex}<br>{float_to_br(abs(final_alex))}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="small-note">Os relatórios ficam na própria tela, prontos para print.</div>', unsafe_allow_html=True)
