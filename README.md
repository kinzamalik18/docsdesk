# DocsDesk

A support assistant that answers customer questions from a company's own help docs. Every fact in an answer links to the article it came from, and when the docs don't cover a question, it says so instead of guessing. Unanswered questions are collected on a "Missing docs" page, so the team knows which article to write next.

The demo runs on the help center of **Fernbill, a fictional invoicing app**. The 14 articles, prices and policies are made up for this project.

- Live demo: _link added after deployment_
- API: _link added after deployment_

## What it does

- **Answers with sources.** Answers carry numbered references. Clicking one shows the exact passage from the help article.
- **Refuses to guess.** If no article is close to the question, the model isn't called at all. If the model reads the sources and they don't answer the question, it has to say so. An answer that cites nothing is held back.
- **Shows what's missing.** Every unanswered question is logged with the reason, on a page behind an admin token.
- **Measures itself.** A fixed set of 32 questions (26 the docs answer, 6 they don't, one of which is a prompt-injection attempt) runs against the live app. Results are shown row by row on the Accuracy page.
- **Takes new docs.** Admins can upload Markdown, text or PDF files through the API, and they're searchable right away.

## How it works

1. **Chunking.** Markdown is split at headings, so each chunk is one section, and the heading path (for example "Plans and pricing > Growth") is kept with it. Long sections are split at paragraph boundaries with one paragraph of overlap.
2. **Embedding.** Each chunk is embedded with its title and section prepended, which helps short sections match. Gemini embeddings at 768 dimensions, normalized so a dot product is cosine similarity.
3. **Hybrid search.** Vector search finds paraphrases ("end my subscription" for "cancel"). Postgres full-text search catches exact terms that embeddings can blur, like "Xero" or "2FA". The two result lists are merged with reciprocal rank fusion, which avoids having to calibrate their very different scores.
4. **Similarity gate.** If the best vector match is below a threshold (`MIN_SIMILARITY`), the question is logged as a gap and the model is never called. This saves API calls and removes the easiest way to get a made-up answer.
5. **Grounded answer.** The model gets numbered sources and must reply in JSON with `answerable`, `answer` and `citations`. Citations are checked against the sources actually sent. The prompt treats the sources and the question as data, so instructions hidden in either are ignored.

## Stack

| Part | Choice |
| --- | --- |
| API | Python, FastAPI |
| Model | Gemini (chat and embeddings) over plain HTTPS, with retries on rate limits |
| Search | Postgres with pgvector (HNSW index) and full-text search. An in-memory store with BM25 is used when no database is set |
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Hosting | Render (API), Supabase (database), Vercel (frontend) |
| Tests | pytest with an offline fake model, GitHub Actions |

## Accuracy

The Accuracy page runs the 32 questions in `backend/evals/fernbill.jsonl` against the deployed app and checks each answer:

- **Cited the right article:** the answer cited the article that covers the question.
- **Included the key fact:** the answer contained the expected detail, such as "$24" or "48 hours".
- **Declined when it should:** for the 6 questions the docs don't cover, the bot said so.

These are simple string checks, not a judge model. They're cheap and easy to audit, but they can mark a correct answer as wrong if it's phrased differently, so every answer is shown on the page for review. A test set of 32 questions on one small help center is a sanity check, not a benchmark.

_Results from the live app will be added here after the first run._

## Run it locally

You need Python 3.12+ and Node 22+.

```bash
# API
cd backend
cp .env.example .env          # add GEMINI_API_KEY, or set LLM_PROVIDER=fake to try it with no key
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend, in a second terminal
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000. Without `DATABASE_URL`, the API keeps everything in memory and re-indexes the sample docs on each start.

`LLM_PROVIDER=fake` swaps in a stand-in that hashes words into vectors and quotes the first source. It's there so the tests and the UI run with no API key. Its answers are not meant to be good.

Run the tests with `pytest` from `backend/`.

## Deploy

1. **Database:** create a free Supabase project, then copy the connection string (Session pooler) from Project settings > Database. The API creates its tables and the `vector` extension on first start.
2. **API:** in Render, create a Blueprint from this repo. It reads `render.yaml`. Fill in `GEMINI_API_KEY`, `DATABASE_URL` and `CORS_ORIGINS` (your Vercel URL). Render generates `ADMIN_TOKEN`; you'll find it in the service's Environment tab.
3. **Frontend:** in Vercel, import the repo with `frontend` as the root directory and set `NEXT_PUBLIC_API_URL` to the Render URL.

Render's free tier sleeps after 15 minutes without traffic, so the first question after a quiet spell can take up to a minute. The UI says so while it waits.

## API

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/chat` | `{"question": "..."}`. Rate limited per visitor |
| POST | `/api/feedback` | Helpful or not, per answer |
| GET | `/api/sources` | Indexed documents |
| GET | `/api/info` | Model and store in use |
| GET | `/api/gaps` | Unanswered questions. Admin token unless `PUBLIC_DASHBOARD=true` |
| GET | `/api/eval/latest` | Latest test-set results |
| POST | `/api/admin/eval` | Start a test-set run |
| POST | `/api/admin/documents` | Upload a `.md`, `.txt` or `.pdf` (5 MB max) |
| DELETE | `/api/admin/documents/{doc_id}` | Remove a document |
| POST | `/api/admin/reindex` | Re-index the sample docs |

Admin routes need the `X-Admin-Token` header.

## Limitations

- Scanned PDFs need OCR before upload. Text is read with pypdf only.
- One help center per deployment. There are no separate customer accounts.
- The chat rate limit and eval status are kept in memory, so they reset when the API restarts.
- Answers are in English, and full-text search uses the English dictionary.

## License

MIT
