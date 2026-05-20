from prometheus_client import Counter, Gauge

notification_delivery_total = Counter(
    "mstechnics_notification_delivery_total",
    "Notification delivery attempts by channel and result.",
    ["channel", "status"],
)

notification_all_channels_failed_total = Counter(
    "mstechnics_notification_all_channels_failed_total",
    "Notifications that failed across every configured fallback channel.",
)

sse_connections_active = Gauge(
    "mstechnics_sse_connections_active",
    "Currently active SSE client connections.",
)
