from fastapi import FastAPI
from app.routes.requests import router as requests_router
from app.routes.inventory import router as inventory_router
from app.routes.reports import router as reports_router
from app.routes.reconciliations import router as reconciliations_router
from app.sockets import router as ws_router

app = FastAPI(title="SVARA Room Service API")

app.include_router(requests_router, prefix="/api/requests", tags=["requests"])
app.include_router(inventory_router, prefix="/api/inventory", tags=["inventory"])
app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
app.include_router(reconciliations_router, prefix="/api/reconciliations", tags=["reconciliations"])
app.include_router(ws_router, tags=["websocket"])