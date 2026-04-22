import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes_chat import router as chat_router
from app.api.routes_health import router as health_router
from app.api.routes_history import router as history_router
from app.api.routes_images import router as images_router
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.core.utils import ensure_dir

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_dir(settings.output_dir)
    logger.info(
        "Starting %s on %s:%s",
        settings.app_name,
        settings.app_host,
        settings.app_port,
    )
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def get_asset_version() -> str:
    candidates = [
        BASE_DIR / "static" / "css" / "styles.css",
        BASE_DIR / "static" / "js" / "app.js",
    ]
    mtimes = [int(path.stat().st_mtime) for path in candidates if path.exists()]
    if not mtimes:
        return settings.app_version
    return str(max(mtimes))


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code, "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Unexpected server error.",
            "code": "internal_server_error",
            "detail": str(exc),
        },
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "asset_version": get_asset_version()},
    )


app.include_router(health_router)
app.include_router(chat_router)
app.include_router(images_router)
app.include_router(history_router)
