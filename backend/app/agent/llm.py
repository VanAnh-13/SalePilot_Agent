import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.config import get_settings

logger = logging.getLogger(__name__)

# Sensible current defaults used only when MODEL_NAME doesn't match the resolved
# provider (e.g. LLM_PROVIDER=anthropic but MODEL_NAME left as an OpenAI id).
_DEFAULT_MODEL = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5",  # current, valid; set MODEL_NAME=claude-sonnet-5/claude-opus-4-8 for higher quality
}


def _resolve_provider() -> str:
    """Pick the active LLM provider.

    Honors LLM_PROVIDER when that provider's key is present; otherwise falls back
    to whichever key IS configured. This makes the service multi-provider: set
    both keys and switch with LLM_PROVIDER, and it still works if only one key
    is filled in regardless of LLM_PROVIDER.
    """
    s = get_settings()
    provider = (s.llm_provider or "").lower().strip()
    has_openai = bool(s.openai_api_key)
    has_anthropic = bool(s.anthropic_api_key)
    if provider == "anthropic" and has_anthropic:
        return "anthropic"
    if provider == "openai" and has_openai:
        return "openai"
    if has_anthropic:
        return "anthropic"
    if has_openai:
        return "openai"
    return provider or "openai"


def has_llm_key() -> bool:
    """True if ANY provider key is configured (LLM path); else offline advisor."""
    s = get_settings()
    return bool(s.openai_api_key or s.anthropic_api_key)


def _pick_model(provider: str, model_name: str) -> str:
    """Use MODEL_NAME if it matches the provider, else the provider default."""
    name = (model_name or "").strip()
    is_claude = name.lower().startswith("claude")
    if provider == "anthropic":
        return name if is_claude else _DEFAULT_MODEL["anthropic"]
    return name if (name and not is_claude) else _DEFAULT_MODEL["openai"]


def _build_provider_model(provider: str) -> BaseChatModel:
    """Construct one provider's model, or the offline _FallbackModel."""
    settings = get_settings()

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            return _FallbackModel()
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=_pick_model("anthropic", settings.model_name),
            api_key=settings.anthropic_api_key,
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
        )

    if not settings.openai_api_key:
        return _FallbackModel()
    from langchain_openai import ChatOpenAI

    # Tight timeout + bounded retries (LLM_MAX_RETRIES): transient 429/5xx get
    # retried, but a genuinely dead endpoint still fails fast into the friendly
    # fallback instead of hanging the chat. max_tokens caps reply length — chat
    # answers don't need essays and slow endpoints charge wall-clock per token.
    kwargs: dict = {
        "api_key": settings.openai_api_key,
        "temperature": 0.3,
        "max_tokens": settings.llm_max_tokens,
        "timeout": settings.llm_timeout_s,
        "max_retries": settings.llm_max_retries,
    }
    if settings.openai_base_url:
        # OpenAI-compatible endpoint: trust MODEL_NAME verbatim (provider-specific
        # ids like "llama-3.3-70b", "deepseek-chat", "anthropic/claude-sonnet-5").
        kwargs["base_url"] = settings.openai_base_url
        kwargs["model"] = (settings.model_name or "").strip() or _DEFAULT_MODEL["openai"]
    else:
        kwargs["model"] = _pick_model("openai", settings.model_name)
    return ChatOpenAI(**kwargs)


class _FailoverModel(BaseChatModel):
    """Try the primary provider; on a hard failure, use the secondary.

    Each inner model already retries transient errors at the SDK level, so
    this wrapper only catches exhausted failures.
    """

    primary: BaseChatModel
    secondary: BaseChatModel

    @property
    def _llm_type(self) -> str:
        return "failover"

    def bind_tools(self, tools, **kwargs):
        return _FailoverModel(
            primary=self.primary.bind_tools(tools, **kwargs),
            secondary=self.secondary.bind_tools(tools, **kwargs),
        )

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        try:
            ai = self.primary.invoke(messages, stop=stop)
        except Exception:
            logger.warning("primary LLM failed, failing over", exc_info=True)
            ai = self.secondary.invoke(messages, stop=stop)
        return ChatResult(generations=[ChatGeneration(message=ai)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        try:
            ai = await self.primary.ainvoke(messages, stop=stop)
        except Exception:
            logger.warning("primary LLM failed, failing over", exc_info=True)
            ai = await self.secondary.ainvoke(messages, stop=stop)
        return ChatResult(generations=[ChatGeneration(message=ai)])


def get_chat_model() -> BaseChatModel:
    provider = _resolve_provider()
    other = "anthropic" if provider == "openai" else "openai"
    primary = _build_provider_model(provider)
    secondary = _build_provider_model(other)
    if isinstance(primary, _FallbackModel):
        return secondary
    if isinstance(secondary, _FallbackModel):
        return primary
    return _FailoverModel(primary=primary, secondary=secondary)


class _FallbackModel(BaseChatModel):
    """Offline replies when no API key — does not support bind_tools."""

    @property
    def _llm_type(self) -> str:
        return "salepilot-fallback"

    def bind_tools(self, tools, **kwargs):
        # Allow graph construction; tools ignored — offline path bypasses this model.
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult

        last = ""
        for m in reversed(messages):
            content = getattr(m, "content", "") or ""
            if content and getattr(m, "type", "") == "human":
                last = content if isinstance(content, str) else str(content)
                break
        text = self._reply(last)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    def _reply(self, text: str) -> str:
        t = (text or "").lower()
        if any(k in t for k in ("tủ lạnh", "tu lanh", "dung tích", "dung tich", "giá", "gia")):
            return (
                "Chào bạn! Em là SalePilot Điện Máy. "
                "Nhà mình có bao nhiêu người và ngân sách khoảng bao nhiêu để em gợi ý tủ lạnh phù hợp ạ?"
            )
        if any(k in t for k in ("giao", "ship", "đổi", "trả", "bảo hành", "bao hanh")):
            return (
                "Shop giao nội thành HN/HCM 1–3 ngày (free đơn từ 5tr), đổi trả 7 ngày nếu lỗi NSX, "
                "bảo hành 12–24 tháng tùy SP."
            )
        if any(k in t for k in ("người", "tư vấn viên", "nhân viên", "gặp")):
            return "Em đã ghi nhận yêu cầu gặp tư vấn viên. Team sẽ liên hệ trong giờ 9:00–21:00 ạ."
        return (
            "Xin chào! Em là SalePilot — trợ lý multi-agent tư vấn tủ lạnh. "
            "Em hỗ trợ so sánh dung tích, kích thước, giá và công nghệ bảo quản. Bạn cần gì ạ?"
        )
