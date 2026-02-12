import mysql.connector as sql
from mysql.connector import errorcode
from flask import current_app
import os

DB_NAME = "zioraa"

def get_db():
    try:
        db = sql.connect(
            host="localhost",
            user="root",
            password="root",
            database=DB_NAME,
            charset="utf8"
        )
        return db, db.cursor()

    except sql.Error as e:
        print("DB ERROR:", e)
        return None, None

