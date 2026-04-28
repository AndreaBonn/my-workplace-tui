from workspace_tui.services.errors import (
    AuthenticationError,
    ConfigurationError,
    ConnectionFailedError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServiceError,
)


class TestServiceError:
    def test_default_code(self):
        err = ServiceError("something broke")
        assert err.message == "something broke"
        assert err.code == "INTERNAL_ERROR"
        assert str(err) == "something broke"

    def test_custom_code(self):
        err = ServiceError("bad", code="CUSTOM")
        assert err.code == "CUSTOM"


class TestNotFoundError:
    def test_message_format(self):
        err = NotFoundError(entity="Issue", identifier="PROJ-99")
        assert err.message == "Issue 'PROJ-99' not found"
        assert err.code == "NOT_FOUND"


class TestAuthenticationError:
    def test_default_message(self):
        err = AuthenticationError()
        assert err.code == "AUTH_ERROR"
        assert "Authentication failed" in err.message


class TestPermissionDeniedError:
    def test_default_message(self):
        err = PermissionDeniedError()
        assert err.code == "PERMISSION_ERROR"


class TestRateLimitError:
    def test_default_message(self):
        err = RateLimitError()
        assert err.code == "RATE_LIMIT"


class TestConnectionFailedError:
    def test_default_service(self):
        err = ConnectionFailedError()
        assert "API" in err.message
        assert err.code == "CONNECTION_ERROR"

    def test_custom_service(self):
        err = ConnectionFailedError(service="Gmail")
        assert "Gmail" in err.message


class TestConfigurationError:
    def test_message(self):
        err = ConfigurationError("Missing config")
        assert err.code == "CONFIG_ERROR"
        assert err.message == "Missing config"
