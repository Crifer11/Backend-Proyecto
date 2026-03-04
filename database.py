import psycopg2

def conectar_db():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="Equipo123",
        host="localhost",
        port="5432"
    )

conexion = conectar_db()
