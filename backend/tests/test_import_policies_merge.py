"""Policy import merge behavior: curated FAQ entries survive re-import."""

from __future__ import annotations

import unittest

from scripts.import_policies import merge_entries

CURATED = {
    "id": "faq-gio-mo-cua",
    "question": "Cửa hàng mở cửa lúc mấy giờ?",
    "answer": "8:00–21:00 hằng ngày.",
    "topic": "faq",
}
OLD_POLICY = {
    "id": "bao_hanh_doi_tra-01",
    "question": "Chính sách bảo hành & đổi trả — cũ",
    "answer": "Bản cũ sẽ bị thay thế.",
    "topic": "bao_hanh_doi_tra",
}
NEW_POLICY = {
    "id": "bao_hanh_doi_tra-01",
    "question": "Chính sách bảo hành & đổi trả — mới",
    "answer": "Bản mới.",
    "topic": "bao_hanh_doi_tra",
}


class MergeEntriesTests(unittest.TestCase):
    def test_merge_keeps_curated_and_replaces_policy_entries(self):
        merged = merge_entries([CURATED, OLD_POLICY], [NEW_POLICY])
        ids = [e["id"] for e in merged]
        self.assertIn("faq-gio-mo-cua", ids)
        self.assertEqual(ids.count("bao_hanh_doi_tra-01"), 1)
        by_id = {e["id"]: e for e in merged}
        self.assertEqual(by_id["bao_hanh_doi_tra-01"]["question"], NEW_POLICY["question"])

    def test_merge_with_empty_existing_returns_policies_only(self):
        merged = merge_entries([], [NEW_POLICY])
        self.assertEqual([e["id"] for e in merged], ["bao_hanh_doi_tra-01"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
