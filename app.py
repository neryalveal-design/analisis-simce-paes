
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Análisis Educativo SIMCE / PAES", layout="wide")

# --- Clasificación de puntajes ---
def clasificar_puntaje(puntaje, tipo):
    if pd.isna(puntaje):
        return "Sin dato"
    puntaje = float(puntaje)
    if tipo == "SIMCE":
        if puntaje <= 250:
            return "Insuficiente"
        elif puntaje <= 285:
            return "Intermedio"
        else:
            return "Adecuado"
    elif tipo == "PAES":
        if puntaje < 600:
            return "Insuficiente"
        elif puntaje < 800:
            return "Intermedio"
        else:
            return "Adecuado"
    return "Desconocido"

# --- Subida de archivo ---
st.title("📊 Análisis de Rendimiento SIMCE / PAES")
tipo_prueba = st.selectbox("🧪 Selecciona el tipo de prueba", ["SIMCE", "PAES"])
archivo = st.file_uploader("📁 Sube archivo Excel", type=["xlsx"])

if archivo:
    xls = pd.ExcelFile(archivo)
    hoja = st.selectbox("📄 Hoja (Curso)", xls.sheet_names)
    df = xls.parse(hoja)

    # Detectar columnas
    col_nombres = next((col for col in df.columns if df[col].astype(str).str.contains(r"[A-Za-z]").sum() > 3), None)
    col_puntajes = [col for col in df.columns if pd.to_numeric(df[col], errors='coerce').gt(100).sum() > 3]

    if not col_nombres or not col_puntajes:
        st.error("❌ No se detectaron columnas válidas de nombres o puntajes.")
    else:
        df["Estudiante"] = df[col_nombres]

        st.subheader("📋 Tabla de resultados")
        st.dataframe(df[["Estudiante"] + col_puntajes])

        # --- GRÁFICO DE CADA ENSAYO ---
        for col in col_puntajes:
            df[f"Desempeño {col}"] = df[col].apply(lambda x: clasificar_puntaje(x, tipo_prueba))

        st.subheader("📈 Gráficos de desempeño por ensayo")
        for col in col_puntajes:
            conteo = df[f"Desempeño {col}"].value_counts().reindex(["Insuficiente", "Intermedio", "Adecuado"], fill_value=0)
            fig, ax = plt.subplots(figsize=(4,3))
            conteo.plot(kind="bar", ax=ax)
            ax.set_title(f"Desempeño - {col}")
            ax.set_ylabel("Estudiantes")
            ax.set_xlabel("Nivel")
            plt.xticks(rotation=0)
            st.pyplot(fig)

        # --- ANÁLISIS DE TRAYECTORIA ---
        if len(col_puntajes) > 1:
            st.subheader("📉 Trayectoria de estudiantes")
            estudiante = st.selectbox("Selecciona estudiante", df["Estudiante"].unique())
            datos = df[df["Estudiante"] == estudiante][col_puntajes].T
            datos.columns = ["Puntaje"]
            fig, ax = plt.subplots(figsize=(5,3))
            datos.plot(ax=ax, marker="o", legend=False)
            ax.set_title(f"Trayectoria de {estudiante}")
            ax.set_ylabel("Puntaje")
            ax.set_xlabel("Ensayo")
            ax.set_ylim([min(200, datos["Puntaje"].min()-20), max(1000, datos["Puntaje"].max()+20)])
            plt.xticks(rotation=45)
            st.pyplot(fig)

        # --- TOP 15 PEOR RENDIMIENTO ---
        st.subheader("⚠️ Top 15 puntajes más bajos")
        col_puntaje_mostrar = st.selectbox("Selecciona ensayo para ranking", col_puntajes)
        peor_15 = df.sort_values(by=col_puntaje_mostrar).head(15)
        st.dataframe(peor_15[["Estudiante", col_puntaje_mostrar]])
