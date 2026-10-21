from app.config import Settings
from app.llm.base import LLMProvider


def get_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "fake":
        from app.llm.fake import FakeProvider

        return FakeProvider(dim=settings.embed_dim)
    if settings.llm_provider == "gemini":
        from app.llm.gemini import GeminiProvider

        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Set it, or use LLM_PROVIDER=fake for a demo.")
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            chat_model=settings.gemini_chat_model,
            embed_model=settings.gemini_embed_model,
            dim=settings.embed_dim,
        )
    raise RuntimeError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
