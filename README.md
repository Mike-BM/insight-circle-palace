# Insight Circle Palace

A community and learning platform for young people and professionals: programs, weekly
**Insighters Monday** live sessions, recordings, memberships, merchandise and certificates.

- **Backend:** FastAPI (async), SQLAlchemy, Alembic migrations
- **Database:** SQLite for local development, PostgreSQL (for example Supabase) in production
- **Frontend:** static HTML with Tailwind and vanilla JS in `static/`; admin portal in `admin_app/`
- **Payments:** M-Pesa (Daraja STK push) and Stripe
- **Email:** Resend, with an SMTP fallback
- **Hosting:** Vercel (`vercel.json`)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # then fill in the values you need
alembic upgrade head                 # create or update the database tables
uvicorn main:app --reload
```

Open <http://localhost:8000>. With no `.env` changes the app uses a local SQLite file
(`insight_circle.db`), which is git-ignored.

## Admin account

No default admin password exists. Create one explicitly:

```bash
ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='a-long-unique-passphrase' python scripts/create_admin.py
```

The account must change its password at first login.

## Tests

```bash
pip install pytest httpx greenlet
pytest tests/ -v
```

The same command runs in CI (`.github/workflows/ci-cd.yml`) on every push and pull request.

## Project layout

```
main.py             App entry point, middleware and page routes
app/
  routers/          API endpoints (auth, programs, payments, recordings, admin, ...)
  services/         Email, M-Pesa, Stripe, certificates, memberships, video
  models.py         Database models
  schemas.py        Request and response schemas
  security.py       Hashing, tokens, validation
alembic/            Database migrations
static/             Public site (HTML, CSS, JS, images)
admin_app/          Admin portal
scripts/            Seed and maintenance scripts
tests/              Test suite
docs/               Project brief and design notes
```

## Configuration

All settings come from environment variables. `.env.example` lists every variable with a
short explanation. Never commit a real `.env` file or real keys.

## Deployment

The project deploys to Vercel from `main`. Set the environment variables from
`.env.example` in the Vercel dashboard, use a PostgreSQL `DATABASE_URL`, and run
`alembic upgrade head` against the production database before the first deploy.

## Contributing

1. Create a branch from `main`.
2. Make a focused change and add or update tests.
3. Run `pytest tests/ -v`.
4. Open a pull request.

## Contact

Insightcirclepalace@gmail.com
