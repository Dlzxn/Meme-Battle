import logging
import sys
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import engine, Base
from app.routers import auth, rooms, stats, websocket as ws_router

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    fmt = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    try:
        from app.telegram import TelegramHandler
        tg = TelegramHandler()
        tg.setLevel(logging.ERROR)
        tg.setFormatter(logging.Formatter(fmt))
        logging.getLogger().addHandler(tg)
    except Exception as e:
        logging.getLogger(__name__).warning("Could not attach Telegram handler: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_logging()
    logger.info("Starting Meme Battle API")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        from app.telegram import resolve_chat_id
        await resolve_chat_id()
    except Exception:
        pass
    yield
    await engine.dispose()
    logger.info("Meme Battle API stopped")


app = FastAPI(title="Meme Battle API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(stats.router)
app.include_router(ws_router.router)


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    try:
        from app.telegram import send_error
        await send_error(f"500 {request.method} {request.url.path}", detail)
    except Exception:
        pass
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health():
    return {"status": "ok"}
