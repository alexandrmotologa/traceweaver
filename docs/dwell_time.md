# Queue Dwell Time Analysis

Queue dwell time measures how long an asynchronous message sits in a broker, buffer, or outbox table before an active worker process begins handling it.

## Why Dwell Time Matters

In synchronous architectures, request latency equals the sum of downstream processing durations plus network transport time:

$$\text{Latency} = \sum \text{Duration}_{\text{downstream}} + \text{NetworkRTT}$$

In asynchronous, event-driven architectures, latency is dominated by queue wait states. When a service publishes an event to Kafka or a message queue, the producer span closes immediately. The consumer span begins later when a worker dequeues the record. Standard distributed tracing dashboards display these spans as disconnected operations or show empty gaps without attributing the delay.

Without dwell time visibility, developers and SREs cannot determine whether high user latency was caused by slow consumer execution or queue starvation caused by consumer lag, partition hot-spotting, or insufficient worker concurrency.

## Calculation Formula

TraceWeaver supports two methods to compute queue dwell time depending on available span attributes:

### Method 1: Producer to Consumer Gap

When a consumer span contains an OpenTelemetry `link` pointing to the producer span:

$$\text{DwellTime}_{\text{ms}} = \frac{\text{ConsumerSpan.start\_time\_ns} - \text{ProducerSpan.end\_time\_ns}}{1{,}000{,}000}$$

### Method 2: Enqueue Timestamp Attribute

When producers write messages in batches (for example, transactional outbox relays like WalPulse), individual publish spans may represent batch commits rather than single-record lifecycles. If the message payload or span attributes contain a `queue_entry_ts` (in Unix epoch milliseconds or nanoseconds):

$$\text{DwellTime}_{\text{ms}} = \text{ConsumerSpan.start\_time} - \text{queue\_entry\_ts}$$

## Visual Representation

### Terminal Waterfall (Textual)

In the terminal waterfall screen, queue dwell intervals appear between the producer and consumer spans using a yellow hatched pattern (`░░░░░`):

```
Service          Span Operation        Duration  Visual Timeline
────────────────────────────────────────────────────────────────────────────────
api-gateway      POST /checkout        120ms     [████████████]
order-service    process_order          45ms       [████]
order-service    db.outbox_insert        6ms         [█]
kafka            orders.events         280ms           ░░░░░░░░░░░░░░░░░░░░
payment-worker   charge_payment         60ms                               [██████]
```

### Web Dashboard (SVG)

In the web interface, dwell intervals are rendered as dashed amber bars with embedded wait duration tags, allowing operators to click and inspect broker partition metadata and consumer group assignments.
