from dataclasses import dataclass


TRIAL_DAYS = 14
LICENSE_DAYS = 365
REFERRAL_BONUS_DAYS = 30


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    price_php: int
    ingredient_limit: int | None
    requirement_limit: int | None


PLANS = {
    "starter": Plan("starter", "Starter", 35_000, 10, 10),
    "premium": Plan("premium", "Premium", 45_000, 50, 50),
    "ultra": Plan("ultra", "Ultra", 50_000, None, None),
}

DEVICE_TYPES = {"phone", "laptop", "desktop"}


def get_plan(code: str) -> Plan:
    return PLANS[code]
