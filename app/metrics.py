"""Application Prometheus metrics.

Custom business metrics that sit alongside the default HTTP metrics exposed
by `prometheus-fastapi-instrumentator` (request rate, latency, in-progress).
All counters live in the default `prometheus_client` registry, so they are
scraped from the same `/metrics` endpoint.

Grafana visualises these:
  - `oss_diagnose_total{source}`  — live vs sample(fallback) diagnoses
  - `oss_cache_total{result}`     — cache hit vs miss (→ hit-rate panel)
"""

from prometheus_client import Counter

DIAGNOSE_TOTAL = Counter(
    "oss_diagnose_total",
    "Total repository diagnoses served, by data source.",
    ["source"],  # "live" | "sample"
)

CACHE_TOTAL = Counter(
    "oss_cache_total",
    "Diagnosis cache lookups, by outcome.",
    ["result"],  # "hit" | "miss"
)
