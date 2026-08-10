"""Tests for Sunnylink authentication and retry handling."""
from __future__ import annotations

import importlib.util
import sys
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest.mock import patch


CLIENT_PATH = (
    Path(__file__).parents[1] / "custom_components" / "sunnypilot" / "client.py"
)
SPEC = importlib.util.spec_from_file_location("sunnypilot_client_under_test", CLIENT_PATH)
assert SPEC is not None and SPEC.loader is not None
client_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = client_module
SPEC.loader.exec_module(client_module)


class SunnylinkClientAuthTests(unittest.TestCase):
    """Verify cached-token recovery without making network requests."""

    def setUp(self) -> None:
        self.client = client_module.SunnylinkClient("refresh-token-1")
        self.client._token_payload = {"id_token": "id-token-1", "expires_in": 3600}
        self.client._token_obtained_at = client_module._time.monotonic()

    def test_forced_id_token_refresh_bypasses_valid_cached_token(self) -> None:
        def authenticate() -> None:
            self.client._token_payload = {
                "id_token": "id-token-2",
                "expires_in": 3600,
            }

        with patch.object(self.client, "authenticate", side_effect=authenticate) as auth:
            token = self.client._id_token(force_refresh=True)

        self.assertEqual("id-token-2", token)
        auth.assert_called_once_with()

    def test_api_auth_error_refreshes_and_retries_once(self) -> None:
        def authenticate() -> None:
            self.client._token_payload = {
                "id_token": "id-token-2",
                "expires_in": 3600,
            }

        with (
            patch.object(self.client, "authenticate", side_effect=authenticate) as auth,
            patch.object(
                client_module,
                "_request",
                side_effect=[
                    client_module.SunnylinkAuthError("HTTP 401"),
                    (200, {"values": []}),
                ],
            ) as request,
        ):
            payload = self.client.get_values("device-1", ["KeyOne"])

        self.assertEqual({"values": []}, payload)
        auth.assert_called_once_with()
        self.assertEqual(2, request.call_count)
        first_headers = request.call_args_list[0].kwargs["headers"]
        second_headers = request.call_args_list[1].kwargs["headers"]
        self.assertEqual("Bearer id-token-1", first_headers["Authorization"])
        self.assertEqual("Bearer id-token-2", second_headers["Authorization"])

    def test_second_api_auth_error_is_not_retried(self) -> None:
        def authenticate() -> None:
            self.client._token_payload = {
                "id_token": "id-token-2",
                "expires_in": 3600,
            }

        with (
            patch.object(self.client, "authenticate", side_effect=authenticate) as auth,
            patch.object(
                client_module,
                "_request",
                side_effect=client_module.SunnylinkAuthError("HTTP 403"),
            ) as request,
        ):
            with self.assertRaises(client_module.SunnylinkAuthError):
                self.client.get_devices()

        auth.assert_called_once_with()
        self.assertEqual(2, request.call_count)

    def test_refresh_token_request_marks_http_400_as_auth_error(self) -> None:
        with patch.object(
            client_module, "_request", return_value=(200, {})
        ) as request:
            client_module.refresh_tokens("invalid-refresh-token")

        self.assertEqual(
            client_module._LOGTO_AUTH_ERROR_STATUSES,
            request.call_args.kwargs["auth_error_statuses"],
        )

    def test_request_classifies_configured_http_status_as_auth_error(self) -> None:
        response = urllib.error.HTTPError(
            "https://logto.example/token",
            400,
            "Bad Request",
            {},
            BytesIO(b'{"error":"invalid_grant"}'),
        )
        try:
            with patch.object(
                client_module.urllib.request, "urlopen", side_effect=response
            ):
                with self.assertRaises(client_module.SunnylinkAuthError):
                    client_module._request(
                        "https://logto.example/token",
                        auth_error_statuses=frozenset({400}),
                    )
        finally:
            response.close()

    def test_set_value_uses_authenticated_request_helper(self) -> None:
        with patch.object(
            self.client,
            "_authenticated_request",
            return_value=(200, {"ok": True}),
        ) as request:
            payload = self.client.set_value("device-1", "Enabled", True, "Bool")

        self.assertEqual({"ok": True}, payload)
        self.assertEqual("POST", request.call_args.kwargs["method"])
        self.assertEqual("application/json", request.call_args.kwargs["content_type"])


if __name__ == "__main__":
    unittest.main()
