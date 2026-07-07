from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_body(code: str, message: str, detail=None) -> dict:
    return {"error": {"code": code, "message": message, "detail": detail}}


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body("http_error", str(exc.detail)),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    from fastapi.encoders import jsonable_encoder

    detail = [
        {"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_body("validation_error", "Invalid request", jsonable_encoder(detail)),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    # sanitized: no stack traces or internals leak to clients
    return JSONResponse(
        status_code=500,
        content=error_body("internal_error", "An internal error occurred"),
    )
