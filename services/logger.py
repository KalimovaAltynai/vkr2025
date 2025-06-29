from database.connection import conn

def log_user_action(user_id: int, action: str):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO user_actions (user_id, action)
            VALUES (%s, %s)
        """, (user_id, action))