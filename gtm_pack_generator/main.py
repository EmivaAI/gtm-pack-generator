from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from emiva_core.core.settings import settings
from emiva_core.core.logger import logger
from gtm_pack_generator.api.routes import generate, crud


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application resources...")
    yield
    logger.info("Shutting down application resources...")


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "allowed_origins", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled application exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Please try again later."},
    )


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "up", "version": settings.version}



app.include_router(generate.router, prefix="/api/generate", tags=["Generate"])
