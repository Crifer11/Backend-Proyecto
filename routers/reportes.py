from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from database import conectar_db
from weasyprint import HTML
from jinja2 import Template
from datetime import datetime
import os
from io import BytesIO
from pathlib import Path

router = APIRouter()

@router.get("/reportes")
def obtener_reportes(id: int, rol: str):
    try:
        conn = conectar_db()
        cur = conn.cursor()

        reportes = []
        incidentes_menores = []

        if rol in ["Administrador", "Vigilante"]:
            # Obtener todos los reportes normales
            cur.execute("SELECT * FROM reporte")
            reportes = cur.fetchall()

            # Obtener todos los incidentes menores
            cur.execute("SELECT * FROM mini")
            incidentes_menores = cur.fetchall()

        elif rol == "Residente":
            # Buscar reportes directamente por el ID del residente
            cur.execute("SELECT * FROM reporte WHERE id_residente = %s", (id,))
            reportes = cur.fetchall()
        
            if not reportes:
                return {"mensaje": "Este residente no tiene reportes registrados."}

        else:
            return {"error": "Rol no válido"}

        cur.close()
        conn.close()

        return {
            "reportes": reportes,
            "incidentes_menores": incidentes_menores if rol != "Residente" else []
        }

    except Exception as e:
        return {"error": f"❌ Error al obtener reportes: {str(e)}"}


@router.get("/descargar_pdf")
def descargar_pdf(id_reporte: str = Query(...)):
    try:
        # ✅ Convertir string ISO a datetime para compatibilidad
        fecha_dt = datetime.fromisoformat(id_reporte)
        id_limpio = id_reporte.replace(":", "")
        ruta_foto_rostro = os.path.join("static", "reportes", f"{id_limpio}_rostro.jpg")
        ruta_foto_placa = os.path.join("static", "reportes", f"{id_limpio}_placa.jpg")
        
        # 🔍 Obtener datos del reporte desde la base de datos
        conn = conectar_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM reporte WHERE tiempo = %s", (fecha_dt,))
        datos_raw = cur.fetchone()
        cur.close()
        conn.close()
        
        if not datos_raw:
            raise HTTPException(status_code=404, detail="Reporte no encontrado.")
        
        # 🧾 Estructurar los datos
        datos = {
            "fecha": str(datos_raw[0].date()),
            "hora": str(datos_raw[0].time())[:8],
            "caseta": datos_raw[3],
            "vigilante": datos_raw[4],
            "motivo": datos_raw[5],
            "carro": datos_raw[7],
            "placa": datos_raw[2],
            "id_duenio": datos_raw[10],
            "duenio": datos_raw[8],
            "comentario": datos_raw[6],
            "conductor": datos_raw[1],
            "placa_identificada": datos_raw[9],
            "foto_rostro": ruta_foto_rostro if os.path.exists(ruta_foto_rostro) else None,
            "foto_placa": ruta_foto_placa if os.path.exists(ruta_foto_placa) else None,
        }
        
        # 📄 Plantilla HTML
        html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Reporte de Incidente | SafeGate</title>
  <style>
    :root {
      --safe-green: #2ecc71;
      --gate-blue: #2f5fb3;
      --dark-text: #2c3e50;
      --light-bg: #f8f9fa;
    }

    @page {
      size: A4;
      margin: 15mm;
    }

    body {
      background: #e9ecef;
      font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: var(--dark-text);
      margin: 0;
      padding: 20px;
    }

    .reporte-container {
      max-width: 850px;
      margin: 0 auto;
      background: white;
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0,0,0,0.1);
      border: 1px solid rgba(255,255,255,0.3);
    }

    /* Encabezado Estilo Moderno */
    .header {
      background: linear-gradient(135deg, var(--gate-blue), #1a3a6d);
      color: white;
      padding: 30px;
      display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center;
      gap: 20px;
    }

    .logo {
      height: 60px;
      filter: brightness(0) invert(1); /* Hace que el logo se vea blanco si es oscuro */
    }

    .header-info h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 1px;
      text-transform: uppercase;
    }

    .header-info p {
      margin: 5px 0 0;
      opacity: 0.8;
      font-size: 14px;
    }

    .fecha-box {
      text-align: right;
      background: rgba(255,255,255,0.1);
      padding: 10px 15px;
      border-radius: 10px;
      font-size: 13px;
      line-height: 1.4;
    }

    /* Cuerpo del Reporte */
    .content {
      padding: 30px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 25px;
    }

    .seccion {
      grid-column: span 1;
    }

    .full-width {
      grid-column: span 2;
    }

    .seccion-titulo {
      font-size: 12px;
      font-weight: bold;
      color: var(--gate-blue);
      text-transform: uppercase;
      margin-bottom: 15px;
      border-bottom: 2px solid var(--safe-green);
      display: inline-block;
      padding-bottom: 3px;
    }

    .info-card {
      background: var(--light-bg);
      padding: 15px;
      border-radius: 12px;
      border-left: 4px solid var(--gate-blue);
    }

    .dato {
      margin-bottom: 10px;
      display: flex;
      flex-direction: column;
    }

    .dato:last-child { margin-bottom: 0; }

    .label {
      font-size: 11px;
      color: #7f8c8d;
      font-weight: bold;
      text-transform: uppercase;
    }

    .valor {
      font-size: 15px;
      font-weight: 600;
      color: #34495e;
    }

    /* Comentario */
    .comentario-box {
      background: #fff;
      border: 1px solid #dee2e6;
      padding: 20px;
      border-radius: 12px;
      font-style: italic;
      line-height: 1.6;
      position: relative;
    }

    /* Fotos */
    .grid-fotos {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }

    .foto-frame {
      background: #f8f9fa;
      border: 1px solid #ddd;
      border-radius: 15px;
      padding: 10px;
      text-align: center;
    }

    .foto-img {
      width: 100%;
      height: 220px;
      object-fit: cover;
      border-radius: 10px;
      margin-top: 10px;
      background: #eee;
    }

    .badge {
      display: inline-block;
      background: var(--gate-blue);
      color: white;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: bold;
    }

    /* Footer / Firma */
    .footer {
      margin-top: 30px;
      padding: 20px 30px;
      border-top: 1px solid #eee;
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: #95a5a6;
    }

    @media print {
      body { background: white; padding: 0; }
      .reporte-container { box-shadow: none; border: none; width: 100%; }
    }
  </style>
</head>
<body>

  <div class="reporte-container">
    <header class="header">
      <img src="{{ logo_path }}" class="logo" alt="SafeGate Logo" />
      <div class="header-info">
        <h1>Reporte de Incidente</h1>
        <p>Sistema de Seguridad Inteligente SafeGate</p>
      </div>
      <div class="fecha-box">
        <strong>FECHA:</strong> {{ fecha }}<br>
        <strong>HORA:</strong> {{ hora }}
      </div>
    </header>

    <main class="content">
      
      <div class="seccion">
        <span class="seccion-titulo">Ubicación y Vigilancia</span>
        <div class="info-card">
          <div class="dato">
            <span class="label">Caseta / Punto de Control</span>
            <span class="valor">{{ caseta }}</span>
          </div>
          <div class="dato">
            <span class="label">Vigilante Responsable</span>
            <span class="valor">{{ vigilante }}</span>
          </div>
        </div>
      </div>

      <div class="seccion">
        <span class="seccion-titulo">Clasificación</span>
        <div class="info-card" style="border-left-color: #e74c3c;">
          <div class="dato">
            <span class="label">Motivo del Incidente</span>
            <span class="valor">{{ motivo }}</span>
          </div>
        </div>
      </div>

      <div class="seccion">
        <span class="seccion-titulo">Identificación del Vehículo</span>
        <div class="info-card">
          <div class="dato">
            <span class="label">Modelo / Carro</span>
            <span class="valor">{{ carro }}</span>
          </div>
          <div class="dato">
            <span class="label">Placa de Registro</span>
            <span class="valor" style="font-family: monospace; font-size: 18px;">{{ placa }}</span>
          </div>
        </div>
      </div>

      <div class="seccion">
        <span class="seccion-titulo">Datos del Propietario</span>
        <div class="info-card">
          <div class="dato">
            <span class="label">Nombre del Dueño</span>
            <span class="valor">{{ duenio }}</span>
          </div>
          <div class="dato">
            <span class="label">ID de Usuario</span>
            <span class="valor">{{ id_duenio }}</span>
          </div>
        </div>
      </div>

      <div class="full-width">
        <span class="seccion-titulo">Descripción Detallada</span>
        <div class="comentario-box">
          {{ comentario }}
        </div>
      </div>

      <div class="full-width">
        <span class="seccion-titulo">Evidencia Digital</span>
        <div class="grid-fotos">
          <div class="foto-frame">
            <span class="badge">IDENTIFICACIÓN ROSTRO</span>
            <p style="font-size: 12px; margin: 5px 0;">Conductor: {{ conductor }}</p>
            {% if foto_rostro %}
            <img src="{{ foto_rostro }}" class="foto-img" />
            {% else %}
            <div class="foto-img" style="display: flex; align-items: center; justify-content: center;">Sin Imagen</div>
            {% endif %}
          </div>

          <div class="foto-frame">
            <span class="badge">LECTURA DE PLACA</span>
            <p style="font-size: 12px; margin: 5px 0;">Captura: {{ placa_identificada }}</p>
            {% if foto_placa %}
            <img src="{{ foto_placa }}" class="foto-img" />
            {% else %}
            <div class="foto-img" style="display: flex; align-items: center; justify-content: center;">Sin Imagen</div>
            {% endif %}
          </div>
        </div>
      </div>
    </main>

    <footer class="footer">
      <span>SafeGate Security System &copy; 2026</span>
      <span>Documento generado electrónicamente - ID: SG-{{ placa }}-{{ fecha }}</span>
    </footer>
  </div>

</body>
</html>
        """

        # 🎨 Renderizar HTML con Jinja2
        template = Template(html_template)
        
        # Obtener ruta absoluta del logo
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        logo_path = "file://" + os.path.join(BASE_DIR, "logo2.PNG")
        
        # Convertir rutas relativas a absolutas para WeasyPrint
        if datos["foto_rostro"]:
            datos["foto_rostro"] = Path(datos["foto_rostro"]).resolve().as_uri()
        
        if datos["foto_placa"]:
            datos["foto_placa"] = Path(datos["foto_placa"]).resolve().as_uri()
        
        print("DEBUG LOGO:", logo_path)
        print("DEBUG ROSTRO:", datos["foto_rostro"], os.path.exists(datos["foto_rostro"]))
        print("DEBUG PLACA:", datos["foto_placa"], os.path.exists(datos["foto_placa"]))
        html_renderizado = template.render(
            logo_path=logo_path,
            **datos
        )
        
        # 📄 Generar PDF con WeasyPrint
        pdf_bytes = HTML(string=html_renderizado).write_pdf()
        
        # 📤 Enviar como descarga
        buffer = BytesIO(pdf_bytes)
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=reporte_{id_limpio}.pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al generar el PDF: {str(e)}")
