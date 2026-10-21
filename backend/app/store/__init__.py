from app.config import Settings
from app.store.base import Store


def get_store(settings: Settings) -> Store:
    if settings.database_url:
        from app.store.pgvector import PgVectorStore

        return PgVectorStore(settings.database_url, dim=settings.embed_dim)
    from app.store.memory import MemoryStore

    return MemoryStore()
