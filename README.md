OAuth and CI setup

This app supports user login via Google and Facebook (OAuth) and includes a CI workflow that runs tests against a temporary PostgreSQL service.

Environment variables for OAuth:
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- FACEBOOK_CLIENT_ID
- FACEBOOK_CLIENT_SECRET
- BASE_URL (optional, defaults to http://localhost:8000)
- APP_ENV (set to `production` in production)

CI notes:
- CI uses TEST_DATABASE_URL to run tests against PostgreSQL. The workflow sets this automatically when running the provided GitHub Actions job.

Local testing:
- Start a local Postgres for tests:
  docker run --name insight-test-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:15
- Set TEST_DATABASE_URL to: postgresql+asyncpg://postgres:postgres@localhost:5432/postgres?ssl=false
- Run pytest

Security:
- Keep OAuth client secrets out of source control. Use repository secrets in GitHub Actions for any production-level credentials.
