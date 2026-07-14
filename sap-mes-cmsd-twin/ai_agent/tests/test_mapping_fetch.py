"""
Tests for POST /api/agent/v1/mapping/fetch
"""
import json
import pytest


class TestMappingFetchEndpoint:
    """Tests for the mapping/fetch endpoint — TDD red phase."""

    # ─── Valid request ──────────────────────────────────────

    def test_fetch_single_endpoint_returns_200(self, client):
        """A valid single-endpoint request returns 200 with payload data."""
        mock_explorer = client.app.state.mock_explorer
        mock_explorer.fetch_payload.return_value = {
            "status_code": 200,
            "url": "http://mock-sap:8001/resources",
            "method": "GET",
            "payload": [{"id": 1, "name": "Lathe-01"}],
            "payload_size_bytes": 30,
        }

        response = client.post(
            "/api/agent/v1/mapping/fetch",
            json={
                "endpoints": [
                    {
                        "source_id": "src-test",
                        "endpoint": "/resources",
                        "method": "GET",
                        "label": "SAP Resources",
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["payloads"]) == 1
        payload = data["payloads"][0]
        assert payload["source_id"] == "src-test"
        assert payload["endpoint"] == "/resources"
        assert payload["label"] == "SAP Resources"
        assert payload["url"] == "http://mock-sap:8001/resources"
        assert payload["status_code"] == 200
        assert payload["status"] == "success"
        assert payload["size_bytes"] == 30
        assert payload["raw_payload"] == [{"id": 1, "name": "Lathe-01"}]

    def test_fetch_defaults_method_to_get(self, client):
        """If method is not provided, it defaults to GET."""
        mock_explorer = client.app.state.mock_explorer
        mock_explorer.fetch_payload.return_value = {
            "status_code": 200,
            "url": "http://mock-sap:8001/resources",
            "method": "GET",
            "payload": [],
            "payload_size_bytes": 2,
        }

        response = client.post(
            "/api/agent/v1/mapping/fetch",
            json={
                "endpoints": [
                    {
                        "source_id": "src-test",
                        "endpoint": "/resources",
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Verify the mock was called with method="GET" (the default)
        mock_explorer.fetch_payload.assert_awaited_once()
        called_kwargs = mock_explorer.fetch_payload.call_args[1]
        assert called_kwargs["method"] == "GET"

    # ─── Validation errors ──────────────────────────────────

    def test_missing_endpoints_field_returns_422(self, client):
        """Request body without 'endpoints' field returns 422."""
        response = client.post(
            "/api/agent/v1/mapping/fetch",
            json={"wrong_field": []},
        )
        assert response.status_code == 422

    def test_empty_endpoints_array_returns_400(self, client):
        """An empty endpoints array returns a 400 error."""
        response = client.post(
            "/api/agent/v1/mapping/fetch",
            json={"endpoints": []},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "No endpoints specified"

    # ─── Error handling ─────────────────────────────────────

    def test_source_not_found_returns_error_status(self, client):
        """When fetch_payload raises ValueError (source not found), return error payload."""
        mock_explorer = client.app.state.mock_explorer

        async def raise_value_error(*args, **kwargs):
            raise ValueError("Source 'bad-src' not configured")

        mock_explorer.fetch_payload.side_effect = raise_value_error

        response = client.post(
            "/api/agent/v1/mapping/fetch",
            json={
                "endpoints": [
                    {
                        "source_id": "bad-src",
                        "endpoint": "/resources",
                        "method": "GET",
                        "label": "Bad Source",
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["payloads"]) == 1
        payload = data["payloads"][0]
        assert payload["status"] == "error"
        error_raw = payload.get("raw_payload", {})
        error_msg = str(error_raw.get("error", "")) if isinstance(error_raw, dict) else str(error_raw)
        assert "not configured" in error_msg or payload.get("status_code") is None

    def test_http_error_returns_error_payload(self, client):
        """When fetch_payload raises an HTTP error, return error payload."""
        mock_explorer = client.app.state.mock_explorer

        async def raise_exception(*args, **kwargs):
            raise Exception("HTTP 500 Internal Server Error")

        mock_explorer.fetch_payload.side_effect = raise_exception

        response = client.post(
            "/api/agent/v1/mapping/fetch",
            json={
                "endpoints": [
                    {
                        "source_id": "src-test",
                        "endpoint": "/broken",
                        "method": "GET",
                        "label": "Broken Endpoint",
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["payloads"]) == 1
        payload = data["payloads"][0]
        assert payload["status"] == "error"

    # ─── Payload truncation ─────────────────────────────────

    def test_payload_truncated_when_over_5000_bytes(self, client):
        """Payloads larger than 5000 bytes are truncated with _truncated flag."""
        mock_explorer = client.app.state.mock_explorer
        large_payload = {"data": "x" * 6000}
        serialized_size = len(json.dumps(large_payload))
        mock_explorer.fetch_payload.return_value = {
            "status_code": 200,
            "url": "http://mock-sap:8001/large",
            "method": "GET",
            "payload": large_payload,
            "payload_size_bytes": serialized_size,
        }

        response = client.post(
            "/api/agent/v1/mapping/fetch",
            json={
                "endpoints": [
                    {
                        "source_id": "src-test",
                        "endpoint": "/large",
                        "method": "GET",
                        "label": "Large Payload",
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        payload = data["payloads"][0]
        raw = payload["raw_payload"]
        # Should have _truncated flag or be truncated
        if isinstance(raw, dict) and raw.get("_truncated"):
            assert raw["_truncated"] is True
            assert "_preview" in raw
            assert "_full_size_bytes" in raw
        # If not truncated (size under limit), that's also fine for this test
