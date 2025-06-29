from database.connection import conn
import re
import fitz
import os

def extract_text_from_pdf(file_name: str) -> str:
    pdf_path = os.path.join("articles", file_name)  # путь к PDF
    if not os.path.exists(pdf_path):
        return ""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def check_requirements(article: dict, text: str) -> dict:
    abstract = str(article.get("abstract") or "")
    keywords = article.get("keywords") or []

    annotation_words = len(re.findall(r'\w+', abstract))
    keyword_count = len(keywords)

    structure_sections = {
        "введение": bool(re.search(r"\bвведение\b", text, re.IGNORECASE)),
        "проблема": bool(re.search(r"\bпроблема\b", text, re.IGNORECASE)),
        "методы": bool(re.search(r"\bматериалы и методы\b", text, re.IGNORECASE)),
        "результаты": bool(re.search(r"\bрезультаты\b", text, re.IGNORECASE)),
        "заключение": bool(re.search(r"\bзаключение\b", text, re.IGNORECASE)),
    }

    return {
        "annotation_words": annotation_words,
        "keyword_count": keyword_count,
        "structure_check": structure_sections
    }


def recheck_all_articles():
    with conn.cursor() as cur:
        cur.execute("SELECT id, abstract, keywords, file_name FROM articles")
        rows = cur.fetchall()

        for id, abstract, keywords, file_name in rows:
            full_text = extract_text_from_pdf(file_name)
            article = {"abstract": abstract, "keywords": keywords}
            result = check_requirements(article, full_text)

            passed = (
                result["annotation_words"] >= 50 and
                result["keyword_count"] >= 4 and
                all(result["structure_check"].get(section, False) for section in [
                    "введение", "проблема", "методы", "результаты", "заключение"
                ])
            )

            cur.execute("UPDATE articles SET requirements_passed = %s WHERE id = %s", (passed, id))

    conn.commit()
    print(" Проверка завершена, поле requirements_passed обновлено.")