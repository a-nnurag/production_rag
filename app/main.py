import time
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from langsmith import traceable
from dotenv import load_dotenv

from app.config import get_settings

from app.models import(
    ChatRequest,ChatResponse,
    HealthResponse,MetricsResponse,ErrorResponse
)

from app.security import SecurityPipeline
from app.cache import ResponseCache
from app.monitoring import get_logger,MetricsCollector,RequestTime
from app.agent import ProductionAgent

load_dotenv()

security :SecurityPipeline = None
cache: ResponseCache = None
metrics: MetricsCollector = None
agent: ProductionAgent = None
logger= get_logger()  

# ===LifeSpan (startup/shutdown) ===
 
@asynccontextmanager
async def lifespan(app:FastAPI):
    """
    Initialize all components on startup, clean up on shutdown.
    This is the modern FASTAPI pattern (replaces @app.on_events).
    """

    global security,cache,metrics,agent

    settings = get_settings()

    logger.info("Starting producton API...",extra={"extra_data":{
        "environment":settings.app_env,
        "primary_model": settings.primary_model,
        "tracing_enabled": settings.langchain_tracing_v2
    }})

    #Initialzing components
    security = SecurityPipeline()
    cache = ResponseCache(ttl_seconds=settings.cache_ttl_seconds)
    metrics = MetricsCollector()
    agent = ProductionAgent()

    logger.info("All components initialized. Ready to serve requests.")

    yield #App is running

    #Shutdown
    logger.info("Shutting down...",extra={"extra_data":metrics.stats})


# =====Rate Limiter Setup ====
limiter = Limiter(key_func=get_remote_address)

#==FASTAPI app===
app=FastAPI(
    title="Production Langgraph API",
    description="A production ready chat API with security ,caching and observability",
    version = "1.0.0",
    lifespan=lifespan
)
app.state.limiter=limiter


# === Exception Handlers ===
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(
        "Rate limit exceeded",
        extra={
            "extra_data": {
                "client_ip": get_remote_address(request),
                "path": request.url.path,
            }
        },
    )

    metrics.record_request(
        latency_ms=0,
        error=True,
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": "Too many requests. Please try again later.",
            "status_code": 429,
        },
    )


# ========================
# ENDPOINTS
# ========================

@app.post("/chat",response_model=ChatResponse)
@limiter.limit(get_settings().rate_limit)
@traceable(name="chat_endpoint")
async def chat(request:Request,body:ChatRequest):
    """
    Main chat endpoint

    Flow:
    1. Security check (injection+ PII masking)
    2. Cache lookup
    3. Langgraph agent invoke (if cache miss)
    4. Output validation
    5. Cache store
    6. Return response
    """

    with RequestTime() as timer:
        security_notes = []

        #-------- Step1 SECURITY CHECK -------------#
        is_allowed,cleaned_message,notes = security.check_input(body.message)
        security_notes.extend(notes)

        if not is_allowed:
            logger.warning("Request blocked by security",extra={"extra_data":{
                "reason":notes,
                "thread_id":body.thread_id,
            }})
            metrics.record_request(latency_ms=0,error=True)
            raise HTTPException(
                status_code=400,
                detail="Your message was blockd by our security filters"
            )
        
        #---------Step2  Cache Lookup-----
        cached_response = cache.get(cleaned_message)
        if cached_response is not None:
            metrics.record_request(latency_ms=0,cache_hit=True)
            logger.info("Cache hit", extra={"extra_data":{
                "thread_id":body.thread_id
            }})
            return ChatResponse(
                response=cached_response,
                thread_id=body.thread_id,
                model_used="cache",
                cached_used=True,
                processing_time_ms=0,
            )
    
        #--------Step3 : Invoke Langgraph Agent---
        try:
            result = agent.invoke(cleaned_message)
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}",extra={"extra_data":{
                "thread_id":body.thread_id,
                "error": str(e)
            }})
            metrics.record_request(latency_ms=0,error=True)
            raise HTTPException(
                status_code=500,
                detail="An error occured while processing the request"
            )
        
        response_text=result["response"]
        model_used= result["model_used"]

        #--------Step4 :Output Validation -------
        isSuccess , validated_response, output_warnings=security.validate_output(response_text)
        security_notes.extend(output_warnings)

        #---------Step5:Cache Store----
        cache.set(cleaned_message,validated_response)

    #------Step6:Log and Record Metrics----
    input_token=int(len(cleaned_message.split())*1.3)
    output_token=int(len(validated_response.split())*1.3)

    metrics.record_request(
        latency_ms=timer.elapsed_ms ,
        input_tokens=input_token,
        output_tokens=output_token,
        cache_hit=False
    )

    if security_notes:
        logger.info("Security notes", extra={"extra_data":{
            "notes":security_notes,
            "thread_id":body.thread_id,
        }})

    logger.info("Request completed",extra={"extra_data":{
        "thread_id": body.thread_id,
        "model_used": model_used,
        "latency_ms":round(timer.elapsed_ms,2)
    }})

    return ChatResponse(
        response=validated_response,
        thread_id=body.thread_id,
        model_used=model_used,
        cached_used=False,
        processing_time_ms=round(timer.elapsed_ms,2)
    )
        
@app.get("/health",response_model=HealthResponse)
async def health():
    """Health check for Docker/Kubernetes."""
    settings = get_settings()

    checks = {
        "agent": agent is not None,
        "security": security is not None,
        "cache": cache is not None,
    }

    all_healthy = all(checks.values())

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        environment=settings.app_env,
        checks=checks
    )

@app.get("/metrics",response_model=MetricsResponse)
async def get_metrics():
    """Metrics for monitoring dashboards"""
    summary = metrics.stats
    return MetricsResponse(**summary)

@app.get("/cache/stats")
async def cache_stats():
    """Cache performance statistics"""
    return cache.stats
