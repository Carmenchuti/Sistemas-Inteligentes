# ============================================================
# SISTEMA DE RECOMENDACIÓN DE NOTICIAS
# Bag of Words + TF-IDF + Similitud del Coseno
# ============================================================

import os
import string
import pandas as pd
import nltk

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ============================================================
# DESCARGA DE RECURSOS NLTK (SOLO PRIMERA VEZ)
# ============================================================

nltk.download("punkt")
nltk.download("stopwords")
nltk.download("wordnet")

# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = "Sistemas-Inteligentes/dataset"
STOP_WORDS = set(stopwords.words("spanish"))
LEMMATIZER = WordNetLemmatizer()

# ============================================================
# PREPROCESAMIENTO NLP
# ============================================================

def preprocess_text(text):
    """
    - Minúsculas
    - Tokenización
    - Eliminación de stopwords
    - Eliminación de puntuación
    - Lematización
    """
    text = text.lower()
    tokens = nltk.word_tokenize(text)

    tokens = [
        LEMMATIZER.lemmatize(token)
        for token in tokens
        if token.isalpha()
        and token not in STOP_WORDS
        and token not in string.punctuation
    ]

    return " ".join(tokens)

# ============================================================
# CARGA DEL DATASET (COMPATIBLE CON TU SCRAPER)
# ============================================================

def cargar_noticias(base_dir=BASE_DIR):
    noticias = []

    for categoria in os.listdir(base_dir):
        ruta_cat = os.path.join(base_dir, categoria)
        if not os.path.isdir(ruta_cat):
            continue

        for periodico in os.listdir(ruta_cat):
            ruta_per = os.path.join(ruta_cat, periodico)
            if not os.path.isdir(ruta_per):
                continue

            for archivo in os.listdir(ruta_per):
                if not archivo.endswith(".txt"):
                    continue

                ruta = os.path.join(ruta_per, archivo)

                with open(ruta, "r", encoding="utf-8") as f:
                    lineas = f.read().splitlines()

                data = {}
                texto = []
                leyendo_texto = False

                for linea in lineas:
                    if linea.startswith("ID:"):
                        data["id"] = linea.replace("ID:", "").strip()
                    elif linea.startswith("TITULO:"):
                        data["titulo"] = linea.replace("TITULO:", "").strip()
                    elif linea.startswith("FECHA:"):
                        data["fecha"] = linea.replace("FECHA:", "").strip()
                    elif linea.startswith("PERIODICO:"):
                        data["periodico"] = linea.replace("PERIODICO:", "").strip()
                    elif linea.startswith("CATEGORIA:"):
                        data["categoria"] = linea.replace("CATEGORIA:", "").strip()
                    elif linea.startswith("URL:"):
                        data["url"] = linea.replace("URL:", "").strip()
                    elif linea.startswith("TEXTO:"):
                        leyendo_texto = True
                    elif leyendo_texto:
                        texto.append(linea)

                data["texto"] = " ".join(texto)
                data["texto_completo"] = data["titulo"] + " " + data["texto"]

                noticias.append(data)

    return pd.DataFrame(noticias)

# ============================================================
# TF-IDF (MODELO ESPACIO VECTORIAL) - OE3.1
# ============================================================

def construir_tfidf(corpus):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)
    return tfidf_matrix, vectorizer

# ============================================================
# RECOMENDACIÓN POR QUERY - OE2
# ============================================================

def recomendar_por_query(query, tfidf_matrix, vectorizer, df, top_n=5):
    query_proc = preprocess_text(query)
    query_vec = vectorizer.transform([query_proc])

    similitudes = cosine_similarity(tfidf_matrix, query_vec).flatten()
    indices = similitudes.argsort()[::-1][:top_n]

    return df.iloc[indices]

# ============================================================
# RECOMENDACIÓN POR NOTICIA - OE2
# ============================================================

def recomendar_por_noticia(indice_noticia, tfidf_matrix, df, top_n=5):
    similitudes = cosine_similarity(
        tfidf_matrix[indice_noticia],
        tfidf_matrix
    ).flatten()

    similitudes[indice_noticia] = -1
    indices = similitudes.argsort()[::-1][:top_n]

    return df.iloc[indices]

# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    print("📥 Cargando noticias...")
    df = cargar_noticias()

    print(f"📰 Total de noticias: {len(df)}")

    print("🧠 Preprocesando textos...")
    df["texto_procesado"] = df["texto_completo"].apply(preprocess_text)

    print("📐 Construyendo matriz TF-IDF...")
    tfidf_matrix, vectorizer = construir_tfidf(df["texto_procesado"])

    # =======================
    # PRUEBA 1: QUERY USUARIO
    # =======================
    print("\n🔎 Recomendación por query:")
    resultados_query = recomendar_por_query(
        "fútbol real madrid champions",
        tfidf_matrix,
        vectorizer,
        df,
        top_n=5
    )

    print(resultados_query[["titulo", "periodico", "categoria"]])

    # =======================
    # PRUEBA 2: NOTICIA SIMILAR
    # =======================
    print("\n📰 Recomendación por noticia similar:")
    resultados_noticia = recomendar_por_noticia(
        indice_noticia=0,
        tfidf_matrix=tfidf_matrix,
        df=df,
        top_n=5
    )

    print(resultados_noticia[["titulo", "periodico", "categoria"]])


if __name__ == "__main__":
    main()