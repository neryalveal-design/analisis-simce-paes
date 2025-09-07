
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



# --- Selección de tipo de análisis ---
modo_analisis = st.radio("📂 Tipo de análisis", ["Ensayo único", "Consolidado (varios ensayos)"])



# --- Análisis general de todos los cursos ---
if st.checkbox("📊 Mostrar análisis general del liceo"):
    resultados_globales = []
    for hoja in xls.sheet_names:
        df_temp = xls.parse(hoja)
        col_nombres_temp = next((col for col in df_temp.columns if df_temp[col].astype(str).str.contains(r"[A-Za-z]").sum() > 3), None)
        col_puntajes_temp = [col for col in df_temp.columns if pd.to_numeric(df_temp[col], errors='coerce').gt(100).sum() > 3]
        if col_nombres_temp and col_puntajes_temp:
            for col in col_puntajes_temp:
                temp = df_temp[[col_nombres_temp, col]].dropna()
                temp["Curso"] = hoja
                temp["Ensayo"] = col
                temp["Desempeño"] = temp[col].apply(lambda x: clasificar_puntaje(x, tipo_prueba))
                resultados_globales.append(temp)

    if resultados_globales:
        df_global = pd.concat(resultados_globales)
        conteo_global = df_global.groupby(["Curso", "Desempeño"]).size().unstack(fill_value=0)
        st.subheader("📊 Panorama General del Liceo")
        st.dataframe(conteo_global)

        fig, ax = plt.subplots(figsize=(10, 5))
        conteo_global.plot(kind="bar", stacked=True, ax=ax)
        ax.set_title("Distribución de Desempeño por Curso")
        ax.set_ylabel("Cantidad de Estudiantes")
        st.pyplot(fig)



# --- Botón para resetear análisis ---
if st.button("🔄 Borrar análisis anterior"):
    st.experimental_rerun()



# --- Guardar y mostrar análisis anteriores ---
if "historial" not in st.session_state:
    st.session_state.historial = []

if st.button("💾 Guardar este análisis"):
    st.session_state.historial.append(df.copy())

if st.session_state.historial:
    st.subheader("🕘 Análisis anteriores")
    seleccion = st.selectbox("Selecciona un análisis guardado", range(len(st.session_state.historial)))
    st.dataframe(st.session_state.historial[seleccion])



# --- Top 15 mejores y peores ---
st.subheader("🥇 Top 15 Mejores y Peores Estudiantes")
for col in col_puntajes:
    st.markdown(f"**🔹 Ensayo: {col}**")
    top_peores = df[["Estudiante", col]].sort_values(by=col).head(15)
    top_mejores = df[["Estudiante", col]].sort_values(by=col, ascending=False).head(15)

    col1, col2 = st.columns(2)
    with col1:
        st.write("🔻 Puntajes más bajos")
        st.dataframe(top_peores)
    with col2:
        st.write("🔺 Puntajes más altos")
        st.dataframe(top_mejores)



# --- Descargar informe en PDF ---
import io
from matplotlib.backends.backend_pdf import PdfPages

def generar_pdf(df, col_puntajes, tipo_prueba):
    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        for col in col_puntajes:
            fig, ax = plt.subplots(figsize=(6, 4))
            conteo = df[f"Desempeño {col}"].value_counts().reindex(["Insuficiente", "Intermedio", "Adecuado"], fill_value=0)
            conteo.plot(kind="bar", ax=ax)
            ax.set_title(f"Desempeño - {col}")
            ax.set_ylabel("Estudiantes")
            ax.set_xlabel("Nivel")
            plt.xticks(rotation=0)
            pdf.savefig(fig)
            plt.close()
    buffer.seek(0)
    return buffer

if st.button("📥 Descargar informe PDF"):
    buffer_pdf = generar_pdf(df, col_puntajes, tipo_prueba)
    st.download_button("Descargar PDF", buffer_pdf, file_name="informe.pdf", mime="application/pdf")



# --- Descargar informe en Excel ---
import io

if st.button("📥 Descargar informe Excel"):
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Análisis")
    excel_buffer.seek(0)
    st.download_button("Descargar Excel", excel_buffer, file_name="informe.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
