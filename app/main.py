from fastapi import FastAPI
app = FastAPI(title="SVARA Room Service API")

# app.include_router(requests_router, prefix="/api/requests", tags=["requests"])
# app.include_router(inventory_router, prefix="/api/inventory", tags=["inventory"])
# app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
# app.include_router(reconciliations_router, prefix="/api/reconciliations", tags=["reconciliations"])
# app.include_router(ws_router, tags=["websocket"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
