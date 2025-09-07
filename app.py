
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
def main():
    st.title("Análisis SIMCE y PAES")
    archivo = st.file_uploader("Sube un archivo Excel", type=["xlsx"])

    if archivo is not None:
        try:
            df = pd.read_excel(archivo)
            st.success("Archivo cargado correctamente.")
            st.dataframe(df)

            # Aquí podrías incluir más lógica de análisis si ya tienes funciones definidas.
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")

if __name__ == "__main__":
    main()
