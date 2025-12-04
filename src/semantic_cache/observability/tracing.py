"""OpenTelemetry tracing utilities for semantic cache."""

import functools
from typing import Optional, Callable, Any, Dict
from contextlib import contextmanager

# Try to import OpenTelemetry, but make it optional
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.trace import Status, StatusCode, Span
    
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    TracerProvider = None
    Span = None

from semantic_cache.utils.logging import get_logger

logger = get_logger("observability.tracing")

# Global tracer instance
_tracer: Optional[Any] = None
_tracer_provider: Optional[Any] = None


def setup_tracing(
    service_name: str = "semantic-cache",
    exporter_type: str = "console",
    endpoint: Optional[str] = None,
) -> bool:
    """
    Setup OpenTelemetry tracing.
    
    Args:
        service_name: Name of the service
        exporter_type: Type of exporter ("console", "otlp", "jaeger")
        endpoint: Endpoint for exporter (for otlp/jaeger)
        
    Returns:
        True if tracing was setup successfully, False otherwise
    """
    global _tracer, _tracer_provider
    
    if not OTEL_AVAILABLE:
        logger.warning(
            "OpenTelemetry not installed. Install with: "
            "pip install semantic-cache[observability]"
        )
        return False
    
    try:
        # Create resource with service name
        resource = Resource(attributes={SERVICE_NAME: service_name})
        
        # Create tracer provider
        _tracer_provider = TracerProvider(resource=resource)
        
        # Setup exporter
        if exporter_type == "console":
            exporter = ConsoleSpanExporter()
        elif exporter_type == "otlp":
            exporter = OTLPSpanExporter(
                endpoint=endpoint or "http://localhost:4317",
                insecure=True,
            )
        elif exporter_type == "jaeger":
            try:
                from opentelemetry.exporter.jaeger.thrift import JaegerExporter
                exporter = JaegerExporter(
                    agent_host_name=endpoint or "localhost",
                    agent_port=6831,
                )
            except ImportError:
                logger.error("Jaeger exporter not available")
                return False
        else:
            logger.error(f"Unknown exporter type: {exporter_type}")
            return False
        
        # Add span processor
        _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        
        # Set global tracer provider
        trace.set_tracer_provider(_tracer_provider)
        
        # Get tracer
        _tracer = trace.get_tracer(__name__)
        
        logger.info(
            f"Tracing initialized with {exporter_type} exporter "
            f"for service {service_name}"
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup tracing: {e}")
        return False


def get_tracer():
    """Get the global tracer instance."""
    global _tracer
    
    if not OTEL_AVAILABLE:
        return None
    
    # Return existing tracer or None - do NOT auto-initialize
    # Tracing must be explicitly enabled via setup_tracing()
    return _tracer


@contextmanager
def trace_operation(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Context manager for tracing an operation.
    
    Args:
        operation_name: Name of the operation
        attributes: Optional attributes to add to the span
        
    Example:
        with trace_operation("cache.check", {"cache_key": key}):
            result = await cache.check(prompt)
    """
    tracer = get_tracer()
    
    if tracer is None or not OTEL_AVAILABLE:
        # No-op if tracing not available
        yield None
        return
    
    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                # Convert value to string if it's not a primitive type
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(key, value)
                else:
                    span.set_attribute(key, str(value))
        
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def trace_async(operation_name: str = None):
    """
    Decorator for tracing async functions.
    
    Args:
        operation_name: Optional custom operation name
        
    Example:
        @trace_async("cache.store")
        async def store(prompt, response):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with trace_operation(op_name):
                return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def add_span_attributes(**attributes):
    """
    Add attributes to the current span.
    
    Args:
        **attributes: Key-value pairs to add as attributes
    """
    if not OTEL_AVAILABLE:
        return
    
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        for key, value in attributes.items():
            if isinstance(value, (str, int, float, bool)):
                current_span.set_attribute(key, value)
            else:
                current_span.set_attribute(key, str(value))


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event to the current span.
    
    Args:
        name: Event name
        attributes: Optional event attributes
    """
    if not OTEL_AVAILABLE:
        return
    
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.add_event(name, attributes or {})
