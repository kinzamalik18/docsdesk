-- DocsDesk schema. Runs automatically on startup, and is safe to run more than once.
-- Works on Supabase and any Postgres with the pgvector extension available.

create extension if not exists vector;

create table if not exists documents (
    doc_id      text primary key,
    title       text not null,
    source      text not null,
    updated_at  timestamptz not null default now()
);

create table if not exists chunks (
    chunk_id    text primary key,
    doc_id      text not null references documents(doc_id) on delete cascade,
    section     text not null default '',
    content     text not null,
    position    int  not null,
    embedding   vector(:dim) not null,
    tsv         tsvector generated always as (
                    to_tsvector('english', coalesce(section, '') || ' ' || content)
                ) stored
);

create index if not exists chunks_embedding_idx on chunks using hnsw (embedding vector_cosine_ops);
create index if not exists chunks_tsv_idx on chunks using gin (tsv);

create table if not exists gaps (
    id             bigserial primary key,
    question       text not null,
    top_similarity real not null,
    reason         text not null,
    created_at     timestamptz not null default now()
);

create table if not exists feedback (
    id          bigserial primary key,
    question    text not null,
    answer      text not null,
    helpful     boolean not null,
    created_at  timestamptz not null default now()
);

create table if not exists eval_reports (
    id          bigserial primary key,
    report      jsonb not null,
    created_at  timestamptz not null default now()
);
