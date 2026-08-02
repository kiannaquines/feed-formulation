from core.exceptions import ForbiddenError, NotFoundError


def require_mutable_owner(resource, user_id: int, resource_name: str) -> None:
    if resource is None or resource.user_id is None:
        raise NotFoundError(f"{resource_name} not found")
    if resource.user_id != user_id:
        raise ForbiddenError(
            f"You are not allowed to modify this {resource_name.lower()}"
        )
