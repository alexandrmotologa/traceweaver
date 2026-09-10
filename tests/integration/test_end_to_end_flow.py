"""Integration test for full end-to-end distributed tracing flow."""

import pytest
from httpx import ASGITransport, AsyncClient

from traceweaver.demo import generate_demo_trace
from traceweaver.engine.store import TraceStore
from traceweaver.web.server import create_app


@pytest.mark.asyncio
async def test_full_trace_ingestion_and_causal_correlation():
    """Verify end-to-end ingestion, causal graph assembly, dwell time, and analytics."""
    store = TraceStore(db_path=":memory:")
    app = create_app(store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Generate and ingest 10 multi-service traces (50 total spans)
        emitted_traces = []
        for i in range(1, 11):
            has_error = i == 4 or i == 8
            spans = generate_demo_trace(trace_idx=i, base_dwell_ms=300.0, inject_error=has_error)
            emitted_traces.append(spans[0].trace_id)

            payload = {
                "resourceSpans": [
                    {
                        "resource": {
                            "attributes": [
                                {"key": "service.name", "value": {"stringValue": s.service_name}}
                            ]
                        },
                        "scopeSpans": [
                            {
                                "spans": [
                                    {
                                        "traceId": s.trace_id,
                                        "spanId": s.span_id,
                                        "parentSpanId": s.parent_span_id,
                                        "name": s.name,
                                        "startTimeUnixNano": str(s.start_time_ns),
                                        "endTimeUnixNano": str(s.end_time_ns),
                                        "status": {"code": 2 if s.status_code == "ERROR" else 1},
                                        "attributes": [
                                            {"key": k, "value": {"stringValue": str(v)}}
                                            for k, v in s.attributes.items()
                                        ],
                                        "links": [
                                            {
                                                "traceId": lk.trace_id,
                                                "spanId": lk.span_id,
                                                "attributes": [
                                                    {"key": k, "value": {"stringValue": str(v)}}
                                                    for k, v in lk.attributes.items()
                                                ],
                                            }
                                            for lk in s.links
                                        ],
                                    }
                                ]
                            }
                        ],
                    }
                    for s in spans
                ]
            }

            res = await client.post("/v1/traces", json=payload)
            assert res.status_code == 200

        # Step 2: Verify total stored spans in DuckDB
        health_res = await client.get("/healthz")
        assert health_res.status_code == 200
        assert health_res.json()["total_spans"] == 50

        # Step 3: List traces
        traces_res = await client.get("/api/v1/traces?limit=50")
        assert traces_res.status_code == 200
        traces_data = traces_res.json()
        assert len(traces_data) == 10

        # Step 4: Filter error traces
        error_res = await client.get("/api/v1/traces?error_only=true")
        assert error_res.status_code == 200
        err_traces = error_res.json()
        assert len(err_traces) == 2

        # Step 5: Test Causal DAG reconstruction on the first trace
        target_trace_id = emitted_traces[0]
        dag_res = await client.get(f"/api/v1/traces/{target_trace_id}")
        assert dag_res.status_code == 200
        dag = dag_res.json()

        assert dag["trace_id"] == target_trace_id
        assert dag["span_count"] == 5
        assert dag["total_dwell_time_ms"] > 200.0  # Asynchronous Kafka queue wait time
        assert len(dag["critical_path_span_ids"]) == 5
        assert len(dag["root_nodes"]) == 1

        root = dag["root_nodes"][0]
        assert root["span"]["service_name"] == "idemgate"
        assert len(root["children"]) == 1

        order_node = root["children"][0]
        assert order_node["span"]["service_name"] == "order-engine"

        # Check that walpulse has payment-worker stitched as a child across Kafka link
        cdc_node = order_node["children"][0]["children"][0]
        assert cdc_node["span"]["service_name"] == "walpulse"
        assert len(cdc_node["children"]) == 1

        consumer_node = cdc_node["children"][0]
        assert consumer_node["span"]["service_name"] == "payment-worker"
        assert len(consumer_node["dwell_intervals"]) == 1
        dwell_item = consumer_node["dwell_intervals"][0]
        assert dwell_item["queue_name"] == "orders.events"
        assert dwell_item["dwell_time_ms"] > 200.0

        # Step 6: Verify Service Analytics
        analytics_res = await client.get("/api/v1/analytics/services")
        assert analytics_res.status_code == 200
        services = analytics_res.json()
        service_names = {s["service_name"] for s in services}
        assert "idemgate" in service_names
        assert "order-engine" in service_names
        assert "walpulse" in service_names
        assert "payment-worker" in service_names

    store.close()
