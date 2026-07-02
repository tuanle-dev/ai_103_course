import time
from datetime import datetime
from contextlib import contextmanager
from functools import wraps
from typing import Optional
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind
from azure.monitor.opentelemetry import configure_azure_monitor


class OpenTelemetry:
    """OpenTelemetry tracing helper class for Application Insights."""

    def __init__(
        self,
        application_insights_connection_string,
        user_name,
        user_role,
    ):
        self.application_insights_connection_string = (
            application_insights_connection_string
        )
        self.user_name = user_name
        self.user_role = user_role
        self.tracer = None
        self.provider = None
        self.exporter = None
        self.conversation_id = None

    def setup_tracing(self):
        """Initialize Azure Monitor tracing and return a tracer instance."""
        try:
            # Configure Azure Monitor with logging enabled
            configure_azure_monitor(
                connection_string=self.application_insights_connection_string,
            )

            self.tracer = trace.get_tracer(__name__)
            print("[TRACE] Azure Monitor tracing initialized successfully")

        except Exception as e:
            print(f"[TRACE] WARNING: Failed to initialize Azure Monitor: {e}")
            self.tracer = trace.get_tracer(__name__)

    def set_conversation_id(self, conversation_id: str):
        """Set the current conversation ID for correlation."""
        self.conversation_id = conversation_id

    def get_conversation_id(self) -> Optional[str]:
        """Get the current conversation ID."""
        return self.conversation_id

    def add_conversation_attributes(self, span, **additional_attrs):
        """Helper to add conversation ID and standard attributes to a span."""
        if self.conversation_id:
            span.set_attribute("conversation.id", self.conversation_id)

        # Add user info if available
        if hasattr(self, "user_name") and self.user_name:
            span.set_attribute("conversation.user_name", self.user_name)
        if hasattr(self, "user_role") and self.user_role:
            span.set_attribute("conversation.user_role", self.user_role)

        # Add any additional attributes
        for key, value in additional_attrs.items():
            span.set_attribute(key, value)

    @contextmanager
    def create_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict = None,
        record_exceptions: bool = True,
    ):
        """
        Context manager for creating spans with automatic conversation ID correlation.

        Args:
            name: Span name
            kind: Span kind (default: INTERNAL)
            attributes: Additional attributes to set on the span
            record_exceptions: Whether to automatically record exceptions

        Yields:
            The created span

        Example:
            with open_telemetry_client.create_span("my_operation", attributes={"key": "value"}):
                # Your code here
                pass
        """
        if not self.tracer:
            self.setup_tracing()

        span = None
        try:
            with self.tracer.start_as_current_span(name, kind=kind) as span:
                # Always add conversation ID and user context
                self.add_conversation_attributes(span, **(attributes or {}))

                # Add timestamp for operations
                span.set_attribute(f"{name}.start_time", datetime.now().isoformat())

                yield span

                # Add end timestamp on successful completion
                span.set_attribute(f"{name}.end_time", datetime.now().isoformat())
                span.set_status(Status(StatusCode.OK))

        except Exception as e:
            if span and record_exceptions:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
            raise

    def flush_and_shutdown(self):
        """Force flush all spans and shutdown the tracer provider."""
        if self.provider:
            self.provider.force_flush()
            time.sleep(5)
            self.provider.shutdown()
            print("[TRACE] Flushed and shutdown tracer provider")
