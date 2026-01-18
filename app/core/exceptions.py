class ApiError(Exception):
    def __init__(self, message: str, code: str, http_status: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


class AuthError(ApiError):
    def __init__(self) -> None:
        super().__init__(
            message="Authentication failed",
            code="AUTH_FAILED",
            http_status=401,
        )


class MalformedInputError(ApiError):
    def __init__(self, message: str, code: str = "SCHEMA_INVALID") -> None:
        super().__init__(message=message, code=code, http_status=400)


class InternalError(ApiError):
    def __init__(self, message: str = "Internal server error") -> None:
        super().__init__(message=message, code="INTERNAL_ERROR", http_status=500)
