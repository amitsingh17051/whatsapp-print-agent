"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.payment import router as payment_router
from app.api.simulator import router as simulator_router
from app.api.whatsapp import router as whatsapp_router
from app.database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for initialization and teardown."""
    init_db()
    yield


app = FastAPI(
    title="WhatsApp Print Agent",
    description="WhatsApp-based printing service powered by deterministic business services and LangGraph.",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount API routers
app.include_router(whatsapp_router)
app.include_router(payment_router)
app.include_router(simulator_router)


@app.get("/health", tags=["System"])
def health_check() -> JSONResponse:
    """
    System health check.
    Conforms to GET /health in API_CONTRACT.md.
    """
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.api_route("/reload-settings", methods=["GET", "POST"], tags=["System"])
def reload_env_settings() -> JSONResponse:
    """Reload environment variables without dropping connection or tunnel."""
    from app.config import reload_settings
    current = reload_settings()
    return JSONResponse(
        status_code=200,
        content={
            "status": "settings_reloaded",
            "mock_mode": current.MOCK_MODE,
            "phone_id": current.WHATSAPP_PHONE_NUMBER_ID,
            "token_prefix": current.WHATSAPP_API_TOKEN[:15] + "...",
        },
    )
