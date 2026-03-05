import psycopg2
import os

def conectar_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])
