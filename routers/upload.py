from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import os
import shutil
from database.connection import conn
from services.pdf_processor import extract_toc_from_pdf, process_new_issue
from services.logger import log_user_action

router = APIRouter()

@router.post("/upload_issue")
async def upload_issue(title: str = Form(...), year: int = Form(...), file: UploadFile = File(...)):
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    save_path = os.path.join(uploads_dir, file.filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM issues WHERE title = %s AND year = %s", (title, year))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Выпуск с таким названием и годом уже существует.")

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO issues (title, year, file_name) VALUES (%s, %s, %s) RETURNING id",
            (title, year, file.filename)
        )
        issue_id = cur.fetchone()[0]

    toc_path = save_path.replace(".pdf", "_toc.txt")
    toc_extracted = extract_toc_from_pdf(save_path, toc_path)

    if not toc_extracted:
        return {"error": "Не удалось извлечь оглавление из PDF."}

    try:
        process_new_issue(save_path, toc_path, issue_id)
    except Exception as e:
        return {"error": f"Ошибка при обработке сборника: {str(e)}"}

    return {"message": "Сборник загружен, статьи распарсены и сохранены", "issue_id": issue_id}


@router.get("/issues")
def get_issues():
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, title, year FROM issues")
        rows = cursor.fetchall()
        issues = [{"id": row[0], "title": row[1], "year": row[2]} for row in rows]
        return issues


@router.post("/select_issues")
async def select_issues(user_id: int = Form(...), issue_ids: List[int] = Form(...)):
    with conn.cursor() as cursor:
        for issue_id in issue_ids:
            cursor.execute("""
                INSERT INTO user_issues (user_id, issue_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (user_id, issue_id))

    log_user_action(user_id, f"Выбрал выпуски: {', '.join(map(str, issue_ids))}")
    return {"message": "Выпуски успешно выбраны"}