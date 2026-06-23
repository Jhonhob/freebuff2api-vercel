"""Tests for the Anthropic /v1/messages endpoint."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from freebuff2api.app import app


class AnthropicMessagesEndpointTests(unittest.TestCase):
    # ── Auth tests ────────────────────────────────────────────────────

    def test_messages_endpoint_requires_configured_api_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with TestClient(app) as client:
                response = client.post("/v1/messages", json={
                    "model": "deepseek/deepseek-v4-flash",
                    "max_tokens": 100,
                    "messages": [{"role": "user", "content": "hello"}],
                })

        self.assertEqual(response.status_code, 503)
        self.assertIn("FREEBUFF_API_KEY", response.json()["detail"])

    def test_messages_endpoint_rejects_bearer_auth(self) -> None:
        """Anthropic endpoints should use x-api-key, not Authorization: Bearer."""
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"Authorization": "Bearer test-key"},
                )

        self.assertEqual(response.status_code, 401)

    def test_messages_endpoint_accepts_x_api_key(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "FREEBUFF_API_KEY": "test-key",
                "FREEBUFF_TOKEN": "test-token",
            },
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"x-api-key": "test-key"},
                )

        # Should be 502 (upstream unreachable) or 503 (no session),
        # NOT 401 (auth rejected).
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 503)

    def test_messages_endpoint_accepts_native_model_id(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "FREEBUFF_API_KEY": "test-key",
                "FREEBUFF_TOKEN": "test-token",
            },
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"x-api-key": "test-key"},
                )

        # Should not be a 400 (model not found).
        self.assertNotEqual(response.status_code, 400)

    def test_messages_endpoint_accepts_anthropic_alias_model(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "FREEBUFF_API_KEY": "test-key",
                "FREEBUFF_TOKEN": "test-token",
            },
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 100,
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"x-api-key": "test-key"},
                )

        # Should not be a 400 (model not found).
        self.assertNotEqual(response.status_code, 400)

    # ── Validation tests ──────────────────────────────────────────────

    def test_messages_missing_max_tokens(self) -> None:
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"x-api-key": "test-key"},
                )

        self.assertEqual(response.status_code, 400)
        self.assertIn("max_tokens", response.json()["detail"].lower())

    def test_messages_empty_messages(self) -> None:
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "messages": [],
                    },
                    headers={"x-api-key": "test-key"},
                )

        self.assertEqual(response.status_code, 400)

    def test_messages_missing_messages_field(self) -> None:
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                    },
                    headers={"x-api-key": "test-key"},
                )

        self.assertEqual(response.status_code, 400)
        self.assertIn("messages", response.json()["detail"].lower())

    def test_messages_invalid_model(self) -> None:
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "openai/gpt-99",
                        "max_tokens": 100,
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"x-api-key": "test-key"},
                )

        self.assertEqual(response.status_code, 400)

    # ── Error format tests ────────────────────────────────────────────

    def test_upstream_error_returns_anthropic_error_format(self) -> None:
        """When upstream fails, the Anthropic endpoint returns Anthropic-format errors."""
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"x-api-key": "test-key"},
                )

        # Should get an Anthropic-formatted error (since upstream is unreachable).
        if response.status_code >= 400:
            body = response.json()
            self.assertEqual(body.get("type"), "error")
            self.assertIn("error", body)
            self.assertIn("message", body["error"])
            self.assertIn("type", body["error"])

    # ── Request body acceptance tests ─────────────────────────────────

    def test_accepts_anthropic_system_top_level_string(self) -> None:
        """Anthropic system as a top-level string field."""
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "system": "You are a helpful coding assistant.",
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"x-api-key": "test-key"},
                )

        # Should not be a validation error.
        self.assertNotEqual(response.status_code, 400)
        self.assertNotEqual(response.status_code, 422)

    def test_accepts_anthropic_system_content_block_array(self) -> None:
        """Anthropic system as a list of text blocks."""
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "system": [
                            {"type": "text", "text": "You are helpful."},
                            {"type": "text", "text": " You use tools."},
                        ],
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"x-api-key": "test-key"},
                )

        self.assertNotEqual(response.status_code, 400)
        self.assertNotEqual(response.status_code, 422)

    def test_accepts_content_as_string(self) -> None:
        """Anthropic content as a plain string."""
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"x-api-key": "test-key"},
                )

        self.assertNotEqual(response.status_code, 400)
        self.assertNotEqual(response.status_code, 422)

    def test_accepts_content_as_block_array(self) -> None:
        """Anthropic content as a block array."""
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Help me code."},
                                ],
                            }
                        ],
                    },
                    headers={"x-api-key": "test-key"},
                )

        self.assertNotEqual(response.status_code, 400)
        self.assertNotEqual(response.status_code, 422)

    def test_accepts_anthropic_params(self) -> None:
        """Anthropic parameters like stop_sequences, top_k."""
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "messages": [{"role": "user", "content": "hello"}],
                        "stop_sequences": ["\n\nHuman:"],
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40,
                    },
                    headers={"x-api-key": "test-key"},
                )

        self.assertNotEqual(response.status_code, 400)
        self.assertNotEqual(response.status_code, 422)

    def test_accepts_tool_definitions(self) -> None:
        """Anthropic tools with input_schema."""
        with patch.dict(
            "os.environ",
            {"FREEBUFF_API_KEY": "test-key", "FREEBUFF_TOKEN": "test-token"},
            clear=True,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "deepseek/deepseek-v4-flash",
                        "max_tokens": 100,
                        "tools": [
                            {
                                "name": "get_weather",
                                "description": "Get the weather",
                                "input_schema": {
                                    "type": "object",
                                    "properties": {
                                        "city": {"type": "string"}
                                    },
                                    "required": ["city"],
                                },
                            }
                        ],
                        "messages": [{"role": "user", "content": "weather in SF?"}],
                    },
                    headers={"x-api-key": "test-key"},
                )

        self.assertNotEqual(response.status_code, 400)
        self.assertNotEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
