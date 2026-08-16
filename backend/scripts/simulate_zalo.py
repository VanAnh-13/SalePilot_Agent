"""Simulate a Zalo OA webhook message against local backend."""

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--text",
        default="Gia đình 4 người cần tủ lạnh dưới 15 triệu, ngang tối đa 70 cm",
    )
    parser.add_argument("--user-id", default="zalo-demo-001")
    parser.add_argument("--url", default="http://127.0.0.1:8000/webhooks/zalo")
    parser.add_argument(
        "--secret",
        default=os.environ.get("ZALO_OA_SECRET", ""),
        help="Zalo OA secret for HMAC signing (or set ZALO_OA_SECRET env var)",
    )
    args = parser.parse_args()

    payload = {
        "event_name": "user_send_text",
        "sender": {"id": args.user_id},
        "recipient": {"id": "oa-salepilot"},
        "message": {"text": args.text, "msg_id": f"sim-{int(time.time())}"},
        "timestamp": str(int(time.time() * 1000)),
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if args.secret:
        signature = hmac.new(
            args.secret.encode(), data, hashlib.sha256
        ).hexdigest()
        headers["X-Zalo-Signature"] = f"sha256={signature}"
        print(f"Signing with HMAC (secret length={len(args.secret)})")
    else:
        print(
            "WARNING: No --secret or ZALO_OA_SECRET set. "
            "Request will fail if webhook uses strict verification (default)."
        )

    req = urllib.request.Request(
        args.url,
        data=data,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
        print(body)


if __name__ == "__main__":
    main()
