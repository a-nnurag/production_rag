"""
API contracts and data models for the application.(means what goes in and what goes out
 of the API endpoints)
"""

from pydantic import BaseModel, Field
from datetime import datetime

class ChatRequest(BaseModel):
    """Incoming chat request"""
    message: str = Field(
        min_length=1,
        description="The user's message to the chatbot",
        max_length=1000
    )
    thread_id:str=Field(
        default="default",
        description="Conversation thread identifier for context management", 
    )

class ChatResponse(BaseModel):
    """Outgoing chat response"""
    response:str
    thread_id:str
    model_used:str
    cached_used:bool =False
    processing_time_ms: float
    timestamp: str=Field(default_factory=lambda: datetime.utcnow().isoformat()) 

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = "ok"
    environment: str
    version: str = "1.0.0"
    checks : dict={}

# class MetricsResponse(BaseModel):
#     """Metrics endpoint response"""
#     total_requests: int
#     total_errors: int
#     error_rate: str
#     avg_latency_ms:float
#     cache_hit_rate:str
#     total_input_tokens: int
#     total_output_tokens: int
class MetricsResponse(BaseModel):
    """Metrics endpoint response"""
    requests_total: int
    errors_total: int
    error_rate_percent: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    input_tokens: int
    output_tokens: int
    cache_hits: int
    cache_misses: int
    cache_hit_rate_percent: float
    uptime_seconds: float

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error_code: str
    detail: str | None = None
    request_id: str | None = None