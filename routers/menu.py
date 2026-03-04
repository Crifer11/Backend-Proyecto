from fastapi import APIRouter
from database import conectar_db

router = APIRouter(prefix="/menu", tags=["Menu"])

@router.get("/residente/reportes/{id_residente}")
def resumen_reportes_residente(id_residente: int):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*) AS total,
            MAX(tiempo) AS ultimo
        FROM reporte
        WHERE id_residente = %s
    """, (id_residente,))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return {
        "total_reportes": row[0],
        "ultimo_reporte": row[1]
    }

@router.get("/residente/autos/{id_residente}")
def resumen_autos_residente(id_residente: int):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(DISTINCT a.id) AS autos,
               COUNT(ra.id_residente) AS autorizados
        FROM autos a
        LEFT JOIN residente_auto ra ON ra.id_tag = a.id
        WHERE a.id_titular = %s
    """, (id_residente,))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return {
        "autos": row[0],
        "autorizados": row[1]
    }

@router.get("/autorizado/autos/{id_residente}")
def autos_autorizados(id_residente: int):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.id, a.placa
        FROM residente_auto ra
        JOIN autos a ON a.id = ra.id_tag
        WHERE ra.id_residente = %s
    """, (id_residente,))

    autos = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        {"id": a[0], "placa": a[1]}
        for a in autos
    ]

@router.get("/reportes/resumen")
def resumen_reportes_global():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE tiempo >= NOW() - INTERVAL '1 day') AS hoy,
            COUNT(*) FILTER (WHERE tiempo >= NOW() - INTERVAL '7 days') AS semana,
            COUNT(*) FILTER (WHERE tiempo >= NOW() - INTERVAL '1 month') AS mes
        FROM reporte
    """)

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return {
        "hoy": row[0],
        "semana": row[1],
        "mes": row[2]
    }

@router.get("/casetas")
def lista_casetas():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, telefono, ubicación
        FROM caseta
        ORDER BY id
    """)

    casetas = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        {
            "id": c[0],
            "telefono": c[1],
            "ubicacion": c[2]
        }
        for c in casetas
    ]

@router.get("/admin/ultimo-reporte")
def ultimo_reporte():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tiempo, motivo, vigilante, caseta
        FROM reporte
        ORDER BY tiempo DESC
        LIMIT 1
    """)

    r = cursor.fetchone()
    cursor.close()
    conn.close()

    if not r:
        return None

    return {
        "tiempo": r[0],
        "motivo": r[1],
        "vigilante": r[2],
        "caseta": r[3]
    }