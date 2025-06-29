from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from routers import upload, filter, search, clustering, users, logs

app = FastAPI()

# ⛓️ Подключаем роутеры
app.include_router(upload.router)
app.include_router(filter.router)
app.include_router(search.router)
app.include_router(clustering.router)
app.include_router(users.router)
app.include_router(logs.router)

# 🌐 Подключение статики и шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 🔐 Сессии (если используешь авторизацию через cookie)
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

# 🏠 Главная страница
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 📰 Статья (по ID или имени файла)
@app.get("/article/{article_id}", response_class=HTMLResponse)
async def read_article(request: Request, article_id: int):
    # Можно тут же делать выборку из БД, пока мок:
    return templates.TemplateResponse("article.html", {"request": request, "article": {
        "title": "Пример статьи", "abstract": "Аннотация...", "keywords": "пример, данные",
        "figures_count": 1, "tables_count": 2, "file_name": "example.pdf"
    }, "user_id": 1})

# ⚙️ Панель администратора
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})