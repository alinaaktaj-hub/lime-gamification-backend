import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat_test_router import router


class ChatTestRouterTests(unittest.TestCase):
    def _make_client(self):
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_chat_test_success(self):
        client = self._make_client()

        with patch(
            "app.api.chat_test_router.OpenAIChatService.generate_response",
            new=AsyncMock(return_value="Hello from OpenAI"),
        ):
            response = client.post("/chat-test", json={"message": "Hello"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"response": "Hello from OpenAI"})

    def test_chat_test_validation(self):
        client = self._make_client()
        response = client.post("/chat-test", json={"message": ""})

        self.assertEqual(response.status_code, 422)

    def test_chat_test_upstream_error(self):
        client = self._make_client()

        with patch(
            "app.api.chat_test_router.OpenAIChatService.generate_response",
            new=AsyncMock(side_effect=RuntimeError("provider down")),
        ):
            response = client.post("/chat-test", json={"message": "Hello"})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "OpenAI request failed"})


if __name__ == "__main__":
    unittest.main()
