from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from database.connection import conn
from psycopg2.extras import RealDictCursor
from typing import Optional

router = APIRouter()


@router.get("/admin/logs")
def get_user_logs(
    username: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        query = """
            SELECT ua.id, u.username, ua.action, ua.action_time
            FROM user_actions ua
            JOIN users u ON ua.user_id = u.id
        """
        conditions = []
        params = []

        if username:
            conditions.append("u.username = %s")
            params.append(username)
        if action:
            conditions.append("ua.action ILIKE %s")
            params.append(f"%{action}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY ua.action_time DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        logs = cur.fetchall()

    return {"logs": logs}


@router.get("/admin/reports/views")
def get_views(start: Optional[str] = Query(None), end: Optional[str] = Query(None)):
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT a.title, v.view_date, v.view_count
                FROM article_views v
                JOIN articles a ON a.id = v.article_id
            """
            params = []
            if start and end:
                query += " WHERE v.view_date BETWEEN %s AND %s"
                params = [start, end]

            query += " ORDER BY v.view_date"
            cur.execute(query, params)
            rows = cur.fetchall()

        reports = [
            {
                "title": row["title"],
                "view_date": row["view_date"],
                "view_count": row["view_count"]
            }
            for row in rows
        ]
        return {"reports": reports}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/admin/reports/downloads")
def get_downloads(start: Optional[str] = Query(None), end: Optional[str] = Query(None)):
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT a.title, d.download_date, d.download_count
                FROM article_downloads d
                JOIN articles a ON a.id = d.article_id
            """
            params = []
            if start and end:
                query += " WHERE d.download_date BETWEEN %s AND %s"
                params = [start, end]

            query += " ORDER BY d.download_date"
            cur.execute(query, params)
            rows = cur.fetchall()

        reports = [
            {
                "title": row["title"],
                "download_date": row["download_date"],
                "download_count": row["download_count"]
            }
            for row in rows
        ]
        return {"reports": reports}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})