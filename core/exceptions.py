class ApplicationError(Exception):
    """Base exception for expected application failures."""


class ValidationError(ApplicationError):
    pass


class AuthenticationError(ApplicationError):
    pass


class ForbiddenError(ApplicationError):
    pass


class NotFoundError(ApplicationError):
    pass


class ConflictError(ApplicationError):
    pass


class PersistenceError(ApplicationError):
    pass


class OptimizationError(ApplicationError):
    pass
