from app.agent.tools.catalog import compare_products, get_product_detail, recommend_top3, search_products
from app.agent.tools.crm import create_lead, escalate_to_human, schedule_followup, update_lead_status
from app.agent.tools.knowledge import search_knowledge
from app.agent.tools.order import create_order_draft

ALL_TOOLS = [
    search_products,
    get_product_detail,
    compare_products,
    recommend_top3,
    search_knowledge,
    create_lead,
    update_lead_status,
    create_order_draft,
    schedule_followup,
    escalate_to_human,
]

__all__ = ["ALL_TOOLS"]
