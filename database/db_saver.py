from database.connection import conn
from services.requirement_checker import check_requirements



def save_to_db(data, filename, issue_id):
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM articles WHERE title = %s AND issue_id = %s", (data['title'], issue_id))
        if cursor.fetchone():
            print(f" Статья '{data['title']}' уже существует в выпуске ID {issue_id}, пропускаем.")
            return

        # Университет
        cursor.execute("SELECT id FROM universities WHERE name = %s", (data['university'],))
        uni = cursor.fetchone()
        if uni:
            university_id = uni[0]
        else:
            cursor.execute("INSERT INTO universities (name) VALUES (%s) RETURNING id", (data['university'],))
            university_id = cursor.fetchone()[0]

        # Авторы
        author_names = [a.strip() for a in data['authors'].split(',') if a.strip()]
        author_ids = []
        for author_name in author_names:
            cursor.execute("SELECT id FROM authors WHERE name = %s", (author_name,))
            author = cursor.fetchone()
            if author:
                author_ids.append(author[0])
            else:
                cursor.execute("INSERT INTO authors (name) VALUES (%s) RETURNING id", (author_name,))
                author_ids.append(cursor.fetchone()[0])



        # Статья
        cursor.execute(

            """
            INSERT INTO articles (
                title, abstract, keywords, tables_count, figures_count,
                file_name, university_id, issue_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data['title'],
                data['abstract'],
                data['keywords'] if data['keywords'] else [],
                data['tables'],
                data['figures'],
                filename,
                university_id,
                issue_id
            )
        )
        article_id = cursor.fetchone()[0]

        for author_id in author_ids:
            cursor.execute(
                "INSERT INTO article_authors (article_id, author_id) VALUES (%s, %s)",
                (article_id, author_id)
            )

        for ref in data['references']:
            cursor.execute(
                "INSERT INTO references_list (article_id, reference_text) VALUES (%s, %s)",
                (article_id, ref)
            )

        print(f" Статья '{data['title']}' сохранена в базу данных (выпуск ID {issue_id}).")
