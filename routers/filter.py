from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from database.connection import conn
from services.logger import log_user_action
from psycopg2.extras import RealDictCursor
from typing import Optional, List
import os

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/articles")
def get_articles(
    user_id: Optional[int] = Query(None),
    issue_ids: Optional[List[int]] = Query(None),
    passed: Optional[bool] = Query(None)
):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        final_issue_ids = issue_ids or []

        if not issue_ids and user_id:
            cursor.execute("SELECT issue_id FROM user_issues WHERE user_id = %s", (user_id,))
            final_issue_ids = [row['issue_id'] for row in cursor.fetchall()]

        base_query = """
            SELECT id, title, abstract, keywords, tables_count, figures_count, file_name, requirements_passed
            FROM articles
        """
        conditions = []
        params = []

        if final_issue_ids:
            conditions.append("issue_id = ANY(%s)")
            params.append(final_issue_ids)
        if passed is not None:
            conditions.append("requirements_passed = %s")
            params.append(passed)

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        cursor.execute(base_query, tuple(params))
        articles = cursor.fetchall()

    if not articles:
        return {"articles": [], "filters": {}}

    for article in articles:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.name
                FROM authors a
                JOIN article_authors aa ON a.id = aa.author_id
                WHERE aa.article_id = %s
            """, (article['id'],))
            article['authors'] = [row[0] for row in cur.fetchall()]

    keywords_counts = [len(a["keywords"]) for a in articles]
    figures_counts = [a["figures_count"] for a in articles]
    tables_counts = [a["tables_count"] for a in articles]

    filters = {
        "keywords": {"min": 0, "max": max(keywords_counts) if keywords_counts else 0},
        "figures": {"min": 0, "max": max(figures_counts) if figures_counts else 0},
        "tables": {"min": 0, "max": max(tables_counts) if tables_counts else 0},
    }

    return {"articles": articles, "filters": filters}


@router.get("/article/{article_id}", response_class=HTMLResponse)
def view_article(request: Request, article_id: int, user_id: Optional[int] = Query(None)):
    from datetime import date
    today = date.today()

    if user_id:
        log_user_action(user_id, f"Просмотр статьи ID {article_id}")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO article_views(article_id, view_date, view_count)
            VALUES (%s, %s, 1)
            ON CONFLICT (article_id, view_date)
            DO UPDATE SET view_count = article_views.view_count + 1
            """,
            (article_id, today)
        )

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM articles WHERE id=%s", (article_id,))
        art = cur.fetchone()

    if not art:
        raise HTTPException(404, "Статья не найдена")

    return templates.TemplateResponse("article.html", {
        "request": request,
        "article": art,
        "user_id": user_id
    })


@router.get("/authors")
def get_authors():
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT a.name
            FROM authors a
            JOIN article_authors aa ON a.id = aa.author_id
        """)
        authors = [row[0] for row in cursor.fetchall()]
    return authors


@router.get("/download/{file_name}", response_class=FileResponse)
def download_file(file_name: str, user_id: Optional[int] = Query(None)):
    from datetime import date

    with conn.cursor() as cur:
        cur.execute("SELECT id FROM articles WHERE file_name = %s", (file_name,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Статья не найдена для данного файла")

    article_id = row[0]

    if user_id:
        log_user_action(user_id, f"Скачал статью ID {article_id}")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO article_downloads(article_id, download_date, download_count)
            VALUES (%s, %s, 1)
            ON CONFLICT (article_id, download_date)
            DO UPDATE SET download_count = article_downloads.download_count + 1
            """,
            (article_id, date.today())
        )

    file_path = os.path.join("articles", file_name)
    if not os.path.exists(file_path):
        raise HTTPException(404, "Файл не найден на сервере")

    return FileResponse(path=file_path, filename=file_name, media_type="application/pdf")