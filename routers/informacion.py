from fastapi import APIRouter, HTTPException, Query, Form
from database import conectar_db

router = APIRouter()

@router.get("/informacion")
def obtener_informacion(id: int = Query(...), rol: str = Query(...)):
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        if rol == "Administrador":
            cursor.execute("SELECT id, nombre FROM administrador WHERE id = %s", (id,))
            admin = cursor.fetchone()
        
            # Obtener todas las casetas
            cursor.execute("SELECT id, telefono, ubicación FROM caseta")
            casetas = cursor.fetchall()
        
            casetas_formateadas = []
            for c in casetas:
                casetas_formateadas.append({
                    "id": c[0],
                    "telefono": c[1],
                    "ubicacion": c[2]
                })
        
            # Obtener todos los vigilantes
            cursor.execute("SELECT id, nombre, celular, id_caseta FROM vigilante")
            vigilantes = cursor.fetchall()
        
            vigilantes_formateados = []
            for v in vigilantes:
                vigilantes_formateados.append({
                    "id": v[0],
                    "nombre": v[1],
                    "celular": v[2],
                    "id_caseta": v[3]
                })
        
            return {
                "id": admin[0],
                "nombre": admin[1],
                "casetas": casetas_formateadas,
                "vigilantes": vigilantes_formateados
            }

        elif rol == "Vigilante":
            cursor.execute("SELECT id, nombre, celular, id_caseta FROM vigilante WHERE id = %s", (id,))
            vigilante = cursor.fetchone()
        
            respuesta = {
                "id": vigilante[0],
                "nombre": vigilante[1],
                "celular": vigilante[2],
            }
        
            id_caseta = vigilante[3]
            if id_caseta:
                cursor.execute("SELECT id, telefono, ubicación FROM caseta WHERE id = %s", (id_caseta,))
                caseta = cursor.fetchone()
                if caseta:
                    respuesta["caseta"] = {
                        "id": caseta[0],
                        "telefono": caseta[1],
                        "ubicacion": caseta[2]
                    }
            else:
                respuesta["caseta"] = None
            
            # Obtener todas las casetas
            cursor.execute("SELECT id, telefono, ubicación FROM caseta")
            casetas = cursor.fetchall()
            
            respuesta["casetas"] = [
                {
                    "id": c[0],
                    "telefono": c[1],
                    "ubicacion": c[2]
                }
                for c in casetas
            ]
            
            # Obtener todos los vigilantes
            cursor.execute("SELECT id, nombre, celular, id_caseta FROM vigilante")
            vigilantes = cursor.fetchall()
            
            respuesta["vigilantes"] = [
                {
                    "id": v[0],
                    "nombre": v[1],
                    "celular": v[2],
                    "id_caseta": v[3]
                }
                for v in vigilantes
            ]
                
            return respuesta


        
        elif rol == "Autorizado":
            # Paso 1: Info del autorizado
            cursor.execute("SELECT id, nombre, celular, foto, domicilio FROM residente WHERE id = %s", (id,))
            autorizado = cursor.fetchone()
        
            if not autorizado:
                raise HTTPException(status_code=404, detail="Autorizado no encontrado")
        
            info_autorizado = {
                "id": autorizado[0],
                "nombre": autorizado[1],
                "celular": autorizado[2],
                "foto": autorizado[3],
                "domicilio": autorizado[4],
                "autos_autorizados": []
            } 
        
            # Paso 2: Obtener IDs de autos que puede sacar
            cursor.execute("SELECT id_tag FROM residente_auto WHERE id_residente = %s", (id,))
            autos_autorizados = cursor.fetchall()
        
            for (id_auto,) in autos_autorizados:
                # Paso 3: Obtener info del auto
                cursor.execute("SELECT id, placa, modelo, id_titular FROM autos WHERE id = %s", (id_auto,))
                auto_info = cursor.fetchone()
        
                if auto_info:
                    id_auto, placa, modelo, id_duenio = auto_info
        
                    # Paso 4: Obtener nombre del dueño
                    cursor.execute("SELECT nombre FROM residente WHERE id = %s", (id_duenio,))
                    duenio = cursor.fetchone()
        
                    nombre_duenio = duenio[0] if duenio else "Desconocido"
        
                    info_autorizado["autos_autorizados"].append({
                        "id": id_auto,
                        "placa": placa,
                        "modelo": modelo,
                        "propietario": nombre_duenio
                    })
        
            cursor.close()
            conn.close()
            return info_autorizado
        
        
        elif rol == "Residente":
            # Obtener info del residente
            cursor.execute("""
                SELECT id, nombre, celular, domicilio, foto
                FROM residente
                WHERE id = %s
            """, (id,))
            info = cursor.fetchone()
        
            # Obtener autos del residente
            cursor.execute("""
                SELECT id, placa, modelo
                FROM autos
                WHERE id_titular = %s
            """, (id,))
            autos = cursor.fetchall()
        
            # Sacar IDs de autos
            ids_autos = [auto[0] for auto in autos]
        
            autorizados_ids = set()
        
            if ids_autos:
                # Buscar IDs de autorizados en residente_auto
                formato_ids_autos = ','.join(['%s'] * len(ids_autos))
                query_autorizados = f"""
                    SELECT DISTINCT id_residente
                    FROM residente_auto
                    WHERE id_tag IN ({formato_ids_autos})
                """
                cursor.execute(query_autorizados, ids_autos)
                ids = cursor.fetchall()
        
                for (id_autorizado,) in ids:
                    if id_autorizado != int(id):  # Excluir al residente
                        autorizados_ids.add(id_autorizado)
        
            autorizados_formateados = []
        
            if autorizados_ids:
                # Buscar información de autorizados
                formato_autorizados = ','.join(['%s'] * len(autorizados_ids))
                query_info = f"""
                    SELECT id, nombre, celular, foto, domicilio
                    FROM residente
                    WHERE id IN ({formato_autorizados})
                """
                cursor.execute(query_info, list(autorizados_ids))
                autorizados = cursor.fetchall()
        
                for a in autorizados:
                    id_autorizado = a[0]
        
                    # Crear el formato para buscar solo en los autos de este residente
                    formato_autos = ','.join(['%s'] * len(ids_autos))
                    query_autos_autorizados = f"""
                        SELECT autos.id, autos.placa, autos.modelo
                        FROM residente_auto
                        JOIN autos ON residente_auto.id_tag = autos.id
                        WHERE residente_auto.id_residente = %s
                        AND residente_auto.id_tag IN ({formato_autos})
                    """
                    cursor.execute(query_autos_autorizados, [id_autorizado, *ids_autos])
                    autos_autorizados = cursor.fetchall()
        
                    autos_info = []
                    for auto in autos_autorizados:
                        autos_info.append({
                            "id": auto[0],
                            "placa": auto[1],
                            "modelo": auto[2]
                        })
        
                    for a in autorizados:
                        id_autorizado, nombre, celular, foto, domicilio = a
                        autorizados_formateados.append({
                            "id": id_autorizado,
                            "nombre": nombre,
                            "celular": celular,
                            "foto": foto,
                            "domicilio": domicilio,
                            "autos": autos_info
                        })

        
            autos_formateados = []
            for a in autos:
                autos_formateados.append({
                    "id": a[0],
                    "placa": a[1],
                    "modelo": a[2]
                })
        
            # Autos autorizados de otros residentes
            cursor.execute("""
                SELECT autos.id, autos.placa, autos.modelo, r.nombre AS propietario
                FROM residente_auto
                JOIN autos ON residente_auto.id_tag = autos.id
                JOIN residente r ON autos.id_titular = r.id
                WHERE residente_auto.id_residente = %s AND autos.id_titular != %s
            """, (id, id))
            
            autos_autorizados_otros = cursor.fetchall()
            
            autos_autorizados_formateados = []
            for auto in autos_autorizados_otros:
                autos_autorizados_formateados.append({
                    "id": auto[0],
                    "placa": auto[1],
                    "modelo": auto[2],
                    "propietario": auto[3]  # nombre del dueño real
                })
            
            return {
                "id": info[0],
                "nombre": info[1],
                "celular": info[2],
                "domicilio": info[3],
                "foto": info[4],
                "autos": autos_formateados,
                "autorizados": autorizados_formateados,
                "autos_autorizados": autos_autorizados_formateados
            }

        elif rol == "Auto":
            cursor.execute("""
                SELECT id, placa, modelo, id_titular
                FROM autos
                WHERE id = %s
            """, (id,))
            auto = cursor.fetchone()
            if auto:
                cursor.execute("SELECT nombre FROM residente WHERE id = %s", (auto[3],))
                titular = cursor.fetchone()
                nombre_titular = titular[0] if titular else "Desconocido"
        
                return {
                    "id": auto[0],
                    "placa": auto[1],
                    "modelo": auto[2],
                    "titular": nombre_titular
                }
        
        elif rol == "Caseta":
            cursor.execute("SELECT id, telefono, ubicación FROM caseta WHERE id = %s", (id,))
            caseta = cursor.fetchone()
        
            if not caseta:
                raise HTTPException(status_code=404, detail="Caseta no encontrada")
        
            # Obtener todos los vigilantes asignados a esa caseta
            cursor.execute("SELECT id, nombre FROM vigilante WHERE id_caseta = %s", (id,))
            vigilantes = cursor.fetchall()
        
            respuesta = {
                "id": caseta[0],
                "telefono": caseta[1],
                "ubicacion": caseta[2],
                "vigilantes": []
            }
        
            for v in vigilantes:
                respuesta["vigilantes"].append({
                    "id": v[0],
                    "nombre": v[1]
                })
        
            return respuesta

        else:
            raise HTTPException(status_code=400, detail="Rol no válido")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al obtener información: {e}")
    finally:
        cursor.close()
        conn.close()


@router.post("/autorizar_auto")
def autorizar_auto(id_auto: int = Form(...), id_residente: int = Form(...)):
    conn = conectar_db()
    cursor = conn.cursor()

    # Verificar que la persona exista en la tabla residente
    cursor.execute("SELECT 1 FROM residente WHERE id = %s", (id_residente,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="❌ El ID ingresado no pertenece a un residente o autorizado válido.")

    # Verificar que no esté ya autorizado
    cursor.execute("""
        SELECT 1 FROM residente_auto WHERE id_tag = %s AND id_residente = %s
    """, (id_auto, id_residente))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="❌ Esta persona ya está autorizada para usar el auto.")

    # Autorizar
    cursor.execute("""
        INSERT INTO residente_auto (id_tag, id_residente)
        VALUES (%s, %s)
    """, (id_auto, id_residente))
    conn.commit()

    return {"mensaje": "✅ Persona autorizada correctamente para usar el auto."}


@router.post("/desautorizar_auto")
def desautorizar_auto(id_auto: int = Form(...), id_residente: int = Form(...)):
    conn = conectar_db()
    cursor = conn.cursor()

    # Verificar si está autorizado
    cursor.execute("""
        SELECT 1 FROM residente_auto WHERE id_tag = %s AND id_residente = %s
    """, (id_auto, id_residente))
    if not cursor.fetchone():
        raise HTTPException(status_code=400, detail="❌ Esta persona no está autorizada para este auto.")

    # Eliminar permiso
    cursor.execute("""
        DELETE FROM residente_auto WHERE id_tag = %s AND id_residente = %s
    """, (id_auto, id_residente))
    conn.commit()

    return {"mensaje": "✅ Persona desautorizada correctamente."}