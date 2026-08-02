from datetime import datetime

from models.models import Ingredient
from repositories import IngredientRepository


def ingredient(name: str, user_id: int | None) -> Ingredient:
    return Ingredient(
        name=name,
        price=1,
        crude_protein=1,
        crude_fat=1,
        crude_fiber=1,
        metabolized_energy=1,
        calcium=1,
        total_phosphorus=1,
        avail_phosphorus=1,
        lysine=1,
        methionine=1,
        m_c=1,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )


def test_ingredient_repository_lists_owned_and_shared_rows(
    db_session, user_factory
):
    owner = user_factory("owner")
    other = user_factory("other")
    db_session.add_all(
        [
            ingredient("owned", owner.id),
            ingredient("shared", None),
            ingredient("other", other.id),
        ]
    )
    db_session.commit()

    visible = IngredientRepository(db_session).list_visible_to(owner.id)

    assert [row.name for row in visible] == ["owned", "shared"]


def test_repository_add_flushes_without_committing(db_session, user_factory):
    owner = user_factory("owner")
    repository = IngredientRepository(db_session)

    created = repository.add(ingredient("new", owner.id))

    assert created.id is not None
    assert db_session.in_transaction()
