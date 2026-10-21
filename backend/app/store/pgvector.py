"""Postgres + pgvector store. Persistent, and works with Supabase's free tier."""

import json
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from app.models import Chunk, GapItem, SourceDoc

MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "001_init.sql"


class PgVectorStore:
    persistent = True

    def __init__(self, database_url: str, dim: int) -> None:
        self.database_url = database_url
        self.dim = dim
        self._migrate()

    def _connect(self) -> psycopg.Connection:
        # prepare_threshold=None keeps this compatible with Supabase's connection pooler.
        conn = psycopg.connect(self.database_url, row_factory=dict_row, prepare_threshold=None)
        register_vector(conn)
        return conn

    def _migrate(self) -> None:
        sql = MIGRATION.read_text().replace(":dim", str(int(self.dim)))
        with psycopg.connect(self.database_url, prepare_threshold=None) as conn:
            conn.execute(sql)

    @staticmethod
    def _row_to_chunk(row: dict) -> Chunk:
        return Chunk(
            chunk_id=row["chunk_id"],
            doc_id=row["doc_id"],
            doc_title=row["title"],
            section=row["section"],
            text=row["content"],
            position=row["position"],
        )

    # Documents ---------------------------------------------------------------

    def replace_document(self, doc_id: str, title: str, source: str, chunks: list[Chunk]) -> None:
        with self._connect() as conn, conn.transaction():
            conn.execute(
                """insert into documents (doc_id, title, source) values (%s, %s, %s)
                   on conflict (doc_id) do update
                   set title = excluded.title, source = excluded.source, updated_at = now()""",
                (doc_id, title, source),
            )
            conn.execute("delete from chunks where doc_id = %s", (doc_id,))
            with conn.cursor() as cur:
                cur.executemany(
                    """insert into chunks (chunk_id, doc_id, section, content, position, embedding)
                       values (%s, %s, %s, %s, %s, %s)""",
                    [(c.chunk_id, doc_id, c.section, c.text, c.position, c.embedding) for c in chunks],
                )

    def delete_document(self, doc_id: str) -> bool:
        with self._connect() as conn:
            result = conn.execute("delete from documents where doc_id = %s", (doc_id,))
            return result.rowcount > 0

    def list_sources(self) -> list[SourceDoc]:
        with self._connect() as conn:
            rows = conn.execute(
                """select d.doc_id, d.title, count(c.chunk_id) as chunks
                   from documents d left join chunks c using (doc_id)
                   group by d.doc_id, d.title order by d.title"""
            ).fetchall()
        return [SourceDoc(**row) for row in rows]

    def chunk_count(self) -> int:
        with self._connect() as conn:
            return conn.execute("select count(*) as n from chunks").fetchone()["n"]

    # Search ------------------------------------------------------------------

    def vector_search(self, query_vector: list[float], k: int) -> list[tuple[Chunk, float]]:
        with self._connect() as conn:
            rows = conn.execute(
                """select c.chunk_id, c.doc_id, d.title, c.section, c.content, c.position,
                          1 - (c.embedding <=> %s::vector) as similarity
                   from chunks c join documents d using (doc_id)
                   order by c.embedding <=> %s::vector
                   limit %s""",
                (query_vector, query_vector, k),
            ).fetchall()
        return [(self._row_to_chunk(r), float(r["similarity"])) for r in rows]

    def keyword_search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        # websearch_to_tsquery ANDs every word, which is too strict for questions,
        # so the question's stemmed words are ORed together instead. Each word is
        # quoted so characters like '@' or ':' can't break the query syntax.
        with self._connect() as conn:
            rows = conn.execute(
                """with q as (
                       select to_tsquery('simple', string_agg(quote_literal(lexeme), ' | ')) as query
                       from unnest(to_tsvector('english', %s)) as t(lexeme)
                   )
                   select c.chunk_id, c.doc_id, d.title, c.section, c.content, c.position,
                          ts_rank_cd(c.tsv, q.query) as rank
                   from chunks c join documents d using (doc_id), q
                   where q.query is not null and c.tsv @@ q.query
                   order by rank desc
                   limit %s""",
                (query, k),
            ).fetchall()
        return [(self._row_to_chunk(r), float(r["rank"])) for r in rows]

    # Gaps, feedback, eval -----------------------------------------------------

    def log_gap(self, question: str, top_similarity: float, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into gaps (question, top_similarity, reason) values (%s, %s, %s)",
                (question, top_similarity, reason),
            )

    def list_gaps(self, limit: int = 100) -> list[GapItem]:
        with self._connect() as conn:
            rows = conn.execute(
                """select question, top_similarity, reason, created_at::text as created_at
                   from gaps order by created_at desc limit %s""",
                (limit,),
            ).fetchall()
        return [GapItem(**r) for r in rows]

    def log_feedback(self, question: str, answer: str, helpful: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into feedback (question, answer, helpful) values (%s, %s, %s)",
                (question, answer, helpful),
            )

    def save_eval_report(self, report: dict) -> None:
        with self._connect() as conn:
            conn.execute("insert into eval_reports (report) values (%s)", (json.dumps(report),))

    def latest_eval_report(self) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("select report from eval_reports order by created_at desc limit 1").fetchone()
        return row["report"] if row else None
