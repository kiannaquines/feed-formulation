# FeedPrime API

FastAPI service for feed formulation, ingredient and nutrient management, and authenticated formulation storage.

## Licensing

New accounts receive one 14-day Starter trial. Registration requires a persistent
client installation UUID, device name, and one of the supported device types:
`phone`, `laptop`, or `desktop`. Access tokens are bound to that registered device,
while login requires only the username (or email address) and password.

Paid licenses are monthly, per-device licenses activated by a superuser after an
offline payment is verified:

| Plan | Monthly price | Saved ingredients | Saved requirements |
| --- | ---: | ---: | ---: |
| Starter | PHP 35,000 | 10 | 10 |
| Premium | PHP 45,000 | 50 | 50 |
| Ultra | PHP 50,000 | Unlimited | Unlimited |

Formulation calculation and saved formulations are unlimited while the device has
an active trial or paid license. After expiration, account, licensing, device, and
referral endpoints remain available, but formulation and saved-data endpoints are
blocked without deleting data.

Register the account and its device together:

```json
{
  "username": "example-user",
  "email": "example@example.com",
  "password": "password123",
  "installation_id": "2a4f56ef-a930-4934-a283-a6e476a6607a",
  "device_name": "Office laptop",
  "device_type": "laptop"
}
```

Then log in without repeating the device details:

```json
{
  "username": "example-user",
  "password": "password123"
}
```

The `username` login field also accepts the registered email address.

The public monthly pricing catalog is available at `/api/v1/pricing/plans`.
`/api/v1/licensing/plans` remains as a deprecated alias. The authenticated device
status is available at `/api/v1/licensing/status`, and superuser license lifecycle
operations are under `/api/v1/admin/licenses`.

Superusers can publish a new immutable price and quota version with
`POST /api/v1/admin/pricing/plans/{plan_code}/versions` and inspect its history
with the corresponding `GET` route. Published versions apply to future paid
activations and renewals; an active license keeps its existing price and quotas
until renewed. When publishing, an omitted quota keeps its current value, while
an explicit `null` changes that quota to unlimited.

## Formulation API versions

`POST /api/v1/feed/formulate` remains the original exact solver. The separate
`POST /v2/feed/formulate` endpoint uses the same primary calculation but adds a
closest bounded candidate, per-ingredient bound statuses, and aggregate constraint
diagnostics when the exact formulation is infeasible.

Saved formulations use immutable snapshots. Saving creates version 1, and
`POST /api/v1/feed/formulation/{formulation_id}/versions` creates the next version
from the current latest snapshot. Existing list routes return latest versions only;
the corresponding `/versions` GET route returns history newest first. The legacy
PUT update path remains available as a deprecated append-only alias.

`PUT /api/v1/feed/formulation/edit/{formulation_id}` edits the selected saved
formulation in place without changing its ID or version number. Use the `/versions`
endpoint instead when the previous formulation contents must remain in history.

## Prerequisites

- Python 3.12
- OpenSSL
- PostgreSQL 18

## Setup

Create and activate the virtual environment:

```bash
python3.12 -m venv env
source env/bin/activate
```

Install runtime and development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Install and start PostgreSQL 18 on macOS:

```bash
brew install postgresql@18
brew services start postgresql@18
```

Create the application role and databases. Use a generated password when
`createuser` prompts for one:

```bash
/opt/homebrew/opt/postgresql@18/bin/createuser --login --pwprompt feedprime_app
/opt/homebrew/opt/postgresql@18/bin/createdb --owner=feedprime_app feedprime
/opt/homebrew/opt/postgresql@18/bin/createdb --owner=feedprime_app feedprime_test
```

Create the local configuration:

```bash
cp .env.example .env
openssl rand -hex 32
```

Copy the generated OpenSSL value into `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://feedprime_app:<database-password>@localhost:5432/feedprime
JWT_SECRET_KEY=<generated-value>
```

The application requires `DATABASE_URL` and rejects missing, placeholder, or
shorter-than-32-character JWT secrets.

Apply the database migrations:

```bash
alembic upgrade head
```

### Migrate the existing SQLite data

Stop the API and create a consistent backup before migrating:

```bash
sqlite3 app_database.db ".backup 'app_database.sqlite.backup'"
```

After the PostgreSQL schema is upgraded, run the transfer first as a dry run and
then explicitly apply it:

```bash
python scripts/migrate_sqlite_to_postgres.py
python scripts/migrate_sqlite_to_postgres.py --apply
```

The migration refuses a non-empty PostgreSQL target, copies all rows in one
transaction, resets identity sequences, and compares every copied value. Keep the
SQLite database and backup until PostgreSQL has been verified. To roll back, stop
the API and restore the previous SQLite `DATABASE_URL`.

## Run

```bash
fastapi dev main.py
```

The combined API documentation is available at `http://127.0.0.1:8000/docs`.
Version-specific Swagger documentation is available at
`http://127.0.0.1:8000/docs/v1` and `http://127.0.0.1:8000/docs/v2`.

## Test

```bash
pytest -q
```

The default suite uses isolated SQLite databases. Run the same suite plus the
PostgreSQL migration and concurrency integration tests with:

```bash
TEST_DATABASE_URL=postgresql+psycopg://feedprime_app:<database-password>@localhost:5432/feedprime_test pytest -q
```

The PostgreSQL integration fixture refuses any database not named
`feedprime_test` before resetting its schema.
