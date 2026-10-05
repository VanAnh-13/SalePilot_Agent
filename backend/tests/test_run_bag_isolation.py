from __future__ import annotations

import asyncio
import unittest

from app.agent.run_bag import bag_trace, get_run_bag, reset_run_bag


class RunBagIsolationTests(unittest.TestCase):
    def test_context_isolation(self):
        async def worker(tag: str) -> list[str]:
            reset_run_bag()
            bag_trace("lead", "start", tag)
            await asyncio.sleep(0.01)
            bag_trace("lead", "end", tag)
            return [x.get("detail") for x in get_run_bag()["trace"]]

        async def main():
            a, b = await asyncio.gather(worker("A"), worker("B"))
            self.assertEqual(a, ["A", "A"])
            self.assertEqual(b, ["B", "B"])

        asyncio.run(main())


if __name__ == "__main__":
    raise SystemExit(unittest.main())
