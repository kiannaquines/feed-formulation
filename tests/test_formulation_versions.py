from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.authentication import create_jwt_token
from core.exceptions import ConflictError
from models.models import Base, FeedFormulation, FormulationSeries, User
from repositories import FeedFormulationRepository
from schema.schema import FeedFormulationWithPayloadRequest
from services import FeedFormulationService


def auth_header(user) -> dict:
    token = create_jwt_token(user.id, user.username, user.test_device_id)
    return {"Authorization": f"Bearer {token}"}


def formulation_payload(name: str, revision: int) -> dict:
    return {
        "formulation_name": name,
        "formulation_description": f"Revision {revision}",
        "payload": {"revision": revision},
    }


def save_formulation(client, user, name: str = "Versioned") -> dict:
    response = client.post(
        "/api/v1/feed/formulation/save",
        json=formulation_payload(name, 1),
        headers=auth_header(user),
    )
    assert response.status_code == 201
    return response.json()["formulation"]


def test_formulation_updates_create_immutable_versions_and_reject_stale_edits(
    client, db_session, user_factory
):
    owner = user_factory("version-owner")
    version_one = save_formulation(client, owner)

    version_two_response = client.post(
        f"/api/v1/feed/formulation/{version_one['id']}/versions",
        json=formulation_payload("Versioned", 2),
        headers=auth_header(owner),
    )
    version_two = version_two_response.json()["formulation"]
    stale = client.post(
        f"/api/v1/feed/formulation/{version_one['id']}/versions",
        json=formulation_payload("Versioned", 99),
        headers=auth_header(owner),
    )
    version_three_response = client.put(
        f"/api/v1/feed/formulation/update/{version_two['id']}",
        json=formulation_payload("Versioned", 3),
        headers=auth_header(owner),
    )
    version_three = version_three_response.json()["formulation"]
    listed = client.get(
        "/api/v1/feed/formulation/all", headers=auth_header(owner)
    )
    history = client.get(
        f"/api/v1/feed/formulation/{version_one['id']}/versions",
        headers=auth_header(owner),
    )
    stored_version_one = db_session.get(FeedFormulation, version_one["id"])

    assert version_two_response.status_code == 201
    assert version_two["version_number"] == 2
    assert version_two["parent_version_id"] == version_one["id"]
    assert stale.status_code == 409
    assert version_three_response.status_code == 201
    assert version_three["version_number"] == 3
    assert [item["version_number"] for item in listed.json()] == [3]
    assert [item["version_number"] for item in history.json()] == [3, 2, 1]
    assert stored_version_one.payload == {"revision": 1}


def test_edit_formulation_updates_selected_version_in_place(
    client, db_session, user_factory
):
    owner = user_factory("edit-owner")
    formulation = save_formulation(client, owner, "Before edit")

    response = client.put(
        f"/api/v1/feed/formulation/edit/{formulation['id']}",
        json=formulation_payload("After edit", 2),
        headers=auth_header(owner),
    )
    edited = response.json()["formulation"]
    db_session.expire_all()
    stored = db_session.get(FeedFormulation, formulation["id"])

    assert response.status_code == 200
    assert response.json()["message"] == "Formulation edited successfully."
    assert edited["id"] == formulation["id"]
    assert edited["series_id"] == formulation["series_id"]
    assert edited["version_number"] == formulation["version_number"]
    assert edited["formulation_name"] == "After edit"
    assert edited["payload"] == {"revision": 2}
    assert stored.formulation_name == "After edit"
    assert stored.formulation_description == "Revision 2"
    assert stored.payload == {"revision": 2}


def test_edit_formulation_enforces_ownership(client, user_factory):
    owner = user_factory("edit-private-owner")
    other = user_factory("edit-private-other")
    formulation = save_formulation(client, owner, "Private formulation")

    response = client.put(
        f"/api/v1/feed/formulation/edit/{formulation['id']}",
        json=formulation_payload("Unauthorized edit", 2),
        headers=auth_header(other),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You are not allowed to modify this formulation"
    }


def test_deleting_one_version_rewires_history_and_never_reuses_numbers(
    client, db_session, user_factory
):
    owner = user_factory("delete-version-owner")
    version_one = save_formulation(client, owner, "Delete versions")
    version_two = client.post(
        f"/api/v1/feed/formulation/{version_one['id']}/versions",
        json=formulation_payload("Delete versions", 2),
        headers=auth_header(owner),
    ).json()["formulation"]
    version_three = client.post(
        f"/api/v1/feed/formulation/{version_two['id']}/versions",
        json=formulation_payload("Delete versions", 3),
        headers=auth_header(owner),
    ).json()["formulation"]

    deleted_middle = client.delete(
        f"/api/v1/feed/formulation/remove/{version_two['id']}",
        headers=auth_header(owner),
    )
    history_after_delete = client.get(
        f"/api/v1/feed/formulation/{version_three['id']}/versions",
        headers=auth_header(owner),
    )
    db_session.expire_all()
    stored_version_three = db_session.get(FeedFormulation, version_three["id"])
    version_four = client.post(
        f"/api/v1/feed/formulation/{version_three['id']}/versions",
        json=formulation_payload("Delete versions", 4),
        headers=auth_header(owner),
    ).json()["formulation"]

    assert deleted_middle.status_code == 200
    assert [
        item["version_number"] for item in history_after_delete.json()
    ] == [3, 1]
    assert stored_version_three.parent_version_id == version_one["id"]
    assert version_four["version_number"] == 4

    client.delete(
        f"/api/v1/feed/formulation/remove/{version_four['id']}",
        headers=auth_header(owner),
    )
    latest = client.get(
        "/api/v1/feed/formulation/all", headers=auth_header(owner)
    )
    assert latest.json()[0]["version_number"] == 3

    client.delete(
        f"/api/v1/feed/formulation/remove/{version_three['id']}",
        headers=auth_header(owner),
    )
    client.delete(
        f"/api/v1/feed/formulation/remove/{version_one['id']}",
        headers=auth_header(owner),
    )
    assert db_session.scalar(select(FormulationSeries)) is None


def test_formulation_history_is_owner_scoped(client, user_factory):
    owner = user_factory("history-owner")
    other = user_factory("history-other")
    formulation = save_formulation(client, owner, "Private history")

    response = client.get(
        f"/api/v1/feed/formulation/{formulation['id']}/versions",
        headers=auth_header(other),
    )

    assert response.status_code == 403


def test_concurrent_version_creation_allocates_only_one_next_version(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'versions.db'}")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    with testing_session() as session:
        user = User(
            username="concurrent-version",
            email="concurrent-version@example.com",
            password_hash="unused",
            otp_secret="secret",
        )
        session.add(user)
        session.flush()
        series = FormulationSeries(user_id=user.id, next_version_number=2)
        session.add(series)
        session.flush()
        version_one = FeedFormulation(
            **formulation_payload("Concurrent version", 1),
            user_id=user.id,
            series_id=series.id,
            version_number=1,
        )
        session.add(version_one)
        session.commit()
        user_id = user.id
        version_one_id = version_one.id

    barrier = Barrier(2)

    def create_version(revision: int) -> str:
        with testing_session() as session:
            service = FeedFormulationService(
                session, FeedFormulationRepository(session)
            )
            barrier.wait()
            try:
                service.create_version(
                    version_one_id,
                    FeedFormulationWithPayloadRequest(
                        **formulation_payload("Concurrent version", revision)
                    ),
                    user_id,
                )
                return "created"
            except ConflictError:
                return "stale"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create_version, [2, 3]))
    with testing_session() as session:
        versions = list(
            session.scalars(
                select(FeedFormulation).order_by(
                    FeedFormulation.version_number
                )
            ).all()
        )
        stored_series = session.scalar(select(FormulationSeries))
    engine.dispose()

    assert sorted(results) == ["created", "stale"]
    assert [version.version_number for version in versions] == [1, 2]
    assert stored_series.next_version_number == 3
