# Feed Formulation API

FastAPI service for feed formulation, ingredient and nutrient management, and authenticated formulation storage.

## Licensing

New accounts receive one 14-day Starter trial. Login requires a persistent client
installation UUID, device name, and one of the supported device types: `phone`,
`laptop`, or `desktop`. Access tokens are bound to that registered device.

Paid licenses are annual, per-device licenses activated by a superuser after an
offline payment is verified:

| Plan | Annual price | Saved ingredients | Saved requirements |
| --- | ---: | ---: | ---: |
| Starter | PHP 35,000 | 10 | 10 |
| Premium | PHP 45,000 | 50 | 50 |
| Ultra | PHP 50,000 | Unlimited | Unlimited |

Formulation calculation and saved formulations are unlimited while the device has
an active trial or paid license. After expiration, account, licensing, device, and
referral endpoints remain available, but formulation and saved-data endpoints are
blocked without deleting data.

Register with an optional referral code, then log in with device identity:

```json
{
  "username": "example-user",
  "password": "password123",
  "installation_id": "2a4f56ef-a930-4934-a283-a6e476a6607a",
  "device_name": "Office laptop",
  "device_type": "laptop"
}
```

The licensing catalog and authenticated device status are available at
`/api/v1/licensing/plans` and `/api/v1/licensing/status`. Superuser lifecycle
operations are under `/api/v1/admin/licenses`.

## Prerequisites

- Python 3.12
- OpenSSL

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

Create the local configuration:

```bash
cp .env.example .env
openssl rand -hex 32
```

Copy the generated OpenSSL value into `.env`:

```dotenv
JWT_SECRET_KEY=<generated-value>
```

The application rejects missing, placeholder, or shorter-than-32-character JWT secrets.

Apply the database migrations:

```bash
alembic upgrade head
```

## Run

```bash
fastapi dev main.py
```

The API documentation is available at `http://127.0.0.1:8000/docs`.

## Test

```bash
pytest -q
```
