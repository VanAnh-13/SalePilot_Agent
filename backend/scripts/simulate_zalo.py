"""Simulate a Zalo OA webhook message against local backend."""

import argparse
import json
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
    args = parser.parse_args()

    payload = {
        "event_name": "user_send_text",
        "sender": {"id": args.user_id},
        "recipient": {"id": "oa-salepilot"},
        "message": {"text": args.text, "msg_id": f"sim-{int(time.time())}"},
        "timestamp": str(int(time.time() * 1000)),
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        args.url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
        print(body)


if __name__ == "__main__":
    main()
