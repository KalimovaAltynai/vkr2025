from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import bcrypt
from database.connection import conn
from psycopg2.extras import RealDictCursor
from fastapi.encoders import jsonable_encoder
from services.logger import log_user_action

router = APIRouter()


@router.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user:
            raise HTTPException(status_code=400, detail="Пользователь уже существует")

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # добавлено поле role со значением "user"
        cursor.execute(
            "INSERT INTO users (username, password, role, created_at, last_login) "
            "VALUES (%s, %s, %s, NOW(), NOW()) RETURNING id",
            (username, hashed_password, "user")
        )
        new_user_id = cursor.fetchone()['id']

    return {"message": "Регистрация успешна", "user_id": new_user_id}



@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

    if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user["id"],))
        log_user_action(user["id"], "Вход в систему")
        return {
            "message": "Login successful",
            "username": user["username"],
            "user_id": user["id"],
            "role": user["role"]
        }

    raise HTTPException(status_code=401, detail="Неверный логин или пароль")


@router.get("/admin/users")
def list_users():
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, username, role, created_at, last_login FROM users ORDER BY id")
        users = cur.fetchall()

    for u in users:
        u["created_at"] = u["created_at"].isoformat()
        u["last_login"] = u["last_login"].isoformat()
    return JSONResponse(jsonable_encoder({"users": users}))


@router.post("/admin/users")
def create_user(username: str = Form(...), password: str = Form(...), role: str = Form("user")):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, password, role, created_at, last_login) "
            "VALUES (%s, %s, %s, NOW(), NOW())",
            (username, hashed, role)
        )
    return JSONResponse({"message": "User created"})


@router.put("/admin/users/{user_id}")
def update_user(
    user_id: int,
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    role: Optional[str] = Form(None)
):
    if not any([username, password, role]):
        raise HTTPException(400, "Nothing to update")

    with conn.cursor() as cur:
        if username:
            cur.execute("UPDATE users SET username=%s WHERE id=%s", (username, user_id))
        if password:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cur.execute("UPDATE users SET password=%s WHERE id=%s", (hashed, user_id))
        if role:
            cur.execute("UPDATE users SET role=%s WHERE id=%s", (role, user_id))

    return JSONResponse({"message": "User updated"})


@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    return JSONResponse({"message": "User deleted"})