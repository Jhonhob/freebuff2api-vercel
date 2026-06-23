"""Tests for the Anthropic Messages API compatibility layer."""

from __future__ import annotations

import json
import unittest

from freebuff2api.anthropic_compat import (
    AnthropicCompletionAccumulator,
    AnthropicStreamState,
    anthropic_error_payload,
    anthropic_sse_encode,
    anthropic_sse_ping,
    anthropic_to_openai_messages,
    anthropic_tool_choice_to_openai,
    anthropic_tools_to_openai,
    build_anthropic_upstream_payload,
)
from freebuff2api.codebuff import FreebuffSession


# ── Helpers ──────────────────────────────────────────────────────────


def _session() -> FreebuffSession:
    return FreebuffSession(instance_id="inst-1", model="deepseek/deepseek-v4-flash")


# ── Message normalization ────────────────────────────────────────────


class AnthropicMessageConversionTests(unittest.TestCase):
    """Tests for anthropic_to_openai_messages."""

    def test_simple_user_message_string_content(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Hello"}],
        }
        messages = anthropic_to_openai_messages(body)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], {"role": "user", "content": "Hello"})

    def test_top_level_system_string_becomes_system_message(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 100,
            "system": "You are a helpful assistant.",
            "messages": [{"role": "user", "content": "hi"}],
        }
        messages = anthropic_to_openai_messages(body)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], "You are a helpful assistant.")
        self.assertEqual(messages[1]["role"], "user")

    def test_top_level_system_text_block_list(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 100,
            "system": [
                {"type": "text", "text": "Part 1. "},
                {"type": "text", "text": "Part 2."},
            ],
            "messages": [{"role": "user", "content": "hi"}],
        }
        messages = anthropic_to_openai_messages(body)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], "Part 1. \nPart 2.")

    def test_no_system_field_produces_no_system_message(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "hi"}],
        }
        messages = anthropic_to_openai_messages(body)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")

    def test_content_block_array_all_text(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hello"},
                        {"type": "text", "text": " world"},
                    ],
                }
            ],
        }
        messages = anthropic_to_openai_messages(body)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["content"], "Hello world")

    def test_tool_use_block_maps_to_assistant_with_tool_calls(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "What is the weather?"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Let me check."},
                        {
                            "type": "tool_use",
                            "id": "toolu_abc123",
                            "name": "get_weather",
                            "input": {"city": "San Francisco"},
                        },
                    ],
                },
            ],
        }
        messages = anthropic_to_openai_messages(body)

        # Should have: user text + assistant text + assistant tool_call
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["content"], "Let me check.")
        self.assertEqual(messages[2]["role"], "assistant")
        self.assertIsNone(messages[2]["content"])
        self.assertIn("tool_calls", messages[2])
        tc = messages[2]["tool_calls"][0]
        self.assertEqual(tc["type"], "function")
        self.assertEqual(tc["function"]["name"], "get_weather")
        parsed = json.loads(tc["function"]["arguments"])
        self.assertEqual(parsed["city"], "San Francisco")

    def test_tool_result_block_maps_to_tool_role(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "Weather?"},
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_abc123",
                            "name": "get_weather",
                            "input": {"city": "SF"},
                        },
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_abc123",
                            "content": "Sunny, 72F",
                        }
                    ],
                },
            ],
        }
        messages = anthropic_to_openai_messages(body)

        tool_messages = [m for m in messages if m["role"] == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertEqual(tool_messages[0]["content"], "Sunny, 72F")
        self.assertTrue(tool_messages[0]["tool_call_id"].startswith("call_"))

    def test_tool_result_content_list_flattened(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "Weather?"},
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_abc123",
                            "name": "get_weather",
                            "input": {"city": "SF"},
                        },
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_abc123",
                            "content": [
                                {"type": "text", "text": "Sunny"},
                                {"type": "text", "text": ", 72F"},
                            ],
                        }
                    ],
                },
            ],
        }
        messages = anthropic_to_openai_messages(body)

        tool_messages = [m for m in messages if m["role"] == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertEqual(tool_messages[0]["content"], "Sunny\n, 72F")


# ── Tools conversion ─────────────────────────────────────────────────


class AnthropicToolsConversionTests(unittest.TestCase):
    def test_anthropic_tools_to_openai_format(self) -> None:
        anthropic_tools = [
            {
                "name": "get_weather",
                "description": "Get the weather",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ]
        result = anthropic_tools_to_openai(anthropic_tools)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "function")
        self.assertEqual(result[0]["function"]["name"], "get_weather")
        self.assertEqual(
            result[0]["function"]["parameters"],
            anthropic_tools[0]["input_schema"],
        )

    def test_none_tools_returns_none(self) -> None:
        self.assertIsNone(anthropic_tools_to_openai(None))
        self.assertIsNone(anthropic_tools_to_openai([]))


class AnthropicToolChoiceConversionTests(unittest.TestCase):
    def test_auto(self) -> None:
        self.assertEqual(anthropic_tool_choice_to_openai("auto"), "auto")

    def test_any_maps_to_required(self) -> None:
        self.assertEqual(anthropic_tool_choice_to_openai("any"), "required")

    def test_none_maps_to_none(self) -> None:
        self.assertEqual(anthropic_tool_choice_to_openai("none"), "none")

    def test_dict_tool_type(self) -> None:
        result = anthropic_tool_choice_to_openai(
            {"type": "tool", "name": "get_weather"}
        )
        self.assertEqual(
            result,
            {"type": "function", "function": {"name": "get_weather"}},
        )

    def test_dict_auto_type(self) -> None:
        self.assertEqual(
            anthropic_tool_choice_to_openai({"type": "auto"}),
            "auto",
        )

    def test_none_input(self) -> None:
        self.assertIsNone(anthropic_tool_choice_to_openai(None))


# ── Upstream payload ─────────────────────────────────────────────────


class AnthropicUpstreamPayloadTests(unittest.TestCase):
    def test_basic_payload_structure(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": "Hello"}],
        }
        payload = build_anthropic_upstream_payload(
            body,
            session=_session(),
            run_id="run-1",
            client_id="client-1",
        )

        self.assertEqual(payload["stream"], True)
        self.assertEqual(payload["max_tokens"], 200)
        self.assertIn("messages", payload)
        self.assertIn("codebuff_metadata", payload)
        self.assertEqual(
            payload["codebuff_metadata"]["freebuff_instance_id"],
            "inst-1",
        )

    def test_temperature_mapped(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7,
        }
        payload = build_anthropic_upstream_payload(
            body,
            session=_session(),
            run_id="run-1",
            client_id="client-1",
        )

        self.assertEqual(payload["temperature"], 0.7)

    def test_stop_sequences_merged_with_default_stop(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": "Hello"}],
            "stop_sequences": ["\n\nHuman:", "END"],
        }
        payload = build_anthropic_upstream_payload(
            body,
            session=_session(),
            run_id="run-1",
            client_id="client-1",
        )

        self.assertIn("\n\nHuman:", payload["stop"])
        self.assertIn("END", payload["stop"])
        self.assertIn('"cb_easp"', payload["stop"])

    def test_top_k_preserved(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": "Hello"}],
            "top_k": 40,
        }
        payload = build_anthropic_upstream_payload(
            body,
            session=_session(),
            run_id="run-1",
            client_id="client-1",
        )

        self.assertEqual(payload["top_k"], 40)

    def test_tools_in_payload(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": "Hello"}],
            "tools": [
                {
                    "name": "get_weather",
                    "description": "...",
                    "input_schema": {"type": "object"},
                }
            ],
        }
        payload = build_anthropic_upstream_payload(
            body,
            session=_session(),
            run_id="run-1",
            client_id="client-1",
        )

        self.assertIn("tools", payload)
        self.assertEqual(payload["tools"][0]["type"], "function")

    def test_tool_choice_in_payload(self) -> None:
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": "Hello"}],
            "tool_choice": "auto",
        }
        payload = build_anthropic_upstream_payload(
            body,
            session=_session(),
            run_id="run-1",
            client_id="client-1",
        )

        self.assertEqual(payload["tool_choice"], "auto")


# ── Non-streaming accumulator ────────────────────────────────────────


class AnthropicCompletionAccumulatorTests(unittest.TestCase):
    def test_text_only_response(self) -> None:
        acc = AnthropicCompletionAccumulator("claude-sonnet-4-20250514")

        acc.add(
            {
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "Hello"},
                        "finish_reason": None,
                    }
                ],
            }
        )
        acc.add(
            {
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": " world"},
                        "finish_reason": "stop",
                    }
                ],
            }
        )

        response = acc.final_response()

        self.assertEqual(response["type"], "message")
        self.assertEqual(response["role"], "assistant")
        self.assertEqual(len(response["content"]), 1)
        self.assertEqual(response["content"][0]["type"], "text")
        self.assertEqual(response["content"][0]["text"], "Hello world")
        self.assertEqual(response["stop_reason"], "end_turn")
        self.assertEqual(response["stop_sequence"], None)

    def test_tool_use_response(self) -> None:
        acc = AnthropicCompletionAccumulator("claude-sonnet-4-20250514")

        acc.add(
            {
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_abc",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city": "SF"',
                                    },
                                }
                            ]
                        },
                    }
                ],
            }
        )
        acc.add(
            {
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "function": {"arguments": "}"},
                                }
                            ]
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }
        )

        response = acc.final_response()

        self.assertEqual(len(response["content"]), 1)
        self.assertEqual(response["content"][0]["type"], "tool_use")
        self.assertEqual(response["content"][0]["name"], "get_weather")
        self.assertEqual(
            response["content"][0]["input"], {"city": "SF"}
        )
        self.assertEqual(response["stop_reason"], "tool_use")

    def test_text_plus_tool_use_response(self) -> None:
        acc = AnthropicCompletionAccumulator("claude-sonnet-4-20250514")

        acc.add(
            {
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "Sure, let me check."},
                    }
                ],
            }
        )
        acc.add(
            {
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_abc",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": "{}",
                                    },
                                }
                            ]
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }
        )

        response = acc.final_response()

        self.assertEqual(len(response["content"]), 2)
        self.assertEqual(response["content"][0]["type"], "text")
        self.assertEqual(
            response["content"][0]["text"], "Sure, let me check."
        )
        self.assertEqual(response["content"][1]["type"], "tool_use")

    def test_finish_reason_mapping(self) -> None:
        test_cases = [
            (None, "end_turn"),
            ("stop", "end_turn"),
            ("length", "max_tokens"),
            ("tool_calls", "tool_use"),
            ("content_filter", "end_turn"),
        ]
        for oai, expected_anthropic in test_cases:
            with self.subTest(openai_reason=oai):
                acc = AnthropicCompletionAccumulator("test")
                acc.add(
                    {
                        "id": "chatcmpl-1",
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": "hi"},
                                "finish_reason": oai,
                            }
                        ],
                    }
                )
                response = acc.final_response()
                self.assertEqual(
                    response["stop_reason"], expected_anthropic
                )

    def test_usage_normalization(self) -> None:
        acc = AnthropicCompletionAccumulator("test")
        acc.add(
            {
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "hi"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            }
        )

        response = acc.final_response()

        self.assertEqual(response["usage"]["input_tokens"], 10)
        self.assertEqual(response["usage"]["output_tokens"], 2)


# ── Streaming state machine ──────────────────────────────────────────


class AnthropicStreamStateTests(unittest.TestCase):
    def test_text_only_stream(self) -> None:
        state = AnthropicStreamState("claude-sonnet-4-20250514")

        # First chunk with content.
        events = state.consume_chunk(
            {
                "id": "msg-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "Hello"},
                    }
                ],
            }
        )

        # Should emit: message_start + content_block_start + content_block_delta
        event_types = [e[0] for e in events]
        self.assertIn("message_start", event_types)
        self.assertIn("content_block_start", event_types)
        self.assertIn("content_block_delta", event_types)

        # Second chunk
        events = state.consume_chunk(
            {
                "id": "msg-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": " world"},
                        "finish_reason": "stop",
                    }
                ],
            }
        )
        event_types = [e[0] for e in events]
        self.assertTrue(all(t == "content_block_delta" for t in event_types))

        # Finalize
        final_events = state.finalize_events()
        final_types = [e[0] for e in final_events]
        self.assertIn("content_block_stop", final_types)
        self.assertIn("message_delta", final_types)
        self.assertIn("message_stop", final_types)

    def test_tool_use_stream_events(self) -> None:
        state = AnthropicStreamState("claude-sonnet-4-20250514")

        # Tool call start
        events = state.consume_chunk(
            {
                "id": "msg-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_abc",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city": "',
                                    },
                                }
                            ]
                        },
                    }
                ],
            }
        )

        event_types = [e[0] for e in events]
        self.assertIn("message_start", event_types)
        self.assertIn("content_block_start", event_types)
        self.assertIn("content_block_delta", event_types)

        # Verify content_block_start has tool_use type
        start_event = next(e for e in events if e[0] == "content_block_start")
        self.assertEqual(start_event[1]["content_block"]["type"], "tool_use")

        # Tool call delta
        events = state.consume_chunk(
            {
                "id": "msg-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "function": {"arguments": 'SF"}'},
                                }
                            ]
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }
        )

        for e in events:
            if e[0] == "content_block_delta":
                self.assertEqual(e[1]["delta"]["type"], "input_json_delta")

    def test_full_stream_lifecycle(self) -> None:
        state = AnthropicStreamState("claude-sonnet-4-20250514")

        chunks = [
            {
                "id": "msg-1",
                "choices": [{"index": 0, "delta": {"content": "Hello"}}],
            },
            {
                "id": "msg-1",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "!"},
                        "finish_reason": "stop",
                    }
                ],
            },
        ]

        all_events: list[str] = []
        for chunk in chunks:
            for event_type, _ in state.consume_chunk(chunk):
                all_events.append(event_type)
        for event_type, _ in state.finalize_events():
            all_events.append(event_type)

        # Check full lifecycle
        self.assertEqual(all_events[0], "message_start")
        self.assertIn("content_block_stop", all_events)
        self.assertIn("message_delta", all_events)
        self.assertEqual(all_events[-1], "message_stop")

        # message_delta should contain stop_reason
        delta_events = [
            e for t, e in state.finalize_events() if t == "message_delta"
        ]
        self.assertTrue(len(delta_events) > 0)
        self.assertEqual(
            delta_events[0]["delta"]["stop_reason"], "end_turn"
        )

    def test_empty_stream_produces_minimal_events(self) -> None:
        state = AnthropicStreamState("claude-sonnet-4-20250514")

        final_events = state.finalize_events()
        event_types = [e[0] for e in final_events]

        self.assertIn("message_start", event_types)
        self.assertIn("message_stop", event_types)


# ── SSE encoding ─────────────────────────────────────────────────────


class AnthropicSSETests(unittest.TestCase):
    def test_sse_encode_text_delta(self) -> None:
        data = anthropic_sse_encode(
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "Hello"},
            },
        )

        decoded = data.decode("utf-8")
        self.assertTrue(decoded.startswith("event: content_block_delta\n"))
        self.assertIn("data:", decoded)
        self.assertTrue(decoded.endswith("\n\n"))

    def test_sse_encode_message_start(self) -> None:
        data = anthropic_sse_encode(
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": "test",
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 10, "output_tokens": 1},
                },
            },
        )

        decoded = data.decode("utf-8")
        self.assertIn("event: message_start", decoded)

    def test_ping_event(self) -> None:
        data = anthropic_sse_ping()
        decoded = data.decode("utf-8")

        self.assertIn("event: ping", decoded)

    def test_sse_string_data(self) -> None:
        data = anthropic_sse_encode("message_stop", "{}")

        decoded = data.decode("utf-8")
        self.assertIn("event: message_stop", decoded)


# ── Error response ───────────────────────────────────────────────────


class AnthropicErrorTests(unittest.TestCase):
    def test_basic_error(self) -> None:
        payload = anthropic_error_payload("Something went wrong")

        self.assertEqual(payload["type"], "error")
        self.assertEqual(payload["error"]["type"], "api_error")
        self.assertEqual(payload["error"]["message"], "Something went wrong")

    def test_custom_error_type(self) -> None:
        payload = anthropic_error_payload(
            "Invalid model",
            error_type="invalid_request_error",
            status_code=400,
        )

        self.assertEqual(payload["error"]["type"], "invalid_request_error")
        self.assertEqual(payload["error"]["message"], "Invalid model")


if __name__ == "__main__":
    unittest.main()
