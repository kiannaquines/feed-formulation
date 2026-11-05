# FeedPrime API

FastAPI service for feed formulation, ingredient and nutrient management, and authenticated formulation storage.

## Quick start

Requires Python 3.12 and OpenSSL. The default configuration uses a local SQLite
database at `app_database.db`.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp -n .env.example .env
openssl rand -hex 32
```

Put the generated value in `.env` as `JWT_SECRET_KEY`, then run:

```bash
python -m alembic upgrade head
fastapi dev main.py
```

The combined API documentation is at `http://127.0.0.1:8000/docs`. Versioned
documentation is at `/docs/v1`, `/docs/v2`, `/docs/v3`, and `/docs/v4`.

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

All formulation endpoints require a Bearer token and an active device license.
They minimize cost for a 100% mixture within ingredient inclusion bounds.

| Version | Endpoint | Nutrients | Infeasible result |
| --- | --- | --- | --- |
| V1 | `POST /api/v1/feed/formulate` | Four fixed fields | Failure details |
| V2 | `POST /v2/feed/formulate` | Four fixed fields | Bounded candidate and diagnostics |
| V3 | `POST /v3/feed/formulate` | Ten fixed fields | Bounded candidate and diagnostics |
| V4 | `POST /v4/feed/formulate` | Names chosen per request | Bounded candidate and diagnostics |

### V3 nutrient fields

V3 requires these fields in **every ingredient** and in `nutrient_requirements`:

| Workbook nutrient | API field | Unit |
| --- | --- | --- |
| CP | `protein_percent` | % |
| Cfat | `fat_percent` | % |
| Cfiber | `fiber_percent` | % |
| ME | `energy_me` | kcal/kg |
| Calcium | `calcium_percent` | % |
| Total P | `phosphorus_percent` | % |
| Avail. P | `available_phosphorus_percent` | % |
| Lysine | `lysine_percent` | % |
| Met | `methionine_percent` | % |
| M+C | `methionine_cystine_percent` | % |

The mapping follows `Mulberry Leaf meal Feed Formulation.xls`, Sheet1 columns
C, E, G, I, K, M, O, Q, S, and U. Percentages are percentage points (23 means
23%), while ingredient `min_percentage` and `max_percentage` are fractions
(0.1 means 10%). ME is energy, despite the `%ME` heading in some workbook tables.
All ten compositions and targets are required, finite, and nonnegative; nutrient
percentages cannot exceed 100. Use explicit zero only for known zero values.
Blank workbook requirements are not imported as zero or invented as presets.

V3 uses exact nutrient targets, not minimum/maximum ranges. Infeasible candidates
respect ingredient bounds but may miss nutrient targets or the 100% total. Check
`status`, `failed_constraints`, and `constraint_diagnostics` before using one.

### V4 dynamic nutrients

`POST /v4/feed/formulate` selects nutrients by name in each request. Each ingredient
has a `nutrients` object; every targeted nutrient must be present in every
ingredient, including an explicit `0` for a known zero value. Other measured
nutrients may be present and are ignored by that calculation. Values must use
consistent units across ingredients and targets. V4 keeps V3's exact targets,
100% mixture, inclusion bounds, least-cost optimization, and bounded failure
diagnostics. It accepts inline ingredients:

```json
{
  "ingredients": [
    {"name": "Corn", "cost_per_kg": 2, "nutrients": {"selenium_mg_kg": 1}},
    {"name": "Soybean", "cost_per_kg": 4, "nutrients": {"selenium_mg_kg": 3}}
  ],
  "nutrient_requirements": {"selenium_mg_kg": 1.5}
}
```

V4 saves ingredient nutrients in the JSON `composition` column. Its ingredient
endpoints are `GET /v4/ingredients/all`, `POST /v4/ingredients/create`,
`PUT /v4/ingredients/update/{ingredient_id}`, and
`DELETE /v4/ingredients/delete/{ingredient_id}`. They retain the existing
licensing and ownership rules. A create request can use
`{"name":"Corn","price":2,"composition":{"selenium_mg_kg":1}}`.

The two V4 Alembic revisions backfill JSON from the ten former nutrient columns,
then remove those columns. The V1 ingredient API keeps its fixed request and
response fields through a compatibility mapping; its list omits V4-only rows
that lack those fields. V1–V3 formulation requests and saved formulation payloads
keep their formats. V4 Swagger documentation is at `/docs/v4`, with its isolated
schema at `/openapi/v4.json`.

## Saved formulations

Saving a formulation creates version 1, and
`POST /api/v1/feed/formulation/{formulation_id}/versions` creates the next version
from the current latest snapshot. List routes return latest versions only;
the corresponding `/versions` GET route returns history newest first. The legacy
PUT update path remains available as a deprecated append-only alias.

`PUT /api/v1/feed/formulation/edit/{formulation_id}` edits the selected saved
formulation in place without changing its ID or version number. Use the `/versions`
endpoint instead when the previous formulation contents must remain in history.

## PostgreSQL (optional)

For PostgreSQL 18 on macOS, install the server and create an application role and
databases. Use a generated password when `createuser` prompts for one:

```bash
brew install postgresql@18
brew services start postgresql@18
/opt/homebrew/opt/postgresql@18/bin/createuser --login --pwprompt feedprime_app
/opt/homebrew/opt/postgresql@18/bin/createdb --owner=feedprime_app feedprime
/opt/homebrew/opt/postgresql@18/bin/createdb --owner=feedprime_app feedprime_test
```

In `.env`, comment out the SQLite `DATABASE_URL` and uncomment the PostgreSQL
example with your password. Run `python -m alembic upgrade head` against the new
database. The historical `scripts/migrate_sqlite_to_postgres.py` requires the
pre-V4 revision `f8b2c6d41e73` and cannot transfer a current V4 database.

## Test

```bash
python -m pytest -q
```

The default suite uses isolated SQLite databases. To include PostgreSQL
migration and concurrency tests, set `TEST_DATABASE_URL` to a dedicated database
named `feedprime_test`, then run `python -m pytest -q`. The integration fixture
refuses other database names before resetting its schema.
