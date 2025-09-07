import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO
from fpdf import FPDF
from PIL import Image
import unicodedata
import re

st.set_page_config(layout="wide", page_title="Análisis SIMCE y PAES")

# -------------------------------
# UTILS
# -------------------------------
def clasificar_puntaje(puntaje, tipo):
    if tipo == "SIMCE":
        if puntaje <= 250:
            return "Insuficiente"
        elif puntaje <= 279:
            return "Intermedio"
        else:
            return "Adecuado"
    elif tipo == "PAES":
        if puntaje <= 500:
            return "Insuficiente"
        elif puntaje <= 799:
            return "Intermedio"
        else:
            return "Adecuado"
    return "Desconocido"

def detectar_columna_nombres(df):
    for col in df.columns:
        if df[col].astype(str).str.contains(" ", regex=False).mean() > 0.8:
            return col
    return None

def detectar_columna_puntajes(df):
    for col in df.columns:
        try:
            nums = pd.to_numeric(df[col], errors='coerce')
            if nums.dropna().astype(int).gt(100).mean() > 0.8:
                return col
        except:
            continue
    return None

def normalizar_nombre(nombre):
    nombre = str(nombre).lower()
    nombre = unicodedata.normalize('NFKD', nombre).encode('ASCII', 'ignore').decode()
    nombre = re.sub(r'\s+', ' ', nombre)
    nombre = nombre.strip()
    partes = nombre.split()
    return ' '.join(partes[:2]) if len(partes) > 1 else nombre

def generar_consolidado_global(historico):
    consolidado = []
    for estudiante, registros in historico.items():
        for r in registros:
            consolidado.append({
                "Nombre": r["Nombre"],
                "Curso": r["Curso"],
                "Fecha": r["Fecha"],
                "Puntaje": r["Puntaje"],
                "Desempeño": r["Desempeño"],
                "Tipo": r["Prueba"]
            })
    return pd.DataFrame(consolidado)

# -------------------------------
# PDF UTILS
# -------------------------------
class PDFReporte(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Reporte Comparativo de Desempeño SIMCE/PAES", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

def generar_grafico_estudiante(nombre, fechas, puntajes):
    fig, ax = plt.subplots()
    ax.plot(fechas, puntajes, marker='o')
    ax.set_title(f"Evolución – {nombre}")
    ax.set_ylabel("Puntaje")
    ax.set_xlabel("Fecha")
    fig.tight_layout()
    img_bytes = BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    plt.close(fig)
    return img_bytes

import tempfile

def grafico_evolucion(df):
    fig, ax = plt.subplots()
    df.plot(ax=ax, marker='o')
    ax.set_title("Evolución de Puntajes por Curso")
    ax.set_ylabel("Puntaje Promedio")
    ax.set_xlabel("Fecha")
    fig.tight_layout()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        plt.savefig(tmpfile.name, format='png')
        plt.close(fig)
        return tmpfile.name


def grafico_distribucion(df):
    fig, ax = plt.subplots()
    df.plot(kind='bar', stacked=True, ax=ax)
    ax.set_title("Distribución de Niveles de Desempeño por Curso (%)")
    ax.set_ylabel("Porcentaje")
    fig.tight_layout()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        plt.savefig(tmpfile.name, format='png')
        plt.close(fig)
        return tmpfile.name


def exportar_dashboard_pdf(df_filtrado, df_evolucion, df_niveles, ranking_top, ranking_bottom, filtros):
    pdf = PDFReporte()
    pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Resumen del Dashboard", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 8, f"""
Filtros Aplicados:
- Cursos: {', '.join(filtros['cursos'])}
- Fechas: {', '.join(filtros['fechas'])}
- Tipos de Prueba: {', '.join(filtros['tipos'])}
""")

    total = len(df_filtrado)
    promedio = df_filtrado["Puntaje"].mean()
    try:
        nivel = df_filtrado["Desempeño"].value_counts(normalize=True).idxmax()
    except:
        nivel = "N/A"

    pdf.cell(0, 8, f"- Estudiantes Evaluados: {total}", ln=True)
    pdf.cell(0, 8, f"- Promedio General: {promedio:.2f}", ln=True)
    pdf.cell(0, 8, f"- Nivel más frecuente: {nivel}", ln=True)

    pdf.ln(5)
    img1 = grafico_evolucion(df_evolucion)
    pdf.image(img1, x=15, w=180)

    pdf.add_page()
    img2 = grafico_distribucion(df_niveles)
    pdf.image(img2, x=15, w=180)

    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Ranking de Estudiantes", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(90, 8, "🔝 Mejores Promedios", 1, 0, "C")
    pdf.cell(90, 8, "🔻 Peores Promedios", 1, 1, "C")

    for i in range(max(len(ranking_top), len(ranking_bottom))):
        left = f"{ranking_top.iloc[i]['Nombre']} ({ranking_top.iloc[i]['Promedio']:.2f})" if i < len(ranking_top) else ""
        right = f"{ranking_bottom.iloc[i]['Nombre']} ({ranking_bottom.iloc[i]['Promedio']:.2f})" if i < len(ranking_bottom) else ""
        pdf.cell(90, 8, left, 1)
        pdf.cell(90, 8, right, 1)
        pdf.ln(8)

    output = BytesIO()
    pdf.output(output)
    output.seek(0)
    return output

# -------------------------------
# INTERFAZ STREAMLIT
# -------------------------------
st.title("📊 Análisis de Puntajes SIMCE y PAES")
archivos = st.file_uploader("Sube uno o más archivos Excel generados por el sistema", type=["xlsx"], accept_multiple_files=True)

historico = {}

if archivos:
    for archivo in archivos:
        fecha_archivo = archivo.name.split("_")[-1].replace(".xlsx", "")
        xls = pd.ExcelFile(archivo)

        for hoja in xls.sheet_names:
            df = xls.parse(hoja)
            nombre_col = detectar_columna_nombres(df)
            puntaje_col = detectar_columna_puntajes(df)

            if not nombre_col or not puntaje_col:
                continue

            df_filtrado = df[[nombre_col, puntaje_col]].dropna()
            df_filtrado.columns = ["Nombre", "Puntaje"]

            tipo_prueba = "SIMCE" if df_filtrado["Puntaje"].max() < 600 else "PAES"
            df_filtrado["Desempeño"] = df_filtrado["Puntaje"].apply(lambda x: clasificar_puntaje(x, tipo_prueba))
            df_filtrado["Curso"] = hoja
            df_filtrado["Fecha"] = fecha_archivo
            df_filtrado["Nombre Normalizado"] = df_filtrado["Nombre"].apply(normalizar_nombre)

            for _, row in df_filtrado.iterrows():
                key = row["Nombre Normalizado"]
                if key not in historico:
                    historico[key] = []
                historico[key].append({
                    "Nombre": row["Nombre"],
                    "Curso": row["Curso"],
                    "Fecha": row["Fecha"],
                    "Puntaje": row["Puntaje"],
                    "Desempeño": row["Desempeño"],
                    "Prueba": tipo_prueba
                })

    df_dashboard = generar_consolidado_global(historico)
    st.header("📊 Dashboard General")
    cursos = df_dashboard["Curso"].unique()
    fechas = df_dashboard["Fecha"].unique()
    tipos = df_dashboard["Tipo"].unique()

    col1, col2, col3 = st.columns(3)
    curso_sel = col1.multiselect("Cursos", cursos, default=list(cursos))
    fecha_sel = col2.multiselect("Fechas", fechas, default=list(fechas))
    tipo_sel = col3.multiselect("Tipo de Prueba", tipos, default=list(tipos))

    df_filtrado = df_dashboard[
        df_dashboard["Curso"].isin(curso_sel) &
        df_dashboard["Fecha"].isin(fecha_sel) &
        df_dashboard["Tipo"].isin(tipo_sel)
    ]

    col1, col2, col3 = st.columns(3)
    col1.metric("Estudiantes Evaluados", len(df_filtrado))
    col2.metric("Promedio General", f"{df_filtrado['Puntaje'].mean():.2f}")
    try:
        nivel = df_filtrado["Desempeño"].value_counts(normalize=True).idxmax()
    except:
        nivel = "N/A"
    col3.metric("Nivel más frecuente", nivel)

    st.markdown("### Evolución de Puntajes por Curso")
    df_evol = df_filtrado.groupby(["Fecha", "Curso"])["Puntaje"].mean().unstack()
    st.line_chart(df_evol)

    st.markdown("### Distribución de Niveles de Desempeño")
    dist = df_filtrado.groupby(["Curso", "Desempeño"]).size().unstack(fill_value=0)
    niveles_pct = dist.div(dist.sum(axis=1), axis=0) * 100
    st.bar_chart(niveles_pct)

    st.markdown("### Ranking de Estudiantes")
    ranking = df_filtrado.groupby("Nombre")["Puntaje"].mean().reset_index().sort_values("Puntaje", ascending=False)
    top_n = 5
    col1, col2 = st.columns(2)
    col1.subheader("🔝 Mejores")
    col1.dataframe(ranking.head(top_n))
    col2.subheader("🔻 Peores")
    col2.dataframe(ranking.tail(top_n))

    st.markdown("### 📄 Descargar PDF del Dashboard")
    filtros_aplicados = {"cursos": curso_sel, "fechas": fecha_sel, "tipos": tipo_sel}
    pdf_dashboard = exportar_dashboard_pdf(df_filtrado, df_evol, niveles_pct, ranking.head(top_n), ranking.tail(top_n), filtros_aplicados)

    st.download_button(
        label="📥 Descargar PDF",
        data=pdf_dashboard,
        file_name=f"Dashboard_Liceo_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.pdf",
        mime="application/pdf"
    )

