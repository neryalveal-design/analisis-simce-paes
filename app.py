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
import zipfile

st.set_page_config(layout="wide", page_title="Análisis SIMCE y PAES")

# Funciones auxiliares

def clasificar_puntaje(puntaje, tipo):
    if tipo == "SIMCE":
        if puntaje <= 250:
            return "Insuficiente"
        elif puntaje <= 279:
            return "Elemental"
        else:
            return "Avanzado"
    elif tipo == "PAES":
        if puntaje <= 500:
            return "Insuficiente"
        elif puntaje <= 799:
            return "Elemental"
        else:
            return "Avanzado"
    return "Desconocido"

def normalizar_nombre(nombre):
    nombre = str(nombre).lower()
    nombre = unicodedata.normalize('NFKD', nombre).encode('ASCII', 'ignore').decode()
    nombre = re.sub(r'\s+', ' ', nombre)
    nombre = nombre.strip()
    partes = nombre.split()
    return ' '.join(partes[:2]) if len(partes) > 1 else nombre

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
    for col in df.columns:
        if df[col].astype(str).str.contains(r'\d+[A-Za-z]', regex=True).mean() > 0.5:
            return col
    return None

def detectar_columna_anio(df):
    for col in df.columns:
        if df[col].astype(str).str.contains('202').mean() > 0.5:
            return col
    return None

def es_archivo_resumen_por_curso(df):
    return (
        "Curso" in df.columns and
        "Promedio último" in df.columns and
        "% Insuficiente" in df.columns
    )

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
                "Año": r["Año"]
            })
    return pd.DataFrame(consolidado)

# PDF personalizado

class PDFReporte(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Reporte Comparativo de Desempeño SIMCE/PAES", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

def generar_pdf_estudiante(registros):
    pdf = PDFReporte()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    nombre = registros[0]["Nombre"]
    curso = registros[0]["Curso"]

    pdf.cell(0, 10, f"Nombre: {nombre}", ln=True)
    pdf.cell(0, 10, f"Curso: {curso}", ln=True)

    for r in registros:
        pdf.cell(0, 10, f"{r['Fecha']} - {r['Prueba']} - Puntaje: {r['Puntaje']} ({r['Desempeño']})", ln=True)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

def guardar_historico_en_archivo(historico):
    pass  # Por si deseas implementar guardado local

# ========== MAIN APP ==========

st.title("📊 Análisis SIMCE y PAES")

if "historico" not in st.session_state:
    st.session_state.historico = {}

# Botón para limpiar análisis anterior
if st.button("🧹 Limpiar análisis anterior"):
    st.session_state.historico = {}
    st.success("Análisis anterior eliminado.")

archivos = st.file_uploader("Sube uno o más archivos Excel", type=["xlsx"], accept_multiple_files=True)

if archivos:
    for archivo in archivos:
        try:
            df = pd.read_excel(archivo)

            if es_archivo_resumen_por_curso(df):
                st.success("📄 Detectado archivo resumen por curso")
                st.subheader("📋 Resumen por curso")
                st.dataframe(df)

                # Gráfico: promedio por curso
                st.subheader("📈 Promedio por curso")
                fig1, ax1 = plt.subplots()
                ax1.bar(df["Curso"], df["Promedio último"])
                ax1.set_ylabel("Puntaje promedio")
                st.pyplot(fig1)

                # Gráfico: niveles por curso
                st.subheader("📊 Distribución por nivel")
                niveles = ["% Insuficiente", "% Elemental", "% Avanzado"]
                df_plot = df[["Curso"] + niveles].set_index("Curso")
                fig2, ax2 = plt.subplots()
                df_plot.plot(kind="bar", stacked=True, ax=ax2)
                st.pyplot(fig2)

                continue  # Salta el análisis individual

            # === Análisis individual ===
            col_nombres = detectar_columna_nombres(df)
            col_puntajes = detectar_columna_puntajes(df)
            col_curso = detectar_columna_curso(df)
            col_anio = detectar_columna_anio(df)

            if not col_nombres or not col_puntajes:
                st.error(f"{archivo.name}: No se detectaron nombres o puntajes.")
                continue

            tipo_prueba = st.selectbox(f"Selecciona tipo de prueba para '{archivo.name}'", ["SIMCE", "PAES"])

            df["Nombre Normalizado"] = df[col_nombres].apply(normalizar_nombre)
            df["Puntaje"] = pd.to_numeric(df[col_puntajes], errors="coerce")
            df["Desempeño"] = df["Puntaje"].apply(lambda x: clasificar_puntaje(x, tipo_prueba))
            df["Prueba"] = tipo_prueba
            df["Fecha"] = datetime.today().strftime('%Y-%m-%d')
            df["Curso"] = df[col_curso].astype(str) if col_curso else "Sin curso"
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

            st.success(f"Archivo '{archivo.name}' cargado correctamente.")
            st.dataframe(df)

        except Exception as e:
            st.error(f"Error al procesar '{archivo.name}': {e}")

# ========== Reporte PDF por estudiante ==========

st.header("🧑‍🏫 Generar reporte PDF por estudiante")

estudiantes_disponibles = sorted(st.session_state.historico.keys())

if estudiantes_disponibles:
    estudiante = st.selectbox("Selecciona estudiante", estudiantes_disponibles)
    if st.button("📤 Generar PDF Individual"):
        registros = st.session_state.historico[estudiante]
        pdf_file = generar_pdf_estudiante(registros)
        st.download_button("📥 Descargar PDF", pdf_file, file_name=f"{estudiante}.pdf")

# ========== Consolidado global ==========

consolidado = generar_consolidado_global(st.session_state.historico)

if not consolidado.empty:
    st.header("📁 Exportar consolidado a Excel")
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            consolidado.to_excel(writer, index=False, sheet_name="Consolidado")
        output.seek(0)
        st.download_button("📥 Descargar consolidado", output, file_name="consolidado.xlsx")
    except ModuleNotFoundError:
        st.error("Falta el módulo 'xlsxwriter'. Instálalo con: pip install xlsxwriter")
