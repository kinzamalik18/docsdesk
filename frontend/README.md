# DocsDesk web

Next.js frontend for DocsDesk. It has three pages:

- `/` chat with cited answers
- `/gaps` questions the docs couldn't answer (needs the admin token)
- `/accuracy` results of the 32-question test set

## Run locally

```bash
cp .env.example .env.local   # point it at your API
npm install
npm run dev
```

The API has to allow this origin in its `CORS_ORIGINS` setting.
