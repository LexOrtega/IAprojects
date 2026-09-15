# -*- coding: utf-8 -*-
"""Asistente nutricional con Streamlit, Groq y RAG."""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

import gdown
import streamlit as st
from groq import Groq


st.set_page_config(
    page_title="Asistente nutricional",
    page_icon="🦈",
    layout="wide",
    initial_sidebar_state="expanded",
)

FOLDER_URL = "https://drive.google.com/drive/folders/1o4R584XeJsC_3AF_BH0EVCJv-3DcTfGy?usp=sharing"
DATA_DIR = Path("data")
APP_DIR = Path(__file__).resolve().parent

ARCHIVOS_REQUERIDOS = {
    "equivalencias": "equivalencias.json",
    "recetas": "recetas.json",
    "imagen": "imgbg.png",
}

MODELOS_NO_CHAT = (
    "whisper",
    "prompt-guard",
    "safeguard",
    "orpheus",
    "tts",
    "audio",
)


def archivo_a_data_uri(path: Path) -> str:
    if not path.exists():
        return ""

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def cargar_css(hero_data_uri: str) -> None:
    hero_background = f'url("{hero_data_uri}")' if hero_data_uri else "none"

    st.markdown(
        f"""
        <style>
        :root {{
            --panel: #f7fbf7;
            --ink: #203127;
            --muted: #5b6d61;
            --green: #54b300;
        }}

        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(121, 242, 79, 0.18), transparent 28%),
                linear-gradient(135deg, #102017 0%, #07100b 100%);
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        [data-testid="stSidebar"] {{
            background: #101713;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }}

        [data-testid="stSidebar"] * {{
            color: #edf8ef;
        }}

        .main .block-container {{
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }}

        .hero {{
            position: relative;
            min-height: 330px;
            padding: 42px 48px;
            overflow: hidden;
            border-radius: 28px 28px 0 0;
            background:
                linear-gradient(90deg, rgba(16, 23, 19, 0.98) 0%, rgba(16, 23, 19, 0.94) 48%, rgba(104, 232, 72, 0.88) 100%);
            box-shadow: 0 28px 90px rgba(0, 0, 0, 0.28);
        }}

        .hero::after {{
            content: "";
            position: absolute;
            top: 22px;
            right: 28px;
            width: 38%;
            height: 86%;
            background-image: {hero_background};
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            filter: drop-shadow(0 28px 34px rgba(0, 0, 0, 0.35));
        }}

        .hero-content {{
            position: relative;
            z-index: 2;
            max-width: 680px;
        }}

        .topline {{
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 34px;
            font-weight: 900;
            color: #ffffff;
        }}

        .brand-note {{
            color: #d8f8d3;
            font-size: 0.95rem;
        }}

        .hero h1 {{
            margin: 0 0 22px;
            color: #ffffff;
            font-size: clamp(2rem, 4vw, 3.2rem);
            line-height: 1.02;
            font-weight: 900;
        }}

        .hero p {{
            margin: 0 0 16px;
            color: #d9e4dc;
            font-size: 1.08rem;
            line-height: 1.55;
            font-weight: 560;
        }}

        .panel {{
            padding: 34px 42px 42px;
            background: var(--panel);
            border-radius: 0 0 28px 28px;
            box-shadow: 0 28px 90px rgba(0, 0, 0, 0.28);
        }}

        .panel h2, .panel h3, .panel p, .panel li {{
            color: var(--ink);
        }}

        .hint {{
            color: var(--muted);
            font-weight: 650;
            margin-bottom: 0.8rem;
        }}

        .answer-card {{
            padding: 1.35rem 1.5rem;
            border: 1px solid #cfe2d4;
            border-radius: 20px;
            background: #ffffff;
            color: var(--ink);
            box-shadow: 0 16px 40px rgba(45, 74, 57, 0.10);
            margin-top: 1.3rem;
        }}

        .answer-card * {{
            color: var(--ink) !important;
        }}

        div.stButton > button:first-child {{
            width: 100%;
            min-height: 48px;
            border-radius: 14px;
            border: 0;
            background: var(--green);
            color: #ffffff;
            font-weight: 900;
            font-size: 1rem;
        }}

        textarea, input, [data-baseweb="select"] > div {{
            border-radius: 14px !important;
        }}

        @media (max-width: 760px) {{
            .hero {{
                padding: 30px 24px 230px;
            }}

            .hero::after {{
                width: 80%;
                height: 220px;
                top: auto;
                right: 10%;
                bottom: 8px;
            }}

            .panel {{
                padding: 28px 22px 34px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def localizar_archivo(nombre: str) -> Path | None:
    candidatos = [
        APP_DIR / nombre,
        DATA_DIR / nombre,
        Path("/content") / nombre,
    ]

    for candidato in candidatos:
        if candidato.exists():
            return candidato

    for base in (DATA_DIR, APP_DIR):
        if base.exists():
            encontrados = list(base.rglob(nombre))
            if encontrados:
                return encontrados[0]

    return None


@st.cache_data(show_spinner="Descargando archivos del recetario...")
def preparar_archivos() -> dict[str, str]:
    faltantes = [
        nombre
        for nombre in ARCHIVOS_REQUERIDOS.values()
        if localizar_archivo(nombre) is None
    ]

    if faltantes:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        gdown.download_folder(
            url=FOLDER_URL,
            output=str(DATA_DIR),
            quiet=True,
            use_cookies=False,
        )

    rutas = {}
    for clave, nombre in ARCHIVOS_REQUERIDOS.items():
        ruta = localizar_archivo(nombre)
        if ruta is None:
            raise FileNotFoundError(
                f"No se encontro {nombre}. Verifica que la carpeta de Drive sea publica."
            )
        rutas[clave] = str(ruta)

    return rutas


@st.cache_data(show_spinner="Cargando recetas y equivalencias...")
def cargar_datos(ruta_eq: str, ruta_rec: str) -> tuple[list[dict], dict]:
    with open(ruta_eq, "r", encoding="utf-8") as f:
        equivalencias_full = json.load(f)

    with open(ruta_rec, "r", encoding="utf-8") as f:
        recetas_full = json.load(f)

    return equivalencias_full["equivalencias"], recetas_full["recetas"]


def normalizar(texto: str) -> str:
    texto = texto.lower()
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n", "ü": "u"}
    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


@st.cache_data(show_spinner=False)
def construir_indices(equivalencias: list[dict], recetas: dict) -> tuple[dict, dict, dict]:
    idx_equivalencias = {normalizar(e["alimento"]): e for e in equivalencias}

    idx_recetas = {}
    for cat, lista in recetas.items():
        for receta in lista:
            idx_recetas[receta["id"]] = {**receta, "categoria": cat}

    idx_ingrediente_a_recetas = {}
    for rid, receta in idx_recetas.items():
        for ing in receta["ingredientes"]:
            key = normalizar(ing["alimento"])
            idx_ingrediente_a_recetas.setdefault(key, []).append(rid)

    return idx_equivalencias, idx_recetas, idx_ingrediente_a_recetas


def buscar_equivalencias(query: str, idx_equivalencias: dict, top_k: int = 10) -> list[dict]:
    q = normalizar(query)
    palabras = q.split()
    resultados = []

    for key, eq in idx_equivalencias.items():
        score = sum(1 for p in palabras if p in key)
        if score > 0:
            resultados.append((score, eq))

    resultados.sort(key=lambda x: -x[0])
    return [eq for _, eq in resultados[:top_k]]


def buscar_recetas_por_ingrediente(
    ingrediente: str,
    idx_recetas: dict,
    idx_ingrediente_a_recetas: dict,
    top_k: int = 10,
) -> list[dict]:
    key = normalizar(ingrediente)
    ids = []

    for ingrediente_key, receta_ids in idx_ingrediente_a_recetas.items():
        if key in ingrediente_key:
            ids.extend(receta_ids)

    ids = list(dict.fromkeys(ids))[:top_k]
    return [idx_recetas[i] for i in ids]


def buscar_recetas_por_categoria(categoria: str, recetas: dict) -> list[dict]:
    mapa = {
        "desayuno": "desayuno",
        "colacionmatutina": "colacionMatutina",
        "colacion matutina": "colacionMatutina",
        "comida": "comida",
        "cena": "cena",
        "colacionnocturna": "colacionNocturna",
        "colacion nocturna": "colacionNocturna",
    }
    key = normalizar(categoria).replace(" ", "")
    cat_real = mapa.get(key) or mapa.get(normalizar(categoria))

    if cat_real and cat_real in recetas:
        return [{**r, "categoria": cat_real} for r in recetas[cat_real]]

    return []


def buscar_recetas_por_nombre(nombre: str, idx_recetas: dict, top_k: int = 5) -> list[dict]:
    q = normalizar(nombre)
    palabras = q.split()
    resultados = []

    for _, receta in idx_recetas.items():
        nombre_norm = normalizar(receta["nombre"])
        score = sum(1 for p in palabras if p in nombre_norm)
        if score > 0:
            resultados.append((score, receta))

    resultados.sort(key=lambda x: -x[0])
    return [receta for _, receta in resultados[:top_k]]


def formatear_equivalencia(eq: dict) -> str:
    return f"- {eq['alimento']}: {eq['cantidad']} (grupo: {eq['grupo']})"


def formatear_receta(receta: dict) -> str:
    lines = [f"### {receta['nombre']} (id: {receta['id']}, categoria: {receta.get('categoria', '?')})"]
    lines.append("Intercambios: " + ", ".join(f"{k}={v}" for k, v in receta["intercambios"].items()))
    lines.append("Ingredientes:")

    for ing in receta["ingredientes"]:
        lines.append(f"  - {ing['alimento']} x{ing['cantidadPorcion']} porcion(es)")

    lines.append("Preparacion:")
    for paso in receta["preparacion"]:
        lines.append(f"  - {paso}")

    lines.append(f"Tiempo: {receta['tiempo_preparacion_min']} min | Porciones: {receta['porciones']}")
    return "\n".join(lines)


def recuperar_contexto(
    pregunta: str,
    recetas: dict,
    idx_equivalencias: dict,
    idx_recetas: dict,
    idx_ingrediente_a_recetas: dict,
) -> str:
    q_norm = normalizar(pregunta)
    recetas_rec = []
    eq_rec = []

    for cat in [
        "desayuno",
        "colacion matutina",
        "colacionmatutina",
        "comida",
        "cena",
        "colacion nocturna",
        "colacionnocturna",
    ]:
        if cat in q_norm:
            recetas_rec.extend(buscar_recetas_por_categoria(cat, recetas))

    stopwords = {
        "que", "con", "sin", "para", "como", "receta", "recetas", "dame",
        "muestrame", "opciones", "tengo", "puedo", "hacer", "usar",
        "el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "o",
        "preparar", "preparacion", "ingredientes", "cantidad", "cantidades",
    }
    palabras = [p for p in q_norm.split() if p not in stopwords and len(p) > 2]

    for palabra in palabras:
        eq_rec.extend(buscar_equivalencias(palabra, idx_equivalencias, top_k=3))
        recetas_rec.extend(
            buscar_recetas_por_ingrediente(
                palabra,
                idx_recetas,
                idx_ingrediente_a_recetas,
                top_k=5,
            )
        )

    recetas_rec.extend(buscar_recetas_por_nombre(pregunta, idx_recetas, top_k=3))

    recetas_final = []
    recetas_vistas = set()
    for receta in recetas_rec:
        if receta["id"] not in recetas_vistas:
            recetas_vistas.add(receta["id"])
            recetas_final.append(receta)

    eq_final = []
    eq_vistas = set()
    for eq in eq_rec:
        if eq["alimento"] not in eq_vistas:
            eq_vistas.add(eq["alimento"])
            eq_final.append(eq)

    partes = []
    if eq_final:
        partes.append("EQUIVALENCIAS RELEVANTES:\n" + "\n".join(formatear_equivalencia(e) for e in eq_final[:15]))

    if recetas_final:
        partes.append("RECETAS RELEVANTES:\n" + "\n\n".join(formatear_receta(r) for r in recetas_final[:8]))

    return "\n\n".join(partes) if partes else "No se encontro contexto relevante."


def preguntar(
    pregunta: str,
    modelo: str,
    client: Groq,
    recetas: dict,
    idx_equivalencias: dict,
    idx_recetas: dict,
    idx_ingrediente_a_recetas: dict,
) -> str:
    contexto = recuperar_contexto(
        pregunta,
        recetas,
        idx_equivalencias,
        idx_recetas,
        idx_ingrediente_a_recetas,
    )

    system_prompt = """Eres un asistente nutricional experto en el plan de alimentacion del usuario.
Respondes en espanol, de forma clara y concisa.
Solo usas la informacion del CONTEXTO proporcionado. Si algo no esta en el contexto, dilo explicitamente.
Cuando des una receta, incluye: nombre, ingredientes con porciones, preparacion paso a paso, tiempo estimado e intercambios.
Cuando des equivalencias, indica el alimento, la cantidad y el grupo."""

    user_prompt = f"""CONTEXTO:
{contexto}

PREGUNTA DEL USUARIO:
{pregunta}
"""

    respuesta = client.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1500,
    )
    return respuesta.choices[0].message.content


def etiqueta_categoria(cat: str) -> str:
    nombres = {
        "desayuno": "Desayuno",
        "colacionMatutina": "Colacion matutina",
        "comida": "Comida",
        "cena": "Cena",
        "colacionNocturna": "Colacion nocturna",
    }
    return nombres.get(cat, cat)


def crear_catalogo(idx_recetas: dict) -> dict[str, str]:
    catalogo = {}
    for rid, receta in idx_recetas.items():
        etiqueta = f"{receta['nombre']} · {etiqueta_categoria(receta.get('categoria', '?'))} · {rid}"
        catalogo[etiqueta] = rid
    return dict(sorted(catalogo.items()))


def recetas_por_categoria(categoria: str, catalogo: dict, idx_recetas: dict) -> list[str]:
    opciones = []
    for etiqueta, rid in catalogo.items():
        receta = idx_recetas[rid]
        if categoria == "Todas" or etiqueta_categoria(receta.get("categoria", "?")) == categoria:
            opciones.append(etiqueta)
    return opciones


def resumen_receta(receta: dict) -> str:
    ingredientes = "\n".join(
        f"- {ing['alimento']} x{ing['cantidadPorcion']} porcion(es)"
        for ing in receta["ingredientes"]
    )
    intercambios = ", ".join(f"{k}={v}" for k, v in receta["intercambios"].items())

    return f"""
### {receta['nombre']}

**Categoria:** {etiqueta_categoria(receta.get("categoria", "?"))}

**Tiempo estimado:** {receta['tiempo_preparacion_min']} min

**Porciones:** {receta['porciones']}

**Ingredientes:**

{ingredientes}

**Intercambios:** {intercambios}
"""


def preguntar_sobre_receta(pregunta: str, receta: dict, modelo: str, client: Groq) -> str:
    contexto_receta = formatear_receta(receta)

    system_prompt = """Eres un asistente nutricional experto en el plan de alimentacion del usuario.
Respondes en espanol, de forma clara y concisa.
El usuario eligio una receta especifica del catalogo.
Prioriza esa receta para responder.
Si la pregunta requiere informacion que no esta en la receta seleccionada, dilo explicitamente.
Cuando hables de ingredientes, porciones, preparacion, tiempo o intercambios, usa unicamente la informacion del contexto."""

    user_prompt = f"""RECETA SELECCIONADA:
{contexto_receta}

PREGUNTA DEL USUARIO:
{pregunta}
"""

    respuesta = client.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1500,
    )

    return respuesta.choices[0].message.content


def obtener_api_key() -> str:
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.getenv("GROQ_API_KEY", "")


@st.cache_resource(show_spinner=False)
def crear_cliente(api_key: str) -> Groq:
    return Groq(api_key=api_key)


@st.cache_data(show_spinner="Consultando modelos disponibles...")
def obtener_modelos(api_key: str) -> list[str]:
    client = Groq(api_key=api_key)
    modelos = client.models.list()
    filtrados = sorted(
        [
            m.id
            for m in modelos.data
            if not any(bloqueado in m.id.lower() for bloqueado in MODELOS_NO_CHAT)
        ]
    )
    return filtrados or ["openai/gpt-oss-20b"]


def modelo_default(modelos: list[str]) -> str:
    for candidato in ("openai/gpt-oss-20b", "llama-3.1-8b-instant"):
        if candidato in modelos:
            return candidato
    return modelos[0]


def main() -> None:
    api_key = obtener_api_key()
    if not api_key:
        st.error("Falta configurar el secret GROQ_API_KEY en Streamlit Cloud.")
        st.stop()

    try:
        rutas = preparar_archivos()
        equivalencias, recetas = cargar_datos(rutas["equivalencias"], rutas["recetas"])
    except Exception as exc:
        st.error("No pude cargar los archivos del recetario.")
        st.exception(exc)
        st.stop()

    idx_equivalencias, idx_recetas, idx_ingrediente_a_recetas = construir_indices(equivalencias, recetas)
    catalogo = crear_catalogo(idx_recetas)
    cargar_css(archivo_a_data_uri(Path(rutas["imagen"])))

    client = crear_cliente(api_key)

    try:
        modelos = obtener_modelos(api_key)
    except Exception:
        modelos = ["openai/gpt-oss-20b", "llama-3.1-8b-instant"]

    with st.sidebar:
        st.markdown("## Configuracion")
        modelo = st.selectbox(
            "Modelo de IA",
            modelos,
            index=modelos.index(modelo_default(modelos)),
            help="Modelos cargados desde Groq. Si uno falla por limite o contexto, prueba otro.",
        )

        st.markdown("---")
        st.markdown("## Catalogo de recetas")
        categorias = ["Todas"] + [etiqueta_categoria(cat) for cat in recetas.keys()]
        categoria = st.selectbox("Filtrar por categoria", categorias)

        opciones = recetas_por_categoria(categoria, catalogo, idx_recetas)
        if not opciones:
            st.error("No encontre recetas para esta categoria.")
            st.stop()

        receta_label = st.selectbox("Elegir receta", opciones)
        receta = idx_recetas[catalogo[receta_label]]

        usar_receta = st.toggle(
            "Responder usando esta receta",
            value=True,
            help="Si lo desactivas, la pregunta se responde con busqueda general en todo el recetario.",
        )

        with st.expander("Ver resumen de la receta", expanded=True):
            st.markdown(resumen_receta(receta))

    st.markdown(
        """
        <section class="hero">
            <div class="hero-content">
                <div class="topline">
                    <span>Asistente nutricional</span>
                    <span class="brand-note">By AIOM</span>
                </div>
                <h1>Come mejor<br>sin complicarte</h1>
                <p>
                    Hola, soy un agente que puede ayudarte a seguir un regimen nutricional
                    disenado para un usuario con caracteristicas particulares.
                </p>
                <p>
                    Uso informacion sobre ingredientes, cantidades por porcion, equivalencias
                    y tus recetas previamente definidas.
                </p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<section class="panel">', unsafe_allow_html=True)
    st.markdown("### Haz tu pregunta")
    st.markdown(
        '<p class="hint">Puedes preguntar sobre recetas, equivalencias o ingredientes. '
        'Tambien puedes elegir una receta del catalogo y preguntar especificamente sobre ella.</p>',
        unsafe_allow_html=True,
    )

    if usar_receta:
        st.info(f"Pregunta enfocada en: {receta['nombre']}")

    pregunta_usuario = st.text_area(
        "Escribe tu pregunta",
        placeholder="Ej: ¿Que puedo comer hoy que tenga pollo?",
        height=145,
    )

    col_enviar, col_limpiar = st.columns([4, 1])
    enviar = col_enviar.button("Enviar", type="primary")
    limpiar = col_limpiar.button("Limpiar")

    if limpiar:
        st.session_state.pop("respuesta", None)
        st.rerun()

    if enviar:
        if not pregunta_usuario.strip():
            st.warning("Escribe una pregunta para que pueda ayudarte.")
        else:
            with st.spinner("Pensando..."):
                try:
                    if usar_receta:
                        respuesta = preguntar_sobre_receta(
                            pregunta_usuario.strip(),
                            receta,
                            modelo,
                            client,
                        )
                    else:
                        respuesta = preguntar(
                            pregunta_usuario.strip(),
                            modelo,
                            client,
                            recetas,
                            idx_equivalencias,
                            idx_recetas,
                            idx_ingrediente_a_recetas,
                        )
                    st.session_state["respuesta"] = respuesta
                except Exception as exc:
                    st.session_state["respuesta"] = (
                        "### El modelo seleccionado no pudo responder esta consulta\n\n"
                        f"Prueba con otro modelo disponible.\n\nDetalle tecnico: `{exc}`"
                    )

    if "respuesta" in st.session_state:
        st.markdown('<div class="answer-card">', unsafe_allow_html=True)
        st.markdown(st.session_state["respuesta"])
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</section>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
