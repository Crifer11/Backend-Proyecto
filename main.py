from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import login, reportes, informacion, supervision, incidentes, administrar, token, menu
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(
    title="Sistema de Acceso Automatizado",
    description="API para el proyecto de control de acceso de autos",
    version="1.0"
)

# Incluir las rutas
app.include_router(login.router)
app.include_router(menu.router)
app.include_router(reportes.router)
app.include_router(informacion.router)
app.include_router(supervision.router)
app.include_router(incidentes.router)
app.include_router(administrar.router)
app.include_router(token.router)
app.mount("/static", StaticFiles(directory=os.path.join(os.getcwd(), "static")), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puedes cambiar esto por ["http://localhost:3000"] si quieres más seguridad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
