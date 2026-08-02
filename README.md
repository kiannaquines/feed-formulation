# Feed Formulation API

FastAPI service for feed formulation, ingredient and nutrient management, and authenticated formulation storage.

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
