from fastapi import APIRouter, HTTPException, Query, Form, File, UploadFile
from database import conectar_db
import os
from PIL import Image
import io

router = APIRouter()

@router.get("/buscar")
def buscar(tipo: str = Query(...), query: str = Query("")):
    """
    Buscar coincidencias por tipo (residente, autorizado, auto, vigilante o caseta).
    """
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        # Mapear qué tabla y qué campos buscar según el tipo
        if tipo == "residente" or tipo == "autorizado":
            tabla = "residente"
            campo_busqueda = "nombre"
        elif tipo == "auto":
            tabla = "autos"
            campo_busqueda = "placa"
        elif tipo == "vigilante":
            tabla = "vigilante"
            campo_busqueda = "nombre"
        elif tipo == "caseta":
            tabla = "caseta"
            campo_busqueda = "ubicación"
        else:
            raise HTTPException(status_code=400, detail="Tipo no válido.")

        # Detectar si la query es número o texto
        if query.isdigit():
            # Buscar por ID exacto
            if tipo in ["residente", "autorizado"]:
                cursor.execute(
                    f"SELECT id, {campo_busqueda} FROM {tabla} WHERE id = %s AND rol = %s",
                    (int(query), tipo.capitalize())
                )
            else:
                cursor.execute(
                    f"SELECT id, {campo_busqueda} FROM {tabla} WHERE id = %s",
                    (int(query),)
                )
        else:
            # Buscar por coincidencia de texto
            if tipo in ["residente", "autorizado"]:
                cursor.execute(
                    f"SELECT id, {campo_busqueda} FROM {tabla} WHERE {campo_busqueda} ILIKE %s AND rol = %s",
                    (f"%{query}%", tipo.capitalize())
                )
            else:
                cursor.execute(
                    f"SELECT id, {campo_busqueda} FROM {tabla} WHERE {campo_busqueda} ILIKE %s",
                    (f"%{query}%",)
                )

        resultados = cursor.fetchall()
        conn.close()

        # Formatear la respuesta
        coincidencias = [{"id": r[0], "nombre": r[1]} for r in resultados]

        return {"coincidencias": coincidencias}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al buscar: {e}")
        

@router.post("/caseta/guardar")
def guardar_caseta(
    ubicacion: str = Form(...),
    telefono: str = Form(...),
    id_vigilante: int = Form(None),
    id_caseta: int = Form(None)  # Este solo se manda en edición
):
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        if id_caseta:
            # 🛠️ Modo edición
            cursor.execute("""
                UPDATE caseta
                SET ubicación = %s, telefono = %s
                WHERE id = %s
            """, (ubicacion, telefono, id_caseta))

            if id_vigilante:
                cursor.execute("""
                    UPDATE vigilante
                    SET id_caseta = %s
                    WHERE id = %s
                """, (id_caseta, id_vigilante))

            mensaje = "✅ Caseta actualizada correctamente"
        else:
            # ✨ Modo alta
            cursor.execute("""
                INSERT INTO caseta (ubicación, telefono)
                VALUES (%s, %s)
                RETURNING id
            """, (ubicacion, telefono))
            id_caseta = cursor.fetchone()[0]

            if id_vigilante:
                cursor.execute("""
                    UPDATE vigilante
                    SET id_caseta = %s
                    WHERE id = %s
                """, (id_caseta, id_vigilante))

            mensaje = "✅ Caseta creada correctamente"

        conn.commit()
        cursor.close()
        conn.close()

        return {"mensaje": mensaje, "id_caseta": id_caseta}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al guardar la caseta: {e}")

        

# Rutas relativas desde el punto de vista del backend
CARPETA_FOTOS = os.path.join("static", "perfiles")
        
@router.post("/residente/guardar")
def guardar_residente(
    nombre: str = Form(...),
    celular: str = Form(...),
    domicilio: str = Form(...),
    rol: str = Form(...),  # "Residente" o "Autorizado"
    contraseña: str = Form(None),
    id_residente: int = Form(None),
    token: str = Form(None),
    foto: UploadFile = File(None)
):
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        nombre_archivo = None

        if id_residente:
            # Si estamos en edición y se manda una nueva foto
            if foto:
                nombre_archivo = f"{id_residente}_perfil.jpg"
                ruta_guardado = os.path.join(CARPETA_FOTOS, nombre_archivo)
                guardar_imagen_jpg(foto, ruta_guardado)


            cursor.execute("""
                UPDATE residente
                SET nombre = %s, celular = %s, domicilio = %s, foto = COALESCE(%s, foto)
                WHERE id = %s
            """, (nombre, celular, domicilio, nombre_archivo, id_residente))

            mensaje = "✅ Información actualizada correctamente"

        else:
            cursor.execute("""
                INSERT INTO residente (nombre, celular, domicilio, foto, rol)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (nombre, celular, domicilio, "", rol))
            nuevo_id = cursor.fetchone()[0]

            # Guardar la imagen si se envió
            if foto:
                nombre_archivo = f"{nuevo_id}_perfil.jpg"
                ruta_guardado = os.path.join(CARPETA_FOTOS, nombre_archivo)
                guardar_imagen_jpg(foto, ruta_guardado)


                # Actualizar el campo `foto` con el nombre del archivo
                cursor.execute("UPDATE residente SET foto = %s WHERE id = %s", (nombre_archivo, nuevo_id))

            if not contraseña:
                raise HTTPException(status_code=400, detail="Se requiere contraseña")

            cursor.execute("""
                INSERT INTO login (id, contraseña, rol)
                VALUES (%s, %s, %s)
            """, (nuevo_id, contraseña, rol))

            mensaje = f"✅ {rol} registrado correctamente (ID: {nuevo_id})"

        conn.commit()
        cursor.close()
        conn.close()

        return {"mensaje": mensaje}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error: {e}")


def guardar_imagen_jpg(imagen_input, ruta_guardado: str):
    """
    Guarda imagen como JPG. Acepta UploadFile o bytes.
    """
    if isinstance(imagen_input, bytes):
        imagen_bytes = imagen_input
    else:  # Es UploadFile
        imagen_bytes = imagen_input.file.read()
    
    imagen = Image.open(io.BytesIO(imagen_bytes))
    imagen = imagen.convert("RGB")  
    imagen.save(ruta_guardado, format="JPEG", quality=85)


@router.post("/vigilante/guardar")
def guardar_vigilante(
    nombre: str = Form(...),
    celular: str = Form(...),
    id_caseta: int = Form(...),
    contraseña: str = Form(None),
    id_vigilante: int = Form(None)  # Si viene, es edición
):
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        if id_vigilante:
            # Editar vigilante existente
            cursor.execute("""
                UPDATE vigilante
                SET nombre = %s, celular = %s, id_caseta = %s
                WHERE id = %s
            """, (nombre, celular, id_caseta, id_vigilante))
            mensaje = "✅ Vigilante editado correctamente"

        else:
            # Dar de alta nuevo vigilante
            cursor.execute("""
                INSERT INTO vigilante (nombre, celular, id_caseta)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (nombre, celular, id_caseta))
            nuevo_id = cursor.fetchone()[0]

            # Insertar en tabla login
            cursor.execute("""
                INSERT INTO login (id, contraseña, rol)
                VALUES (%s, %s, 'Vigilante')
            """, (nuevo_id, contraseña))

            mensaje = "✅ Vigilante registrado correctamente"

        conn.commit()
        cursor.close()
        conn.close()

        return {"mensaje": mensaje}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al guardar vigilante: {e}")
        


@router.post("/auto/guardar")
def guardar_auto(
    placa: str = Form(...),
    modelo: str = Form(...),
    id_titular: int = Form(...),
    id_auto: int = Form(None),
    token: str = Form(None)  # Solo requerido si se quiere editar
):
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        # Verificar que el titular existe y sea un residente (no autorizado)
        cursor.execute("SELECT rol FROM residente WHERE id = %s", (id_titular,))
        rol_info = cursor.fetchone()
        if not rol_info or rol_info[0] != "Residente":
            raise HTTPException(status_code=400, detail="❌ El titular no es un residente válido.")

        if id_auto:
            # 🛠️ Modo edición

            # Obtener el titular anterior
            cursor.execute("SELECT id_titular FROM autos WHERE id = %s", (id_auto,))
            anterior = cursor.fetchone()
            if not anterior:
                raise HTTPException(status_code=404, detail="Auto no encontrado")
            id_anterior = anterior[0]

            # Actualizar el auto
            cursor.execute("""
                UPDATE autos
                SET placa = %s, id_titular = %s
                WHERE id = %s
            """, (placa, id_titular, id_auto))

            # Si cambió el titular
            if id_anterior != id_titular:
                # 🧼 Eliminar relaciones anteriores
                cursor.execute("""
                    DELETE FROM residente_auto
                    WHERE id_tag = %s
                """, (id_auto,))

                # 🔗 Insertar nuevo vínculo con el nuevo titular
                cursor.execute("""
                    INSERT INTO residente_auto (id_tag, id_residente)
                    VALUES (%s, %s)
                """, (id_auto, id_titular))

            mensaje = "✅ Auto actualizado correctamente"

        else:
            # ✨ Validar que la placa no esté repetida
            cursor.execute("SELECT id FROM autos WHERE placa = %s", (placa,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="❌ Ya existe un auto con esa placa.")

            # ✨ Alta del auto
            cursor.execute("""
                INSERT INTO autos (placa, modelo, id_titular)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (placa, modelo, id_titular))
            id_auto = cursor.fetchone()[0]

            # 🔗 Insertar vínculo titular-auto
            cursor.execute("""
                INSERT INTO residente_auto (id_tag, id_residente)
                VALUES (%s, %s)
            """, (id_auto, id_titular))

            mensaje = "✅ Auto registrado correctamente"

        conn.commit()
        cursor.close()
        conn.close()

        return {"mensaje": mensaje, "id_auto": id_auto}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al guardar el auto: {e}")

@router.get("/residente_id_por_nombre")
def obtener_id(nombre: str):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM residente WHERE nombre = %s AND rol = 'Residente'", (nombre,))
    resultado = cur.fetchone()
    conn.close()

    if resultado:
        return {"id": resultado[0]}
    else:
        raise HTTPException(status_code=404, detail="Residente no encontrado")
        
from fastapi import Form

@router.post("/caseta/eliminar")
def eliminar_caseta(id_caseta: int = Form(...)):
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        # Primero, quitar la asignación de vigilantes con esa caseta
        cursor.execute("""
            UPDATE vigilante
            SET id_caseta = NULL
            WHERE id_caseta = %s
        """, (id_caseta,))

        # Luego, eliminar la caseta
        cursor.execute("""
            DELETE FROM caseta WHERE id = %s
        """, (id_caseta,))

        conn.commit()
        cursor.close()
        conn.close()

        return {"mensaje": "✅ Caseta eliminada correctamente"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al eliminar la caseta: {e}")


@router.delete("/vigilante/eliminar")
def eliminar_vigilante(id: int = Query(...)):
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        # Verificar que el vigilante exista
        cursor.execute("SELECT id FROM vigilante WHERE id = %s", (id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="❌ Vigilante no encontrado.")

        # Eliminar de la tabla vigilante
        cursor.execute("DELETE FROM vigilante WHERE id = %s", (id,))

        # Eliminar también de la tabla login
        cursor.execute("DELETE FROM login WHERE id = %s", (id,))

        conn.commit()
        cursor.close()
        conn.close()

        return {"mensaje": f"✅ Vigilante (ID: {id}) eliminado correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al eliminar vigilante: {e}")
        
@router.delete("/auto/eliminar")
def eliminar_auto(id: int = Query(...)):
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        # Verificar que el auto exista
        cursor.execute("SELECT id FROM autos WHERE id = %s", (id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="❌ Auto no encontrado.")

        # Eliminar las relaciones con residentes/autorizados
        cursor.execute("DELETE FROM residente_auto WHERE id_tag = %s", (id,))

        # Eliminar el auto
        cursor.execute("DELETE FROM autos WHERE id = %s", (id,))

        conn.commit()
        cursor.close()
        conn.close()

        return {"mensaje": f"✅ Auto (ID: {id}) eliminado correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al eliminar auto: {e}")
        

@router.delete("/persona/eliminar")
def eliminar_persona(id: int = Query(...), rol: str = Query(...)):
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        # Verificar que existe
        cursor.execute("SELECT rol FROM residente WHERE id = %s", (id,))
        persona = cursor.fetchone()

        if not persona:
            raise HTTPException(status_code=404, detail="❌ Usuario no encontrado.")

        if persona[0] != rol.capitalize():
            raise HTTPException(status_code=400, detail="❌ El rol no coincide con el usuario.")
            
        ruta_foto = f"static/perfiles/{id}_perfil.jpg"

        if rol.lower() == "residente":
            # 1) Obtener autos del residente
            cursor.execute("SELECT id FROM autos WHERE id_titular = %s", (id,))
            autos = cursor.fetchall()

            # 2) Eliminar relaciones en residente_auto (personas autorizadas que podían sacar esos autos)
            for (id_auto,) in autos:
                cursor.execute("DELETE FROM residente_auto WHERE id_tag = %s", (id_auto,))
            
            # 3) Eliminar autos
            cursor.execute("DELETE FROM autos WHERE id_titular = %s", (id,))
        
        elif rol.lower() == "autorizado":
            # Eliminar sus permisos de sacar autos
            cursor.execute("DELETE FROM residente_auto WHERE id_residente = %s", (id,))

        # Borrar de residente y login (para ambos casos)
        cursor.execute("DELETE FROM residente WHERE id = %s", (id,))
        cursor.execute("DELETE FROM login WHERE id = %s", (id,))

        conn.commit()
        cursor.close()
        conn.close()
        
        if os.path.exists(ruta_foto):
            os.remove(ruta_foto)

        return {"mensaje": f"✅ {rol.capitalize()} (ID: {id}) eliminado correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al eliminar: {e}")