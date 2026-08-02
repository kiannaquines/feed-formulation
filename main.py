from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.exception_handlers import register_exception_handlers
from api.openapi import OPENAPI_TAGS
from core.config import (
    API_PREFIX,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_ORIGINS,
    SERVER_HOST,
    SERVER_PORT,
)

from routes.authentication_routes import auth_router
from routes.feed_formulation_routes import feed_formulation_router
from routes.feed_formulation_v2_routes import feed_formulation_v2_router
from routes.ingredient_routes import ingredient_router
from routes.licensing_routes import admin_licensing_router, licensing_router
from routes.nutrient_requirements_routes import nutrient_requirements_router
from routes.root_routes import root_router

app = FastAPI(
    title="FeedPrime API",
    summary="Least-cost feed formulation and nutrition data management API",
    description="""
Calculate least-cost feed formulations with SciPy linear programming, manage
ingredient and nutrient data, and store formulation results per authenticated user.

## Authentication

1. Register with `/auth/register`.
2. Log in with `/auth/login` using the registered username or email and password.
3. When OTP is enabled, submit the returned session token and OTP to
   `/auth/verify-otp`.
4. Select **Authorize** and paste the access token. Swagger UI adds the
   `Bearer` authentication scheme automatically.

## Licensing

New accounts receive one 14-day Starter trial on their first registered device.
Paid Starter, Premium, and Ultra licenses are annual and assigned to one device.
Business endpoints require an active device entitlement; account, licensing, and
referral endpoints remain available after expiration.

## Ownership

Ingredient and nutrient lists include the current user's records and shared
legacy records. Shared records are read-only. Saved formulations are private to
the authenticated user.

## Formulation calculation

The optimizer minimizes ingredient cost while enforcing a 100% total mixture,
the supplied nutrient targets, and each ingredient's minimum and maximum bounds.
Percentages are submitted as decimals from `0` to `1` and returned as percentages.
The original endpoint remains under `/api/v1`; `/v2/feed/formulate` adds bounded
failure candidates and constraint diagnostics without changing V1 behavior.
""",
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS,
    contact={
        "name": "Kian Naquines",
        "email": "kjgnaquines@usm.edu.ph",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)
register_exception_handlers(app)

app.include_router(root_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(licensing_router, prefix=API_PREFIX)
app.include_router(admin_licensing_router, prefix=API_PREFIX)
app.include_router(feed_formulation_router, prefix=API_PREFIX)
app.include_router(ingredient_router, prefix=API_PREFIX)
app.include_router(nutrient_requirements_router, prefix=API_PREFIX)
app.include_router(feed_formulation_v2_router, prefix="/v2")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
