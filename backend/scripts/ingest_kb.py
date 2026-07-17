import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag.store import ingest_kb


def main() -> None:
    result = ingest_kb()
    print("ingest_kb:", result)


if __name__ == "__main__":
    main()
