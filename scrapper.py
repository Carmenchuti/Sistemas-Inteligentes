import os
import re
import time
import random
import hashlib
import requests
from bs4 import BeautifulSoup

# =====================
# CONFIG
# =====================

BASE_DIR = "Sistemas-Inteligentes/dataset"

HEADERS = {
    "User-Agent": "Chrome/124.0.0.0 Safari/537.36"
}

CATEGORIAS = ["deportes", "economia", "internacional"]
PERIODICOS = ["telemadrid", "elmundo", "okdiario"]

URLS_TELEMADRID = {
    "deportes": "https://www.telemadrid.es/deportes/",
    "economia": "https://www.telemadrid.es/noticias/economia/",
    "internacional": "https://www.telemadrid.es/noticias/internacional/"
}

URLS_ELMUNDO = {
    "deportes": "https://www.elmundo.es/deportes.html",
    "economia": "https://www.elmundo.es/economia.html",
    "internacional": "https://www.elmundo.es/internacional.html"
}

URLS_OKDIARIO = {
    "deportes": "https://okdiario.com/deportes/",
    "economia": "https://okdiario.com/economia/",
    "internacional": "https://okdiario.com/internacional/"
}

# =====================
# UTILS
# =====================

def asegurar_carpetas(base_dir=BASE_DIR):
    for cat in CATEGORIAS:
        for per in PERIODICOS:
            ruta = os.path.join(base_dir, cat, per)
            if not os.path.exists(ruta):
                os.makedirs(ruta)

def limpiar_nombre_archivo(texto, max_len=60):
    texto = (texto or "").strip().lower()
    texto = re.sub(r"\s+", "_", texto)
    texto = re.sub(r"[^a-z0-9áéíóúüñ_]+", "", texto, flags=re.IGNORECASE)
    if len(texto) > max_len:
        texto = texto[:max_len]
    if texto == "":
        texto = "noticia"
    return texto

def id_url(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]

def pedir_html(url, timeout=15, reintentos=3):
    for i in range(reintentos):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200 and r.text:
                return r.text
        except Exception:
            pass
        time.sleep(1 + i)
    return None

def pausa(min_s=1.0, max_s=2.5):
    time.sleep(random.uniform(min_s, max_s))

# =====================
# NO REPETIR NOTICIAS
# =====================

def ya_descargada(base_dir, categoria, periodico, url):
    """
    Devuelve True si ya existe un .txt cuyo nombre empieza por <id_url(url)>_
    dentro de dataset/<categoria>/<periodico>/
    """
    nid = id_url(url)
    carpeta = os.path.join(base_dir, categoria, periodico)
    if not os.path.exists(carpeta):
        return False

    prefijo = nid + "_"
    for nombre in os.listdir(carpeta):
        if nombre.startswith(prefijo) and nombre.lower().endswith(".txt"):
            return True
    return False

# =====================
# LIMPIEZA DE TEXTO (SIN "BASURA")
# =====================

def limpiar_texto_noticia(texto):
    if not texto:
        return ""

    texto = BeautifulSoup(texto, "html.parser").get_text(" ")
    texto = texto.replace("\xa0", " ")
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()

# =====================
# GUARDADO (METADATOS + TEXTO:)
# =====================

def guardar_noticia_txt(base_dir, categoria, periodico, url, titulo, fecha, texto):
    carpeta = os.path.join(base_dir, categoria, periodico)
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    nid = id_url(url)
    nombre = f"{nid}_{limpiar_nombre_archivo(titulo)}.txt"
    ruta = os.path.join(carpeta, nombre)

    texto_limpio = limpiar_texto_noticia(texto)

    contenido = []
    contenido.append(f"ID: {nid}")
    contenido.append(f"TITULO: {titulo}")
    contenido.append(f"FECHA: {fecha}")
    contenido.append(f"PERIODICO: {periodico}")
    contenido.append(f"CATEGORIA: {categoria}")
    contenido.append(f"URL: {url}")
    contenido.append("")
    contenido.append("TEXTO:")
    contenido.append(texto_limpio)

    f = open(ruta, "w", encoding="utf-8")
    f.write("\n".join(contenido).strip() + "\n")
    f.close()

# =====================
# VALIDACIÓN DE CATEGORÍA (ROBUSTA)
# =====================

def _norm(s):
    s = (s or "").strip().lower()
    s = (s.replace("í", "i").replace("ó", "o").replace("á", "a")
           .replace("é", "e").replace("ú", "u").replace("ü", "u")
           .replace("ñ", "n"))
    return s

def _equivalentes_categoria(categoria):
    cat = _norm(categoria)
    eq = {cat}
    if cat == "economia":
        eq.add("economia y negocios")
        eq.add("negocios")
    if cat == "internacional":
        eq.add("mundo")
    return eq

def _filtro_url_rapido(periodico, categoria, url):
    periodico = _norm(periodico)
    categoria = _norm(categoria)

    if periodico == "okdiario":
        return url.startswith("https://okdiario.com/" + categoria + "/")

    if periodico == "elmundo":
        return ("/" + categoria + "/") in url or ("/" + categoria + ".html") in url

    if periodico == "telemadrid":
        return ("/" + categoria + "/") in url

    return False

def url_corresponde_categoria(periodico, categoria, url):
    periodico = _norm(periodico)
    categoria = _norm(categoria)

    # ✅ TELEMADRID: validar SOLO por ruta
    if periodico == "telemadrid":
        if ("/" + categoria + "/") not in url:
            return False
        if not (url.endswith(".html") or url.endswith(".amp.html")):
            return False
        return True

    eqs = _equivalentes_categoria(categoria)

    if not _filtro_url_rapido(periodico, categoria, url):
        return False

    html = pedir_html(url)
    if not html:
        return False

    soup = BeautifulSoup(html, "html.parser")

    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        content = _norm(meta.get("content"))

        if prop in ["article:section", "section", "parsely-section", "page-section", "cg.section"]:
            for e in eqs:
                if e and e in content:
                    return True

    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        txt = sc.string
        if not txt:
            continue
        t = _norm(txt)
        for e in eqs:
            if ('"articlesection":"' + e) in t or ('"articlesection": "' + e) in t:
                return True
            if "breadcrumblist" in t and ('"name":"' + e) in t:
                return True

    for a in soup.find_all("a", href=True):
        texto = _norm(a.get_text(strip=True))
        href = (a.get("href") or "").lower()
        if texto in eqs:
            return True
        if ("/" + categoria + "/") in href:
            return True

    return False

# =====================
# EXTRACTORES (TITULO, FECHA, TEXTO)
# =====================

def extraer_okdiario(url):
    html = pedir_html(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    titulo = h1.get_text(strip=True) if h1 else "Sin título"

    time_tag = soup.find("time")
    fecha = time_tag.get_text(strip=True) if time_tag else "Sin fecha"

    article = soup.find("article") or soup
    parrafos = article.find_all("p")
    texto = "\n".join(p.get_text(strip=True) for p in parrafos if p.get_text(strip=True))

    return titulo, fecha, texto

def extraer_elmundo(url):
    html = pedir_html(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    titulo = h1.get_text(strip=True) if h1 else "Sin título"

    time_tag = soup.find("time")
    fecha = time_tag.get_text(strip=True) if time_tag else "Sin fecha"

    article = soup.find("article")
    if not article:
        return None

    parrafos = article.find_all("p")
    texto = "\n".join(p.get_text(strip=True) for p in parrafos if p.get_text(strip=True))
    return titulo, fecha, texto

def extraer_telemadrid(url):
    html = pedir_html(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    titulo = h1.get_text(strip=True) if h1 else "Sin título"

    time_tag = soup.find("time")
    fecha = time_tag.get_text(strip=True) if time_tag else "Sin fecha"

    body = soup.find(attrs={"itemprop": "articleBody"})
    if body:
        texto = "\n".join(p.get_text(strip=True) for p in body.find_all("p") if p.get_text(strip=True))
        if len(texto) >= 200:
            return titulo, fecha, texto

    main = soup.find("main")
    if main:
        ps = main.find_all("p")
        texto = "\n".join(p.get_text(strip=True) for p in ps if p.get_text(strip=True))
        if len(texto) >= 200:
            return titulo, fecha, texto

    texto_plano = soup.get_text("\n", strip=True)
    if len(texto_plano) > 4000:
        texto_plano = texto_plano[:4000]

    return titulo, fecha, texto_plano

# =====================
# ENLACES DE SECCIÓN
# =====================

def recolectar_enlaces_seccion(periodico, categoria, url_base):
    html = pedir_html(url_base)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    enlaces = []

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if periodico == "okdiario":
            if href.startswith("/"):
                href = "https://okdiario.com" + href
            if not href.startswith("https://okdiario.com/"):
                continue

        if periodico == "elmundo":
            if href.startswith("/"):
                href = "https://www.elmundo.es" + href
            if not href.startswith("https://www.elmundo.es/"):
                continue

        if periodico == "telemadrid":
            if href.startswith("/"):
                href = "https://www.telemadrid.es" + href
            if not href.startswith("https://www.telemadrid.es/"):
                continue

        if href.startswith("http") and href not in enlaces:
            enlaces.append(href)

    return enlaces

# =====================
# SCRAPER
# =====================

def scrapear_categoria(periodico, categoria, url_base, extractor, max_noticias=100):
    print(f"\n[{periodico.upper()}] {categoria}")

    enlaces = recolectar_enlaces_seccion(periodico, categoria, url_base)
    if not enlaces:
        print("  ! No se encontraron enlaces en la sección.")
        return

    guardadas = 0
    revisadas = 0
    saltadas_repetidas = 0

    for url in enlaces:
        if guardadas >= max_noticias:
            break

        revisadas += 1

        if not url_corresponde_categoria(periodico, categoria, url):
            continue

        # ✅ NO REPETIR
        if ya_descargada(BASE_DIR, categoria, periodico, url):
            saltadas_repetidas += 1
            continue

        datos = extractor(url)
        if not datos:
            continue

        titulo, fecha, texto = datos

        if texto is None or len(texto) < 500:
            continue

        guardar_noticia_txt(BASE_DIR, categoria, periodico, url, titulo, fecha, texto)
        guardadas += 1
        print(f"  ✓ {guardadas}")
        pausa()

    print(f"  Revisadas: {revisadas} | Guardadas: {guardadas} | Repetidas saltadas: {saltadas_repetidas}")

def main():
    asegurar_carpetas()

    for cat in CATEGORIAS:
        scrapear_categoria("telemadrid", cat, URLS_TELEMADRID[cat], extraer_telemadrid, 100)
        scrapear_categoria("okdiario", cat, URLS_OKDIARIO[cat], extraer_okdiario, 100)
        scrapear_categoria("elmundo", cat, URLS_ELMUNDO[cat], extraer_elmundo, 100)

if __name__ == "__main__":
    main()