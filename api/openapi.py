from schema.schema import DetailResponse

OPENAPI_TAGS = [
    {
        "name": "System",
        "description": "Service discovery and runtime health information.",
    },
    {
        "name": "Authentication",
        "description": (
            "Register users, authenticate credentials, and complete optional "
            "one-time-password verification. Protected endpoints use a Bearer JWT."
        ),
    },
    {
        "name": "Licensing",
        "description": (
            "Inspect per-device plans, current entitlement and quota usage, registered "
            "devices, and referral rewards."
        ),
    },
    {
        "name": "Pricing",
        "description": "Public monthly prices and quota comparisons.",
    },
    {
        "name": "Pricing Administration",
        "description": (
            "Superuser-only immutable monthly price and quota version publishing."
        ),
    },
    {
        "name": "License Administration",
        "description": (
            "Superuser-only offline payment activation, renewal, revocation, and "
            "same-account device reassignment."
        ),
    },
    {
        "name": "Feed Formulation",
        "description": (
            "Calculate least-cost feed formulations and manage the authenticated "
            "user's saved formulation payloads."
        ),
    },
    {
        "name": "Feed Formulation V2",
        "description": (
            "Run the isolated V2 formulation API with closest-candidate diagnostics "
            "for infeasible optimization requests."
        ),
    },
    {
        "name": "Feed Formulation V3",
        "description": (
            "Calculate exact ten-nutrient formulations with bounded failure "
            "candidates and constraint diagnostics."
        ),
    },
    {
        "name": "Ingredients",
        "description": (
            "Manage ingredient composition and pricing. Users can read their own "
            "and shared ingredients, but shared records are read-only."
        ),
    },
    {
        "name": "Nutrient Requirements",
        "description": (
            "Manage named nutrient targets. Users can read their own and shared "
            "requirements, but shared records are read-only."
        ),
    },
]

PROTECTED_RESPONSES = {
    401: {
        "model": DetailResponse,
        "description": "The Bearer token is invalid, expired, or belongs to an inactive user.",
    },
    403: {
        "model": DetailResponse,
        "description": "Authentication credentials are missing or access is forbidden.",
    },
}

VALIDATION_RESPONSE = {
    422: {"description": "The request body or path parameters failed validation."}
}

OWNED_RESOURCE_RESPONSES = {
    **PROTECTED_RESPONSES,
    404: {
        "model": DetailResponse,
        "description": "The resource does not exist or is a read-only shared resource.",
    },
    **VALIDATION_RESPONSE,
}
