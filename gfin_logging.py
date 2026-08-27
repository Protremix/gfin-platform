"""
GFIN Structured Logging System
Replaces print() statements with proper structured JSON logging.
Outputs to both stdout (for journald) and /gfin/logs/gfin_server.log
"""
import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production observability."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source_module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "ip"):
            log_entry["ip"] = record.ip
        if hasattr(record, "endpoint"):
            log_entry["endpoint"] = record.endpoint
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging():
    """Configure structured logging for the GFIN server."""
    os.makedirs("/gfin/logs", exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    
    # Console handler (goes to journald via systemd)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # File handler (rotating, 10MB per file, keep 7 days)
    file_handler = logging.handlers.RotatingFileHandler(
        "/gfin/logs/gfin_server.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=7
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    
    # Named loggers for different components
    loggers = {
        "gfin.api": logging.getLogger("gfin.api"),
        "gfin.auth": logging.getLogger("gfin.auth"),
        "gfin.investigation": logging.getLogger("gfin.investigation"),
        "gfin.telegram": logging.getLogger("gfin.telegram"),
        "gfin.security": logging.getLogger("gfin.security"),
        "gfin.database": logging.getLogger("gfin.database"),
        "gfin.hunter": logging.getLogger("gfin.hunter"),
        "gfin.ai": logging.getLogger("gfin.ai"),
    }
    
    for name, logger in loggers.items():
        logger.setLevel(logging.INFO)
        logger.propagate = True
    
    logging.info("Structured logging initialized", extra={"source_module": "logging"})
    return logging.getLogger("gfin")

def get_logger(name="gfin"):
    """Get a named logger."""
    return logging.getLogger(name)

# Request logging middleware
def create_request_logger():
    """Create a middleware that logs all HTTP requests with timing."""
    import time
    
    async def log_requests(request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = (time.time() - start) * 1000
        
        logger = logging.getLogger("gfin.api")
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code}",
            extra={
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
                "ip": request.headers.get("X-Real-IP", request.client.host if request.client else "unknown"),
            }
        )
        return response
    
    return log_requests
