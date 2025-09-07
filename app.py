
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Análisis SIMCE y PAES", layout="wide")

# --- Función de clasificación SIMCE ---
def clasificar_simce(puntaje):
    if pd.isna(puntaje):
        return "Sin dato"
    puntaje = float(puntaje)
    if puntaje <= 250:
        return "Insuficiente"
    elif puntaje <= 285:
        return "Intermedio"
    else:
        return "Adecuado"

# --- Subir archivo ---
st.title("📊 Análisis de Rendimiento SIMCE")
archivo = st.file_uploader("📁 Sube un archivo Excel con datos del ensayo", type=["xlsx"])

if archivo:
    xls = pd.ExcelFile(archivo)
    hojas = xls.sheet_names
    hoja = st.selectbox("📄 Selecciona la hoja (curso)", hojas)
    df = xls.parse(hoja)

    # Detectar columna de nombres
    col_nombres = next((col for col in df.columns if df[col].astype(str).str.contains(r"[A-Za-z]").sum() > 3), None)
    col_puntajes = [col for col in df.columns if pd.to_numeric(df[col], errors='coerce').gt(100).sum() > 3]

    if not col_nombres or not col_puntajes:
        st.error("❌ No se detectaron columnas válidas de nombres o puntajes.")
    else:
        df["Estudiante"] = df[col_nombres]
        col_ensayo = st.selectbox("🧪 Selecciona columna de puntaje", col_puntajes)
        df["Puntaje"] = df[col_ensayo]
        df["Desempeño"] = df["Puntaje"].apply(clasificar_simce)

        st.subheader("📋 Tabla de resultados")
        st.dataframe(df[["Estudiante", "Puntaje", "Desempeño"]])

        st.subheader("📈 Gráfico de desempeño")
        conteo = df["Desempeño"].value_counts().reindex(["Insuficiente", "Intermedio", "Adecuado"], fill_value=0)
        fig, ax = plt.subplots()
        conteo.plot(kind="bar", ax=ax)
        ax.set_title(f"Distribución de Desempeño - {col_ensayo}")
        ax.set_ylabel("Número de Estudiantes")
        ax.set_xlabel("Nivel de Desempeño")
        plt.xticks(rotation=0)
        st.pyplot(fig)
