from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock

import pytest
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from faststream.asgi import (
    AsgiFastStream,
    AsgiResponse,
    Request,
    get,
    make_asyncapi_asgi,
    make_ping_asgi,
    post,
)
from faststream.asgi.types import ASGIApp, Scope
from faststream.specification import AsyncAPI


class AsgiTestcase:
    def get_broker(self) -> Any:
        raise NotImplementedError

    def get_test_broker(self, broker: Any) -> Any:
        raise NotImplementedError

    @pytest.mark.asyncio()
    async def test_not_found(self) -> None:
        broker = self.get_broker()
        app = AsgiFastStream(broker)

        async with self.get_test_broker(broker):
            with TestClient(app) as client:
                response = client.get("/")
                assert response.status_code == 404

    @pytest.mark.asyncio()
    async def test_ws_not_found(self) -> None:
        broker = self.get_broker()

        app = AsgiFastStream(broker)

        async with self.get_test_broker(broker):
            with TestClient(app) as client:
                with pytest.raises(WebSocketDisconnect):
                    with client.websocket_connect("/ws"):  # raises error
                        pass

    @pytest.mark.asyncio()
    async def test_asgi_ping_healthy(self) -> None:
        broker = self.get_broker()

        app = AsgiFastStream(
            broker,
            asgi_routes=[("/health", make_ping_asgi(broker, timeout=5.0))],
        )

        async with self.get_test_broker(broker):
            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 204

    @pytest.mark.asyncio()
    async def test_asgi_ping_unhealthy(self) -> None:
        broker = self.get_broker()

        app = AsgiFastStream(
            broker,
            asgi_routes=[
                ("/health", make_ping_asgi(broker, timeout=5.0)),
            ],
        )
        async with self.get_test_broker(broker) as br:
            br.ping = AsyncMock()
            br.ping.return_value = False

            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 500

    @pytest.mark.asyncio()
    async def test_asyncapi_asgi(self) -> None:
        broker = self.get_broker()

        app = AsgiFastStream(
            broker,
            specification=AsyncAPI(),
            asyncapi_path="/docs",
        )

        async with self.get_test_broker(broker):
            with TestClient(app) as client:
                response = client.get("/docs")
                assert response.status_code == 200, response
                assert response.text

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("decorator", "client_method"),
        (
            pytest.param(get, "get", id="get"),
            pytest.param(post, "post", id="post"),
        ),
    )
    async def test_decorators(
        self, decorator: Callable[..., ASGIApp], client_method: str
    ) -> None:
        @decorator
        async def some_handler(scope: Scope) -> AsgiResponse:
            return AsgiResponse(body=b"test", status_code=200)

        broker = self.get_broker()
        app = AsgiFastStream(broker, asgi_routes=[("/test", some_handler)])

        async with self.get_test_broker(broker):
            with TestClient(app) as client:
                response = getattr(client, client_method)("/test")
                assert response.status_code == 200
                assert response.text == "test"

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("decorator", "client_method"),
        (
            pytest.param(get, "get", id="get"),
            pytest.param(post, "post", id="post"),
        ),
    )
    async def test_request_injected(
        self, decorator: Callable[..., ASGIApp], client_method: str
    ) -> None:
        @decorator
        async def some_handler(request: Request) -> AsgiResponse:
            return AsgiResponse(body=request.__class__.__name__.encode(), status_code=200)

        broker = self.get_broker()
        app = AsgiFastStream(broker, asgi_routes=[("/test", some_handler)])

        async with self.get_test_broker(broker):
            with TestClient(app) as client:
                response = getattr(client, client_method)("/test")
                assert response.status_code == 200
                assert response.text == "AsgiRequest"

    def test_asyncapi_pure_asgi(self) -> None:
        broker = self.get_broker()

        app = Starlette(routes=[Mount("/", make_asyncapi_asgi(AsyncAPI(broker)))])

        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert response.text.strip().startswith("<!DOCTYPE html>")
