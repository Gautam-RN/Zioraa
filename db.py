import psycopg2
import os

def get_db():
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        return conn, conn.cursor()
    except:
        return None,None



