from unittest.mock import patch

from app import services


@patch("app.services.requests.post")
def test_query_secure_slm_never_sends_raw_pii(mock_post):
    class MockResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"response": "We will notify <USER_EMAIL_1>."}

    mock_post.return_value = MockResponse()
    prompt = "My name is Alice Smith and my email is alice@example.com"

    response, latency = services.query_secure_slm(prompt)

    assert latency >= 0
    assert "alice@example.com" in response
    _, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert "alice@example.com" not in payload["prompt"]
    assert "<USER_EMAIL_1>" in payload["prompt"]
