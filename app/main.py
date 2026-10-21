from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.api.auth import router as auth_router
from app.api.api_keys import router as api_keys_router
from app.api.gateway import router as gateway_router
from app.api.usage import router as usage_router
from app.api.status import router as status_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    from app.services.rate_limiter import RateLimiterService
    from app.core.database import async_session
    from app.services.provider_health_service import ProviderHealthService
    from app.services.langfuse_service import LangfuseService
    import asyncio
    from app.services.cache_cleanup_service import start_cache_cleanup_loop
    
    await RateLimiterService.init()
    LangfuseService.init()
    
    async with async_session() as db:
        await ProviderHealthService.initialize_metrics(db)
        
    cleanup_task = asyncio.create_task(start_cache_cleanup_loop())
        
    yield
    # Shutdown actions
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await RateLimiterService.close()

app = FastAPI(
    title="LLM Gateway Platform API",
    description="A secure and cost-tracked gateway proxy for multiple AI models.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware to allow connection from web frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.observability import router as observability_router
from app.api.cache_analytics import router as cache_router
from app.api.guardrail_analytics import router as guardrails_router
from app.api.prompts import router as prompts_router
from app.api.benchmarks import router as benchmarks_router

# Register routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(api_keys_router, prefix="/api/api-keys", tags=["API Key Management"])
app.include_router(gateway_router, prefix="/api/gateway", tags=["LLM Gateway"])
app.include_router(usage_router, prefix="/api/usage", tags=["Analytics & Usage Dashboard"])
app.include_router(status_router, prefix="/api/providers", tags=["Providers Config & Health"])
app.include_router(observability_router, prefix="/api/observability", tags=["Observability & Tracing"])
app.include_router(cache_router, prefix="/api/cache", tags=["Cache Analytics"])
app.include_router(guardrails_router, prefix="/api/guardrails", tags=["Guardrails & Content Safety"])
app.include_router(prompts_router, prefix="/api/prompts", tags=["Prompt Registry & Evaluation"])
app.include_router(benchmarks_router, prefix="/api/benchmarks", tags=["Model Evaluation & Benchmarking"])


from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import uuid

@app.exception_handler(HTTPException)
async def gateway_http_exception_handler(request: Request, exc: HTTPException):
    """Interceptors to set X-Trace-ID header and log trace status for gateway exceptions."""
    # Check if request has a trace_id already generated
    trace_id = getattr(request.state, "trace_id", None)
    
    if request.url.path == "/api/gateway/chat":
        if not trace_id:
            trace_id = f"trace_{uuid.uuid4().hex[:12]}"
            
        # Log auth errors to DB (as we don't hit route_request for 401s)
        if exc.status_code == 401:
            from app.core.database import async_session
            from app.services.trace_service import TraceService
            async with async_session() as db:
                await TraceService.start_trace(trace_id, None, "[Unauthorized Request]", db)
                await TraceService.update_trace(
                    trace_id=trace_id,
                    response="[Unauthorized]",
                    status_code=exc.status_code,
                    error_type="authentication_error",
                    error_message=str(exc.detail),
                    db=db
                )
        
        headers = {"X-Trace-ID": trace_id}
        # Standardize response detail formatting
        detail = exc.detail
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail},
            headers=headers
        )
        
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to ensure API gateway is running."""
    return {"status": "healthy"}

# Mount the static files directory at the root last, so it acts as a fallback for the SPA
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Automatically runs on port 9000 when main.py is executed directly
    uvicorn.run("app.main:app", host="127.0.0.1", port=9000, reload=True)
