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
import tempfile

st.set_page_config(layout="wide", page_title="Análisis SIMCE y PAES")

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

class PDFReporte(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Reporte Comparativo de Desempeño SIMCE/PAES", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

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
