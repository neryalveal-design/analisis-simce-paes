
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import os

st.set_page_config(page_title="Análisis SIMCE y PAES", layout="wide")

DB_PATH = "analisis.db"

# Crear base de datos si no existe
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analisis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curso TEXT,
                tipo_prueba TEXT,
                fecha TEXT,
                archivo TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resultados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analisis_id INTEGER,
                estudiante TEXT,
                puntaje REAL,
                desempeno TEXT,
                prueba TEXT,
                FOREIGN KEY(analisis_id) REFERENCES analisis(id)
            )
        """)

# Clasificación por tipo
def clasificar_puntaje(valor, tipo):
    if pd.isna(valor):
        return "Sin dato"
    valor = float(valor)
    if tipo == "SIMCE":
        if valor <= 250:
            return "Insuficiente"
        elif valor <= 285:
            return "Intermedio"
        else:
            return "Adecuado"
    elif tipo == "PAES":
        if valor < 600:
            return "Insuficiente"
        elif valor < 800:
            return "Intermedio"
        else:
            return "Adecuado"
    return "Desconocido"

# Insertar nuevo análisis
def guardar_analisis(curso, tipo_prueba, archivo_nombre, df, puntaje_cols):
    fecha = datetime.today().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO analisis (curso, tipo_prueba, fecha, archivo) VALUES (?, ?, ?, ?)",
                       (curso, tipo_prueba, fecha, archivo_nombre))
        analisis_id = cursor.lastrowid

        for _, row in df.iterrows():
            for col in puntaje_cols:
                puntaje = row[col]
                desempeno = clasificar_puntaje(puntaje, tipo_prueba)
                cursor.execute("INSERT INTO resultados (analisis_id, estudiante, puntaje, desempeno, prueba) VALUES (?, ?, ?, ?, ?)",
                               (analisis_id, row["Estudiante"], puntaje, desempeno, col))
        conn.commit()

# Cargar análisis anteriores
def cargar_analisis():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM analisis ORDER BY fecha DESC", conn)

def cargar_resultados_por_analisis(analisis_id):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM resultados WHERE analisis_id = ?", conn, params=(analisis_id,))

# UI
init_db()
st.sidebar.title("📂 Menú")
opcion = st.sidebar.selectbox("Ir a:", ["📤 Cargar nuevo análisis", "📚 Ver análisis anteriores"])

if opcion == "📤 Cargar nuevo análisis":
    st.title("📊 Nuevo Análisis SIMCE o PAES")
    tipo_prueba = st.selectbox("Tipo de prueba", ["SIMCE", "PAES"])
    archivo = st.file_uploader("Sube archivo Excel", type=["xlsx"])

    if archivo:
        xls = pd.ExcelFile(archivo)
        hojas = xls.sheet_names
        hoja = st.selectbox("Selecciona hoja (curso)", hojas)
        df = xls.parse(hoja)

        col_nombres = next((col for col in df.columns if df[col].astype(str).str.contains(r"[A-Za-z]").sum() > 3), None)
        col_puntajes = [col for col in df.columns if pd.to_numeric(df[col], errors='coerce').gt(100).sum() > 3]

        if not col_nombres or not col_puntajes:
            st.error("No se detectaron columnas válidas de nombres o puntajes.")
        else:
            df["Estudiante"] = df[col_nombres]
            st.dataframe(df[[col_nombres] + col_puntajes])

            if st.button("📥 Guardar análisis"):
                guardar_analisis(hoja, tipo_prueba, archivo.name, df, col_puntajes)
                st.success("✅ Análisis guardado exitosamente.")

elif opcion == "📚 Ver análisis anteriores":
    st.title("📚 Análisis anteriores")
    analisis_df = cargar_analisis()
    if analisis_df.empty:
        st.info("No hay análisis guardados aún.")
    else:
        seleccion = st.selectbox("Selecciona un análisis", analisis_df.apply(lambda x: f"{x['fecha']} - {x['curso']} ({x['tipo_prueba']})", axis=1))
        idx = analisis_df.index[analisis_df.apply(lambda x: f"{x['fecha']} - {x['curso']} ({x['tipo_prueba']})", axis=1) == seleccion][0]
        analisis_id = analisis_df.loc[idx, "id"]
        resultados = cargar_resultados_por_analisis(analisis_id)
        st.dataframe(resultados)

        # Gráfico de rendimiento
        st.subheader("📈 Rendimiento")
        fig, ax = plt.subplots()
        resultados["desempeno"].value_counts().plot(kind="bar", ax=ax)
        st.pyplot(fig)
