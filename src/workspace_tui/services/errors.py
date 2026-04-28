class ServiceError(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class AuthenticationError(ServiceError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message=message, code="AUTH_ERROR")


class PermissionError(ServiceError):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message=message, code="PERMISSION_ERROR")


class RateLimitError(ServiceError):
    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message=message, code="RATE_LIMIT")


class NotFoundError(ServiceError):
    def __init__(self, entity: str, identifier: str) -> None:
        super().__init__(message=f"{entity} '{identifier}' not found", code="NOT_FOUND")


class ConnectionError(ServiceError):
    def __init__(self, service: str = "API") -> None:
        super().__init__(message=f"Cannot connect to {service}", code="CONNECTION_ERROR")


class ConfigurationError(ServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="CONFIG_ERROR")
