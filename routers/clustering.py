from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional
import os
import base64
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import plotly.express as px
from database.connection import conn
from services.pdf_tools import extract_text_from_pdf
from services.requirement_checker import check_requirements
from services.vectorizer import model

router = APIRouter()


@router.get("/check_requirements/{article_id}")
def check_article_requirements(article_id: int):
    from psycopg2.extras import RealDictCursor

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM articles WHERE id = %s", (article_id,))
        article = cursor.fetchone()

        cursor.execute("SELECT reference_text FROM references_list WHERE article_id = %s", (article_id,))
        references = cursor.fetchall()
        reference_count = len(references)

        if not article:
            return {"error": "Статья не найдена"}

    file_path = os.path.join("articles", article["file_name"])
    if not os.path.exists(file_path):
        return {"error": f"PDF файл не найден: {file_path}"}

    try:
        full_text = extract_text_from_pdf(file_path)
    except Exception as e:
        return {"error": f"Ошибка чтения PDF: {str(e)}"}

    result = check_requirements(article, full_text, reference_count)
    return result


@router.post("/update_requirements_flags")
def update_all_requirements():
    from psycopg2.extras import RealDictCursor
    updated = 0

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, file_name FROM articles")
        articles = cur.fetchall()

    for article in articles:
        file_path = os.path.join("articles", article["file_name"])
        full_text = extract_text_from_pdf(file_path)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM references_list WHERE article_id = %s", (article["id"],))
            ref_count = cur.fetchone()[0]

        result = check_requirements(article, full_text, ref_count)
        passed = result["score"] >= 85

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE articles SET requirements_passed = %s WHERE id = %s",
                (passed, article["id"])
            )
            updated += 1

    return {"message": f"Обновлено {updated} статей"}


@router.post("/admin/clusterize")
async def clusterize_abstracts(request: Request):
    try:
        form = await request.form()
        num_clusters = int(form.get("num_clusters", 3))
        issue_ids = [int(i) for i in form.getlist("issue_ids")]

        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, title, abstract FROM articles
                WHERE issue_id = ANY(%s) AND abstract IS NOT NULL
            """, (issue_ids,))
            rows = cur.fetchall()

        if not rows:
            return JSONResponse(status_code=400, content={"error": "Нет аннотаций"})

        df = pd.DataFrame(rows)
        embeddings = model.encode(df["abstract"].tolist(), show_progress_bar=False)

        kmeans = KMeans(n_clusters=num_clusters, random_state=42)
        df['cluster'] = kmeans.fit_predict(embeddings)

        with conn.cursor() as cur:
            for i, row in df.iterrows():
                cur.execute("""
                    INSERT INTO annotation_clusters (article_id, cluster_id)
                    VALUES (%s, %s)
                    ON CONFLICT (article_id) DO UPDATE SET cluster_id = EXCLUDED.cluster_id
                """, (row['id'], int(row['cluster'])))

        centroids = kmeans.cluster_centers_
        with conn.cursor() as cur:
            for idx, vec in enumerate(centroids):
                cur.execute("""
                    INSERT INTO cluster_centroids (cluster_id, center_vector)
                    VALUES (%s, %s)
                    ON CONFLICT (cluster_id) DO UPDATE SET center_vector = EXCLUDED.center_vector
                """, (idx, vec.tolist()))

        pca = PCA(n_components=3).fit_transform(embeddings)
        df['x'], df['y'], df['z'] = pca[:, 0], pca[:, 1], pca[:, 2]

        fig = px.scatter_3d(
            df, x='x', y='y', z='z',
            color=df['cluster'].astype(str),
            hover_name=df['title'],
            title="Кластеризация аннотаций",
            width=900, height=700
        )

        html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        encoded_html = base64.b64encode(html.encode("utf-8")).decode("utf-8")
        return {"plot_html": encoded_html, "message": "Кластеризация завершена"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})