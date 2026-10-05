"""Shared agent constants.

Cross-cutting literals used by more than one agent module. This module sits
at the bottom of the agent dependency graph: it imports nothing but `re`, so
every other module can import it without creating a cycle. Prefer putting a
value here only when it is genuinely shared by two or more modules; single-file
limits stay as module-level constants next to their owner.
"""

import re

# Vietnamese mobile number matcher (also used for memory extraction). Single
# source of truth — previously duplicated in `intent.py` and `memory/store.py`.
PHONE_RE = re.compile(r"(?<!\d)0\d{8,10}(?!\d)")

# Lead scoring / status business rules (shared across graph fast-path, offline
# route, CRM tool, and the leads service).
LEAD_SCORE_BASE = 0.5
LEAD_SCORE_QUALIFIED = 0.6
LEAD_STATUS_QUALIFIED = "qualified"

# Fields carried from a recommendation into the phrase-LLM payload.
RECOMMEND_PHRASE_FIELDS = ("name", "sku", "price_display", "why", "gift_promotion")

# LangGraph recursion cap for the lead/tools loop.
GRAPH_RECURSION_LIMIT = 24

# Sub-agent names the lead model may delegate to (mirrors the SUBAGENTS registry).
LEAD_SUBAGENTS = ("catalog", "knowledge", "crm", "order", "escalation")

# Text-truncation caps for trace detail and delegated-task briefs.
DELEGATE_TASK_CAP = 120
TRACE_DETAIL_CAP = 200
