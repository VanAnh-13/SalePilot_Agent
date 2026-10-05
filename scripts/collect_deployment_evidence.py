#!/usr/bin/env python3
"""Deployment evidence collector for RIVF Track 2.

Usage:
  python scripts/collect_deployment_evidence.py --url https://optivisionlab.fit-haui.edu.vn
  python scripts/collect_deployment_evidence.py --url http://127.0.0.1:8000 --frontend-url https://sale-pilot-agent.vercel.app
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _http_request(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    timeout: int = 30,
    expect_json: bool = True,
) -> tuple[int, object, float]:
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            latency = (time.perf_counter() - t0) * 1000
            if not expect_json:
                return resp.status, raw.decode("utf-8", errors="replace")[:2000], latency
            try:
                body = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                body = {"raw": raw.decode("utf-8", errors="replace")[:500]}
            return resp.status, body, latency
    except urllib.error.HTTPError as exc:
        latency = (time.perf_counter() - t0) * 1000
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            body = {"error": str(exc)}
        return exc.code, body, latency
    except Exception as exc:  # noqa: BLE001
        latency = (time.perf_counter() - t0) * 1000
        return 0, {"error": str(exc)}, latency


def health_check(base_url: str) -> dict:
    status, body, latency = _http_request(f"{base_url}/health")
    catalog = body.get("catalog") if isinstance(body, dict) else None
    return {
        "endpoint": "/health",
        "status_code": status,
        "latency_ms": round(latency, 2),
        "catalog_source": catalog.get("source") if isinstance(catalog, dict) else None,
        "catalog_products": catalog.get("products") if isinstance(catalog, dict) else None,
        "catalog_categories": catalog.get("categories") if isinstance(catalog, dict) else None,
        "response": body if isinstance(body, dict) else {"raw": str(body)[:300]},
    }


def chat_latency_test(base_url: str, n_requests: int = 10) -> dict:
    latencies: list[float] = []
    errors = 0
    decision_count = 0
    for i in range(n_requests):
        query = {
            "message": "Gia đình 4 người cần tủ lạnh dưới 15 triệu",
            "external_id": f"bench-{i}",
            "channel": "web",
        }
        data = json.dumps(query).encode("utf-8")
        status, body, latency = _http_request(f"{base_url}/chat", method="POST", data=data, timeout=60)
        if status == 200:
            latencies.append(latency)
            if isinstance(body, dict) and body.get("decision"):
                decision_count += 1
        else:
            errors += 1
        print(f"  Chat [{i+1}/{n_requests}]: {status} {latency:.0f}ms")

    if not latencies:
        return {"endpoint": "/chat", "error": "all requests failed", "errors": errors, "requests": n_requests}

    ordered = sorted(latencies)
    p95_idx = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95)))
    p99_idx = min(len(ordered) - 1, max(0, int(len(ordered) * 0.99)))
    return {
        "endpoint": "/chat",
        "requests": n_requests,
        "successful": len(latencies),
        "errors": errors,
        "decision_present_count": decision_count,
        "p50_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(ordered[p95_idx], 2),
        "p99_ms": round(ordered[p99_idx], 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "stdev_ms": round(statistics.stdev(latencies), 2) if len(latencies) >= 2 else 0.0,
    }


def products_api_test(base_url: str) -> dict:
    results: dict = {}
    status, body, latency = _http_request(f"{base_url}/products/categories")
    results["categories"] = {
        "endpoint": "/products/categories",
        "status_code": status,
        "latency_ms": round(latency, 2),
        "count": len(body) if isinstance(body, list) else (
            len(body.get("items") or []) if isinstance(body, dict) else None
        ),
    }
    status, body, latency = _http_request(f"{base_url}/products?page=1&size=10")
    results["products_page1"] = {
        "endpoint": "/products?page=1&size=10",
        "status_code": status,
        "latency_ms": round(latency, 2),
        "items_returned": len(body.get("items", [])) if isinstance(body, dict) else None,
    }
    return results


def offline_fallback_test(base_url: str) -> dict:
    query = {
        "message": "tủ lạnh dưới 10 triệu",
        "external_id": "offline-test",
        "channel": "web",
    }
    data = json.dumps(query).encode("utf-8")
    status, body, latency = _http_request(f"{base_url}/chat", method="POST", data=data, timeout=60)
    return {
        "endpoint": "/chat (offline-capable path)",
        "status_code": status,
        "latency_ms": round(latency, 2),
        "has_reply": bool(body.get("reply")) if isinstance(body, dict) else False,
        "has_decision": bool(body.get("decision")) if isinstance(body, dict) else False,
        "used_agents": body.get("used_agents") if isinstance(body, dict) else None,
    }


def frontend_check(frontend_url: str) -> dict:
    status, body, latency = _http_request(frontend_url, expect_json=False, timeout=30)
    text = body if isinstance(body, str) else str(body)
    return {
        "url": frontend_url,
        "status_code": status,
        "latency_ms": round(latency, 2),
        "looks_like_salepilot": ("SalePilot" in text) or ("salepilot" in text.casefold()),
        "snippet": text[:240].replace("\n", " "),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--frontend-url", default=None, help="Optional public frontend URL")
    parser.add_argument("--chat-requests", type=int, default=10)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--allow-unhealthy",
        action="store_true",
        help="Exit 0 even if /health is not 200 (still writes evidence JSON)",
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    output_path = (
        Path(args.output)
        if args.output
        else ROOT / "experiments" / "results" / "deployment_evidence.json"
    )

    print(f"Collecting deployment evidence from {base_url}")
    evidence = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "target_url": base_url,
        "frontend_url": args.frontend_url,
        "claim_class": "public" if base_url.startswith("https://") else "local",
        "tests": {},
    }

    print("\n1. Health check...")
    evidence["tests"]["health"] = health_check(base_url)
    print(f"   Status: {evidence['tests']['health']['status_code']}")

    healthy = evidence["tests"]["health"]["status_code"] == 200
    if healthy:
        print(f"\n2. Chat latency ({args.chat_requests} requests)...")
        evidence["tests"]["chat_latency"] = chat_latency_test(base_url, args.chat_requests)
        print("\n3. Products API...")
        evidence["tests"]["products_api"] = products_api_test(base_url)
        print("\n4. Offline-capable chat...")
        evidence["tests"]["offline_fallback"] = offline_fallback_test(base_url)
    else:
        evidence["tests"]["chat_latency"] = {"skipped": True, "reason": "health not 200"}
        evidence["tests"]["products_api"] = {"skipped": True, "reason": "health not 200"}
        evidence["tests"]["offline_fallback"] = {"skipped": True, "reason": "health not 200"}
        print("   Skipping chat/products tests because health failed")

    if args.frontend_url:
        print("\n5. Frontend check...")
        evidence["tests"]["frontend"] = frontend_check(args.frontend_url.rstrip("/"))
        print(
            f"   Status: {evidence['tests']['frontend']['status_code']} "
            f"salepilot={evidence['tests']['frontend']['looks_like_salepilot']}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nEvidence saved to {output_path}")

    if not healthy:
        print("\nHealth check failed — backend may be down (see DEPLOYMENT_HANDOFF.md)")
        return 0 if args.allow_unhealthy else 1

    print("\nDeployment evidence collected successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
