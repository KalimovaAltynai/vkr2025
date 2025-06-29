from fastapi import APIRouter, Body, HTTPException
from typing import List
from database.connection import conn
from psycopg2.extras import RealDictCursor
from services.vectorizer import combined_similarity, model
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

router = APIRouter()


@router.post("/semantic_search")
async def semantic_search(data: dict = Body(...)):
    query = data.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Пустой запрос")

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT id, title, abstract, keywords, tables_count, figures_count, file_name
            FROM articles
        """)
        articles = cursor.fetchall()

    for article in articles:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.name
                FROM authors a
                JOIN article_authors aa ON a.id = aa.author_id
                WHERE aa.article_id = %s
            """, (article['id'],))
            authors = [row[0] for row in cur.fetchall()]
            article['authors'] = authors

    threshold = 0.5
    results = []

    for article in articles:
        score = combined_similarity(query, article)
        if score >= threshold:
            results.append((score, article))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results]


@router.post("/cluster_search")
async def cluster_search(data: dict = Body(...)):
    query = data.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Пустой запрос")

    query_vec = model.encode([query])[0]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT cluster_id, center_vector FROM cluster_centroids")
        rows = cur.fetchall()
        cluster_centers = {r["cluster_id"]: np.array(r["center_vector"]) for r in rows}

    if not cluster_centers:
        raise HTTPException(status_code=400, detail="Центры кластеров не найдены")

    best_cluster = max(
        cluster_centers.items(),
        key=lambda kv: cosine_similarity([query_vec], [kv[1]])[0][0]
    )[0]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT a.id, a.title, a.abstract, a.keywords, a.tables_count, a.figures_count,
                   a.file_name, ac.cluster_id
            FROM articles a
            JOIN annotation_clusters ac ON ac.article_id = a.id
            WHERE ac.cluster_id = %s AND a.abstract IS NOT NULL
        """, (best_cluster,))
        rows = cur.fetchall()

    if not rows:
        return []

    df = pd.DataFrame(rows)
    embeddings = model.encode(df['abstract'].tolist(), show_progress_bar=False)
    similarities = cosine_similarity([query_vec], embeddings)[0]
    df['similarity'] = similarities

    df = df.sort_values(by='similarity', ascending=False).head(20)

    result = []
    for _, row in df.iterrows():
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.name FROM authors a
                JOIN article_authors aa ON aa.author_id = a.id
                WHERE aa.article_id = %s
            """, (row['id'],))
            authors = [r[0] for r in cur.fetchall()]

        result.append({
            "id": row["id"],
            "title": row["title"],
            "abstract": row["abstract"],
            "keywords": row["keywords"],
            "tables_count": row["tables_count"],
            "figures_count": row["figures_count"],
            "file_name": row["file_name"],
            "authors": authors
        })

    return result