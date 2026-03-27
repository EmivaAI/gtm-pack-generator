from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from emiva_core.core.settings import settings
from emiva_core.core.logger import setup_logger
from emiva_api.api.routes import crud

logger = setup_logger(__name__)

app = FastAPI(
    title="Emiva Core Data API",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "up", "version": "1.0.0"}

app.include_router(crud.router, prefix="/api", tags=["CRUD"])
