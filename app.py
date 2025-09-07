
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from fpdf import FPDF
import base64

st.set_page_config(page_title="Análisis con Exportación a PDF", layout="wide")

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

def exportar_pdf(df, imagenes, filename="informe.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Informe de Desempeño Académico", ln=True, align="C")
    pdf.ln(10)

    for _, row in df.iterrows():
        pdf.cell(0, 10, f"{row['Estudiante']}: {row['Puntaje']} - {row['Desempeño']}", ln=True)

    for i, img in enumerate(imagenes):
        pdf.add_page()
        pdf.image(img, x=15, y=25, w=180)

    buffer = io.BytesIO()
    pdf.output(buffer)
    b64 = base64.b64encode(buffer.getvalue()).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">📄 Descargar PDF</a>'
    return href

st.title("📊 Análisis de Rendimiento + PDF")

tipo_prueba = st.selectbox("Tipo de prueba", ["SIMCE", "PAES"])
archivo = st.file_uploader("Sube archivo Excel", type=["xlsx"])

if archivo:
    xls = pd.ExcelFile(archivo)
    hoja = st.selectbox("Selecciona la hoja", xls.sheet_names)
    df = xls.parse(hoja)

    col_nombres = next((col for col in df.columns if df[col].astype(str).str.contains(r"[A-Za-z]").sum() > 3), None)
    col_puntajes = [col for col in df.columns if pd.to_numeric(df[col], errors='coerce').gt(100).sum() > 3]

    if not col_nombres or not col_puntajes:
        st.error("No se detectaron nombres o puntajes.")
    else:
        df["Estudiante"] = df[col_nombres]
        ensayo = st.selectbox("Selecciona columna de puntaje", col_puntajes)
        df["Puntaje"] = df[ensayo]
        df["Desempeño"] = df["Puntaje"].apply(lambda x: clasificar_puntaje(x, tipo_prueba))

        st.dataframe(df[["Estudiante", "Puntaje", "Desempeño"]])

        # Gráfico
        st.subheader("📈 Distribución de desempeño")
        conteo = df["Desempeño"].value_counts().reindex(["Insuficiente", "Intermedio", "Adecuado"], fill_value=0)
        fig, ax = plt.subplots(figsize=(4,3))
        conteo.plot(kind="bar", ax=ax)
        ax.set_title("Distribución de Desempeño")
        st.pyplot(fig)

        # Guardar imagen del gráfico
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format="PNG")
        img_buffer.seek(0)

        # Descargar PDF
        if st.button("📥 Exportar informe en PDF"):
            link = exportar_pdf(df[["Estudiante", "Puntaje", "Desempeño"]], [img_buffer])
            st.markdown(link, unsafe_allow_html=True)
