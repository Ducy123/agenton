from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    def __init__(self, detail: str = "Conflicting state"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class InsufficientBalanceError(HTTPException):
    def __init__(self, detail: str = "Insufficient wallet balance"):
        super().__init__(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)


class UnauthorizedError(HTTPException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Not allowed to access this resource"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
