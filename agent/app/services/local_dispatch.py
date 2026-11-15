"""Invoke the canonical API handlers inside the mono-server process."""
import asyncio
import inspect
from typing import get_type_hints
from urllib.parse import parse_qs, urlsplit

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, TypeAdapter, ValidationError
from starlette.routing import Match


def call(method: str, path: str, body=None):
    from ..main import app
    from ..db import SessionLocal
    url = urlsplit(path)
    scope = {"type": "http", "method": method, "path": url.path, "root_path": ""}
    query = {k: v[-1] for k, v in parse_qs(url.query).items()}
    from .project_access import authorize
    authorize(method, url.path, query=query, body=body)
    def routes(router):
        for route in router.routes:
            included = getattr(route, "original_router", None)
            if included is not None:
                yield from routes(included)
            else:
                yield route

    for route in routes(app):
        if not hasattr(route, "endpoint"):
            continue
        match, child = route.matches(scope)
        if match != Match.FULL:
            continue
        endpoint = route.endpoint
        hints = get_type_hints(endpoint)
        with SessionLocal() as db:
            args = {}
            for name, param in inspect.signature(endpoint).parameters.items():
                annotation = hints.get(name, param.annotation)
                if name == "db":
                    args[name] = db
                elif name in child.get("path_params", {}):
                    args[name] = child["path_params"][name]
                elif name in query:
                    try:
                        args[name] = TypeAdapter(annotation).validate_python(query[name])
                    except ValidationError as exc:
                        raise HTTPException(422, "Paramètre de requête invalide") from exc
                elif inspect.isclass(annotation) and issubclass(annotation, BaseModel):
                    try:
                        args[name] = annotation.model_validate(body or {})
                    except ValidationError as exc:
                        raise HTTPException(422, "Corps de requête invalide") from exc
                elif annotation is dict and body is not None:
                    args[name] = body
                elif param.default is inspect.Parameter.empty:
                    raise HTTPException(422, f"Paramètre manquant : {name}")
            result = endpoint(**args)
            if inspect.isawaitable(result):
                result = asyncio.run(result)
            from starlette.responses import Response
            if isinstance(result, Response):
                import json
                content = json.loads(result.body)
                if result.status_code >= 400:
                    raise HTTPException(result.status_code, content)
                return content
            return jsonable_encoder(result)
    raise HTTPException(404, "Route interne inconnue")
