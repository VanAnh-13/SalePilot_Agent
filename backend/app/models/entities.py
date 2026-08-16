from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# --------------------------------------------------------------------------- #
# Catalog — the real dienmayxanh dataset, transformed into normalized SQL.
# MongoDB keeps the same documents (secondary); PostgreSQL is the primary store
# the ranking engine and PostgREST both read from.
# --------------------------------------------------------------------------- #

class Category(Base):
    __tablename__ = "categories"

    code: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), index=True)
    display: Mapped[str] = mapped_column(String(128), default="")
    is_deep: Mapped[bool] = mapped_column(Boolean, default=False)
    product_count: Mapped[int] = mapped_column(Integer, default=0)


class CatalogProduct(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(32), primary_key=True)
    model_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    product_id_web: Mapped[str] = mapped_column(String(64), default="")
    name: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    category_code: Mapped[int] = mapped_column(Integer, index=True)
    category_slug: Mapped[str] = mapped_column(String(64), default="", index=True)
    category_display: Mapped[str] = mapped_column(String(128), default="")
    price_original_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_sale_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    has_current_price: Mapped[bool] = mapped_column(Boolean, default=False)
    gift_promotion: Mapped[str | None] = mapped_column(Text, nullable=True)
    outstanding: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    sold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warranty: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessories: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(128), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    online_only: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(Text, default="")
    search_text: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(64), default="")
    norm: Mapped[dict] = mapped_column(JSON, default=dict)   # parsed numeric/text specs
    specs: Mapped[dict] = mapped_column(JSON, default=dict)  # raw Vietnamese spec_product
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ProductSpec(Base):
    """Fully-normalized (EAV) view of each product's raw specs — one row per
    (sku, spec_key) — so specs are queryable in pure SQL / via PostgREST."""

    __tablename__ = "product_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(32), index=True)
    category_code: Mapped[int] = mapped_column(Integer, index=True)
    spec_key: Mapped[str] = mapped_column(String(128), index=True)
    spec_value: Mapped[str] = mapped_column(Text, default="")


class KbDoc(Base):
    """Policy / FAQ knowledge base chunks (bảo hành, giao hàng, khui hộp Apple...)."""

    __tablename__ = "kb_docs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    topic: Mapped[str] = mapped_column(String(64), default="", index=True)
    question: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(128), default="")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    channel: Mapped[str] = mapped_column(String(32), default="web")
    external_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    interest: Mapped[str] = mapped_column(Text, default="")
    budget_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String(32), default="web", index=True)
    external_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    customer_name: Mapped[str] = mapped_column(String(128), default="Khách")
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(Integer, index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrderDraft(Base):
    __tablename__ = "order_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items_json: Mapped[str] = mapped_column(Text, default="[]")
    total_vnd: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String(32), default="zalo")
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    direction: Mapped[str] = mapped_column(String(16), default="outbound")
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CustomerMemory(Base):
    __tablename__ = "customer_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String(32), default="web", index=True)
    external_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    profile_json: Mapped[str] = mapped_column(Text, default="{}")
    summary: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(64), default="follow_up")
    channel: Mapped[str] = mapped_column(String(32), default="web")
    external_id: Mapped[str] = mapped_column(String(128), default="")
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    result: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    channel: Mapped[str] = mapped_column(String(32), default="web")
    external_id: Mapped[str] = mapped_column(String(128), default="")
    conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_text: Mapped[str] = mapped_column(Text, default="")
    reply: Mapped[str] = mapped_column(Text, default="")
    trace_json: Mapped[str] = mapped_column(Text, default="[]")
    agents_json: Mapped[str] = mapped_column(Text, default="[]")
    tools_json: Mapped[str] = mapped_column(Text, default="[]")
    memory_json: Mapped[str] = mapped_column(Text, default="{}")
    skills_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
