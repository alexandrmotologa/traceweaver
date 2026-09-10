"""OTLP gRPC Receiver implementation on port 4317."""

import logging
from collections.abc import Callable

import grpc
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceServicer,
    add_TraceServiceServicer_to_server,
)

from traceweaver.engine.store import TraceStore
from traceweaver.receiver.span_normalizer import NormalizedSpan, parse_otlp_protobuf

logger = logging.getLogger(__name__)


class TraceServiceImpl(TraceServiceServicer):
    """gRPC service implementation handling Export calls from OpenTelemetry SDKs."""

    def __init__(
        self,
        store: TraceStore,
        broadcast_callback: Callable[[list[NormalizedSpan]], None] | None = None,
    ):
        self.store = store
        self.broadcast_callback = broadcast_callback

    async def Export(
        self,
        request: ExportTraceServiceRequest,
        context: grpc.aio.ServicerContext,
    ) -> ExportTraceServiceResponse:
        """Process incoming OTLP export request."""
        try:
            raw_bytes = request.SerializeToString()
            spans = parse_otlp_protobuf(raw_bytes)
            if spans:
                self.store.insert_spans(spans)
                if self.broadcast_callback:
                    try:
                        self.broadcast_callback(spans)
                    except Exception as err:
                        logger.warning("Error in span broadcast callback: %s", err)
        except Exception as err:
            logger.error("Failed to process gRPC trace export: %s", err)
            await context.abort(grpc.StatusCode.INTERNAL, f"Internal error parsing traces: {err}")

        return ExportTraceServiceResponse()


async def start_grpc_server(
    store: TraceStore,
    host: str = "0.0.0.0",
    port: int = 4317,
    broadcast_callback: Callable[[list[NormalizedSpan]], None] | None = None,
) -> grpc.aio.Server:
    """Initialize and start asynchronous gRPC server."""
    server = grpc.aio.server()
    servicer = TraceServiceImpl(store, broadcast_callback=broadcast_callback)
    add_TraceServiceServicer_to_server(servicer, server)
    listen_addr = f"{host}:{port}"
    server.add_insecure_port(listen_addr)
    await server.start()
    logger.info("OTLP gRPC receiver listening on %s", listen_addr)
    return server
