"""One error body for every failure: RFC 9457 Problem Details (`application/problem+json`)."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

TITLES = {401: "Unauthorized", 404: "Not Found", 409: "Conflict", 422: "Validation Error", 500: "Run Failed",
          503: "Service Unavailable", 504: "Run Timed Out"}


def problem(status: int, detail: str = "", instance: str = "") -> dict:
    return {"type": "about:blank", "title": TITLES.get(status, "Error"), "status": status, "detail": detail,
            "instance": instance}


async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(problem(exc.status_code, str(exc.detail), request.url.path), exc.status_code,
                        headers=exc.headers, media_type="application/problem+json")


async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    body = problem(422, "The request body or parameters are invalid.", request.url.path)
    body["errors"] = [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse(body, 422, media_type="application/problem+json")


def add_error_handlers(app: FastAPI) -> None:
    # Starlette's HTTPException also covers FastAPI's and the 404 of unknown routes
    app.add_exception_handler(StarletteHTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
