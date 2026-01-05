import streamlit as st
import pandas as pd
import random
import whois
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(
    page_title="Generador y Verificador de Dominios",
    layout="wide"
)

# =====================
# GENERADOR
# =====================
st.title("🔧 Generador + Verificador de Dominios De ArturoVE")

col1, col2, col3, col4, col5 = st.columns([1, 1, 1.5, 1.2, 1.2])

with col1:
    cantidad = st.number_input(
        "Cantidad",
        min_value=1,
        max_value=1000,
        value=100,
        step=1
    )

with col2:
    extension = st.text_input(
        "Extensión",
        value=".me",
        help="Ej: .me, .com, .mx, .app"
    )

with col3:
    longitud = st.slider(
        "Longitud del nombre",
        min_value=1,
        max_value=20,
        value=(3, 4)
    )

with col4:
    modo = st.selectbox(
        "Modo de generación",
        ["Aleatorio", "Pronunciable"]
    )

with col5:
    generar = st.button(
        "🎲 Generar dominios",
        use_container_width=True
    )

letras = "abcdefghijklmnopqrstuvwxyz"
numeros = "0123456789"
vocales = "aeiou"
consonantes = "bcdfghjklmnpqrstvwxyz"


def generar_aleatorio(ext, rango):
    l = random.randint(rango[0], rango[1])
    return "".join(random.choices(letras + numeros, k=l)) + ext


def generar_pronunciable(ext, rango):
    l = random.randint(rango[0], rango[1])
    nombre = ""
    for i in range(l):
        nombre += random.choice(consonantes if i % 2 == 0 else vocales)
    return nombre + ext


if generar:
    dominios = set()
    while len(dominios) < cantidad:
        if modo == "Pronunciable":
            dominios.add(generar_pronunciable(extension, longitud))
        else:
            dominios.add(generar_aleatorio(extension, longitud))

    st.session_state["dominios_generados"] = sorted(dominios)
    st.session_state["generados_ok"] = True


if st.session_state.get("generados_ok"):
    st.success("✅ Dominios generados. Ya puedes descargarlos.")

    df_gen = pd.DataFrame(
        st.session_state["dominios_generados"],
        columns=["Dominio"]
    )

    st.download_button(
        "📥 Descargar lista generada",
        df_gen.to_csv(index=False).encode("utf-8"),
        "dominios_generados.csv",
        "text/csv"
    )

st.divider()

# =====================
# MÉTODO B (DNS + WHOIS)
# =====================
def tiene_dns(dominio):
    try:
        socket.gethostbyname(dominio)
        return True
    except:
        return False


def verificar_dominio(dominio):
    dominio = dominio.strip().lower()

    if tiene_dns(dominio):
        return "Ocupado"

    try:
        w = whois.whois(dominio)
        if w.domain_name:
            return "Ocupado"
    except:
        return "Desconocido"

    return "Disponible"


def link_compra(dominio, proveedor):
    if proveedor == "namecheap":
        return f"https://www.namecheap.com/domains/registration/results/?domain={dominio}"
    if proveedor == "godaddy":
        return f"https://www.godaddy.com/domainsearch/find?domainToCheck={dominio}"


# =====================
# VERIFICACIÓN RÁPIDA
# =====================
st.subheader("⚡ Verificación rápida de un dominio")

col_a, col_b = st.columns([3, 1])

with col_a:
    dominio_manual = st.text_input(
        "Escribe el dominio a verificar",
        placeholder="ejemplo: mipagina.me"
    )

with col_b:
    verificar_manual = st.button(
        "🔍 Verificar dominio",
        use_container_width=True
    )

if verificar_manual and dominio_manual:
    with st.spinner("Verificando dominio..."):
        estado = verificar_dominio(dominio_manual)

    if estado == "Disponible":
        st.success(f"🟢 {dominio_manual} está DISPONIBLE")
    elif estado == "Ocupado":
        st.error(f"🔴 {dominio_manual} está OCUPADO")
    else:
        st.warning(f"⚠️ No se pudo confirmar la disponibilidad de {dominio_manual}")

st.divider()

# =====================
# VERIFICADOR MASIVO
# =====================
st.header("🔍 Verificador de disponibilidad (archivo)")

archivo = st.file_uploader(
    "Sube un archivo CSV o Excel con una columna llamada 'Dominio'",
    type=["csv", "xlsx"]
)

filtro = st.selectbox(
    "Filtrar resultados",
    ["Todos", "Disponible", "Ocupado", "Desconocido"]
)

def color_filas(row):
    if row["Estado"] == "Disponible":
        return ["background-color: #1B8511"] * len(row)
    if row["Estado"] == "Ocupado":
        return ["background-color: #851111"] * len(row)
    return ["background-color: #FFBC00"] * len(row)


if archivo:
    if archivo.name.endswith(".csv"):
        df = pd.read_csv(archivo)
    else:
        df = pd.read_excel(archivo)

    if "Dominio" not in df.columns:
        st.error("❌ El archivo debe contener una columna llamada 'Dominio'")
    else:
        resultados = []

        with st.spinner("⚡ Verificando dominios (DNS + WHOIS)..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(verificar_dominio, d): d
                    for d in df["Dominio"]
                }

                for future in as_completed(futures):
                    resultados.append({
                        "Dominio": futures[future],
                        "Estado": future.result()
                    })

        res_df = pd.DataFrame(resultados)

        c_disp = (res_df["Estado"] == "Disponible").sum()
        c_ocu = (res_df["Estado"] == "Ocupado").sum()
        c_desc = (res_df["Estado"] == "Desconocido").sum()

        st.markdown(
            f"### 🟢 {c_disp} disponibles | 🔴 {c_ocu} ocupados | 🟡 {c_desc} desconocidos"
        )

        if filtro != "Todos":
            res_df = res_df[res_df["Estado"] == filtro]

        res_df["💰 Namecheap"] = res_df.apply(
            lambda r: link_compra(r["Dominio"], "namecheap")
            if r["Estado"] == "Disponible"
            else "",
            axis=1
        )

        res_df["💰 GoDaddy"] = res_df.apply(
            lambda r: link_compra(r["Dominio"], "godaddy")
            if r["Estado"] == "Disponible"
            else "",
            axis=1
        )

        styled_df = res_df.style.apply(color_filas, axis=1)

        st.dataframe(
            styled_df,
            use_container_width=True,
            column_config={
                "💰 Namecheap": st.column_config.LinkColumn(
                    "💰 Namecheap",
                    display_text="Comprar"
                ),
                "💰 GoDaddy": st.column_config.LinkColumn(
                    "💰 GoDaddy",
                    display_text="Comprar"
                ),
            }
        )

        st.download_button(
            "📥 Descargar resultados",
            res_df.to_csv(index=False).encode("utf-8"),
            "resultados_dominios.csv",
            "text/csv"
        )
