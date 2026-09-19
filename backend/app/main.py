import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import bills, chores, dashboard, groceries, households, members, messages
from app.core.config import get_settings
from app.database.session import init_db
from app.websocket import chat as chat_ws

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("liferoom")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("LifeRoom API started (env=%s)", settings.environment)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Centralized error handling: never leak stack traces to clients ---


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": "Validation error", "errors": errors})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# --- Routes ---

app.include_router(households.router)
app.include_router(members.router)
app.include_router(chores.router)
app.include_router(bills.router)
app.include_router(groceries.router)
app.include_router(messages.router)
app.include_router(dashboard.router)
app.include_router(chat_ws.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": settings.app_name}


# Serve the built UI and API from one origin for team demo tunnels.
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.is_dir():
    @app.get("/app", include_in_schema=False)
    @app.get("/app/{path:path}", include_in_schema=False)
    @app.get("/create", include_in_schema=False)
    @app.get("/join", include_in_schema=False)
    def frontend_page():
        return FileResponse(frontend_dist / "index.html")

    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
