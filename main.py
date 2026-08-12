from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config.database import init_db
from routes.auth_routes import router as auth_router
from routes.page_routes import router as page_router
from routes.usuarios_routes import router as usuarios_router
from routes.produtos_routes import router as produtos_router
from routes.clientes_routes import router as clientes_router
from routes.pedidos_routes import router as pedidos_router
from routes.dashboard_routes import router as dashboard_router
from routes.financeiro_routes import router as financeiro_router
from routes.orcamentos_routes import router as orcamentos_router

init_db()

app = FastAPI(title="Sistema Interno da Empresa")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Registra os roteadores
app.include_router(auth_router)
app.include_router(page_router)
app.include_router(usuarios_router)
app.include_router(produtos_router)
app.include_router(clientes_router)
app.include_router(pedidos_router)
app.include_router(dashboard_router)
app.include_router(financeiro_router)
app.include_router(orcamentos_router)