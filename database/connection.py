import psycopg2


conn = psycopg2.connect(
    dbname="sbornik_md",
    user="postgres",
    password="Kalimova2003",
    host="localhost",
    port="5432"
)
conn.autocommit = True