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
import os
import pickle
import zipfile

st.set_page_config(layout="wide", page_title="Análisis SIMCE y PAES")

HISTORICO_PATH = "historico.pkl"

# ------------------ Funciones auxiliares ------------------

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

def detectar_columna_curso(df):
    posibles = [col for col in df.columns if "curso" in col.lower()]
    return posibles[0] if posibles else None

def detectar_columna_anio(df):
    posibles = [col for col in df.columns if "año" in col.lower() or "anio" in col.lower()]
    return posibles[0] if posibles else None

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
                "Tipo": r["Prueba"],
                "Año": r.get("Año", "")
            })
    return pd.DataFrame(consolidado)

def guardar_historico_en_archivo(historico):
    with open(HISTORICO_PATH, "wb") as f:
        pickle.dump(historico, f)

def cargar_historico_desde_archivo():
    if os.path.exists(HISTORICO_PATH):
        with open(HISTORICO_PATH, "rb") as f:
            return pickle.load(f)
    return {}

class PDFReporte(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Reporte Comparativo de Desempeño SIMCE/PAES", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

def generar_grafico_barras(df_curso, curso, tipo_prueba):
    fig, ax = plt.subplots(figsize=(10, 4))
    df_ordenado = df_curso.sort_values("Puntaje", ascending=False)
    ax.bar(df_ordenado["Nombre"], df_ordenado["Puntaje"])
    ax.set_title(f"Puntajes - {curso} ({tipo_prueba})")
    ax.set_xlabel("Estudiantes")
    ax.set_ylabel("Puntaje")
    ax.set_xticklabels(df_ordenado["Nombre"], rotation=45, ha='right')
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='PNG', dpi=150)
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

def generar_pdf_curso(df_curso, curso, tipo_prueba):
    pdf = PDFReporte()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Curso: {curso} - Prueba: {tipo_prueba}", ln=True)
    pdf.ln(5)
    promedio = round(df_curso["Puntaje"].mean(), 2)
    distribucion = df_curso["Desempeño"].value_counts().to_dict()
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 10, f"Promedio del curso: {promedio}", ln=True)
    pdf.cell(0, 10, "Distribución por niveles:", ln=True)
    for nivel in ["Insuficiente", "Intermedio", "Adecuado"]:
        cantidad = distribucion.get(nivel, 0)
        pdf.cell(0, 10, f" - {nivel}: {cantidad}", ln=True)
    pdf.ln(5)
    grafico = generar_grafico_barras(df_curso, curso, tipo_prueba)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        tmpfile.write(grafico.read())
        tmpfile.flush()
        pdf.image(tmpfile.name, x=10, y=None, w=190)
    pdf.ln(10)
    pdf.set_font("Arial", "", 10)
    for index, row in df_curso.iterrows():
        linea = f"{row['Nombre']} - Puntaje: {row['Puntaje']} - Desempeño: {row['Desempeño']}"
        pdf.cell(0, 10, linea, ln=True)
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

def generar_pdf_estudiante(registros):
    if not registros:
        return None
    estudiante = registros[0]["Nombre"]
    pdf = PDFReporte()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Reporte Individual - {estudiante}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "", 11)
    for r in registros:
        linea = f"Fecha: {r['Fecha']} | Prueba: {r['Prueba']} | Puntaje: {r['Puntaje']} | Desempeño: {r['Desempeño']}"
        pdf.cell(0, 10, linea, ln=True)
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

def generar_zip_reportes_por_curso(df_consolidado, tipo_prueba):
    cursos = df_consolidado["Curso"].dropna().unique()
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for curso in cursos:
            df_curso = df_consolidado[
                (df_consolidado["Curso"] == curso) &
                (df_consolidado["Tipo"] == tipo_prueba)
            ]
            if not df_curso.empty:
                pdf_buffer = generar_pdf_curso(df_curso, curso, tipo_prueba)
                filename = f"Reporte_{curso}_{tipo_prueba}.pdf"
                zipf.writestr(filename, pdf_buffer.read())
    zip_buffer.seek(0)
    return zip_buffer

def exportar_excel_consolidado(consolidado_df):
    resumen = (
        consolidado_df
        .groupby(["Curso", "Tipo", "Desempeño"])
        .agg(Cantidad=("Nombre", "count"), Promedio_Puntaje=("Puntaje", "mean"))
        .reset_index()
    )
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        consolidado_df.to_excel(writer, index=False, sheet_name="Detalle_Estudiantes")
        resumen.to_excel(writer, index=False, sheet_name="Resumen_Cursos")
    output.seek(0)
    return output

# ------------------ MAIN APP ------------------

if "historico" not in st.session_state:
    st.session_state.historico = cargar_historico_desde_archivo()

st.title("📊 Análisis SIMCE y PAES")

# Subida múltiple
archivos = st.file_uploader("Sube uno o más archivos Excel", type=["xlsx"], accept_multiple_files=True)

if archivos:
    for archivo in archivos:
        try:
            df = pd.read_excel(archivo)
            st.success(f"Archivo '{archivo.name}' cargado correctamente.")
            st.dataframe(df)

            col_nombres = detectar_columna_nombres(df)
            col_puntajes = detectar_columna_puntajes(df)
            col_curso = detectar_columna_curso(df)
            col_anio = detectar_columna_anio(df)

            if not col_nombres or not col_puntajes:
                st.error(f"'{archivo.name}': No se detectaron nombres o puntajes.")
                continue

            if not col_curso:
                col_curso = st.selectbox(f"Selecciona columna de curso para '{archivo.name}'", df.columns, key=f"curso_{archivo.name}")

            if not col_anio:
                col_anio = st.selectbox(f"Selecciona columna de año académico para '{archivo.name}' (opcional)", ["(Ninguna)"] + df.columns.tolist(), key=f"anio_{archivo.name}")
                if col_anio == "(Ninguna)":
                    col_anio = None

            tipo_prueba = st.selectbox(f"Selecciona tipo de prueba para '{archivo.name}'", ["SIMCE", "PAES"], key=f"tipo_{archivo.name}")

            df["Nombre Normalizado"] = df[col_nombres].apply(normalizar_nombre)
            df["Puntaje"] = pd.to_numeric(df[col_puntajes], errors='coerce')
            df["Desempeño"] = df["Puntaje"].apply(lambda x: clasificar_puntaje(x, tipo_prueba))
            df["Prueba"] = tipo_prueba
            df["Fecha"] = datetime.today().strftime('%Y-%m-%d')
            df["Curso"] = df[col_curso].astype(str)
            df["Año"] = df[col_anio].astype(str) if col_anio else str(datetime.today().year)

            for _, row in df.iterrows():
                nombre_key = row["Nombre Normalizado"]
                if nombre_key not in st.session_state.historico:
                    st.session_state.historico[nombre_key] = []

                registro = {
                    "Nombre": row[col_nombres],
                    "Curso": row["Curso"],
                    "Fecha": row["Fecha"],
                    "Puntaje": row["Puntaje"],
                    "Desempeño": row["Desempeño"],
                    "Prueba": row["Prueba"],
                    "Año": row["Año"]
                }

                if registro not in st.session_state.historico[nombre_key]:
                    st.session_state.historico[nombre_key].append(registro)

            guardar_historico_en_archivo(st.session_state.historico)

        except Exception as e:
            st.error(f"Error al procesar '{archivo.name}': {e}")
