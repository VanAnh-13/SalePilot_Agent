from langchain_core.language_models.chat_models import BaseChatModel

from app.config import get_settings


def has_llm_key() -> bool:
    s = get_settings()
    provider = s.llm_provider.lower()
    if provider == "anthropic":
        return bool(s.anthropic_api_key)
    return bool(s.openai_api_key)


def get_chat_model() -> BaseChatModel:
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not settings.anthropic_api_key:
            return _FallbackModel()
        return ChatAnthropic(
            model=settings.model_name if "claude" in settings.model_name else "claude-3-5-haiku-latest",
            api_key=settings.anthropic_api_key,
            temperature=0.3,
        )

    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        return _FallbackModel()
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )


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
