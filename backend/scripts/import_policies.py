"""Ingest Điện Máy Xanh policy documents into the knowledge base.

The real policy files (bảo hành/đổi trả, giao hàng/lắp đặt, khui hộp Apple,
xử lý dữ liệu cá nhân, điều khoản sử dụng, nội quy cửa hàng, cam kết phục vụ)
are plain-text. This script chunks each doc into retrieval-sized passages,
writes them to ``data/faq.json`` (the file the lexical ``search_faq`` reads), and
copies the raw docs into ``data/policies/`` so the knowledge base is
self-contained inside the repo/container.

Usage (from backend/):
    python -m scripts.import_policies --src /path/to/dmx_docs

Environment variables (used when --src is not passed):
    DMX_SRC_DIR  Path to the directory containing policy .md files
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from app.rag.chunker import SmartChunker
from scripts.shared import resolve_dmx_src

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# filename stem -> (human title, kb topic tag). Order controls entry ids.
POLICY_DOCS: dict[str, tuple[str, str]] = {
    "chinh_sach_bao_hanh_doi_tra": ("Chính sách bảo hành & đổi trả", "bao_hanh_doi_tra"),
    "chinh_sach_giao_hang_lap_dat": ("Chính sách giao hàng & lắp đặt", "giao_hang_lap_dat"),
    "chinh_sach_khui_hop_apple": ("Chính sách khui hộp sản phẩm Apple", "khui_hop_apple"),
    "chinh_sach_xu_ly_du_lieu_ca_nhan": ("Chính sách xử lý dữ liệu cá nhân", "du_lieu_ca_nhan"),
    "dieu-khoang-su-dung": ("Điều khoản sử dụng", "dieu_khoan"),
    "noi_quy_cua_hang": ("Nội quy cửa hàng", "noi_quy"),
    "chat_luong_phuc_vu": ("Cam kết chất lượng phục vụ", "phuc_vu"),
}


_chunker = SmartChunker(max_chars=800, min_chars=80)


def build_entries(src: Path) -> list[dict]:
    entries: list[dict] = []
    policies_dir = DATA_DIR / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)

    for stem, (title, topic) in POLICY_DOCS.items():
        path = src / f"{stem}.md"
        if not path.exists():
            print(f"  ! missing {path.name}, skipped")
            continue
        shutil.copyfile(path, policies_dir / path.name)
        text = path.read_text(encoding="utf-8")
        chunks = _chunker.chunk(text)
        for chunk in chunks:
            entries.append(
                {
                    "id": f"{topic}-{chunk.index + 1:02d}",
                    "question": f"{title} — {chunk.heading}",
                    "answer": chunk.text[:1400],
                    "topic": topic,
                    "source": f"policies/{path.name}",
                    **chunk.metadata.to_dict(),
                }
            )
        print(f"  + {title}: {len(chunks)} chunks")
    return entries


def merge_entries(existing: list[dict], policy_entries: list[dict]) -> list[dict]:
    """Replace policy entries in place, keep every curated (non-policy) entry.

    An entry is a policy entry when its id starts with one of the POLICY_DOCS
    topics — those ids are generated above, so hand-curated FAQ entries that
    use any other id survive a re-import.
    """
    policy_prefixes = tuple(f"{topic}-" for _, topic in POLICY_DOCS.values())
    curated = [e for e in existing if not str(e.get("id", "")).startswith(policy_prefixes)]
    kept = len(curated)
    if kept:
        print(f"  = kept {kept} curated (non-policy) entries")
    return curated + policy_entries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest DMX policy .md files into the knowledge base.",
        epilog="Source resolution: --src flag > DMX_SRC_DIR in .env > error",
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=None,
        help="Directory containing policy .md files. Falls back to DMX_SRC_DIR in .env.",
    )
    parser.add_argument("--out", type=Path, default=DATA_DIR / "faq.json")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Overwrite the whole output file (old behavior). Default merges: curated non-policy entries are kept.",
    )
    args = parser.parse_args()

    src = resolve_dmx_src(args.src)

    print(f"Ingesting policies from {src} ...")
    entries = build_entries(src)
    if not entries:
        raise SystemExit("No policy chunks produced.")

    if not args.replace and args.out.exists():
        try:
            existing = json.loads(args.out.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                entries = merge_entries(existing, entries)
        except json.JSONDecodeError:
            print("  ! existing output is not valid JSON, writing fresh file")

    args.out.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {len(entries)} KB entries -> {args.out}")
    print(f"Raw docs copied -> {DATA_DIR / 'policies'}")


if __name__ == "__main__":
    main()
