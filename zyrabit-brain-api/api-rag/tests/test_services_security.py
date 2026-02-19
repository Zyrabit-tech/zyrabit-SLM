from unittest.mock import patch

from app import services


@patch("app.services.print")
@patch("app.services.requests.post")
def test_query_secure_slm_never_sends_raw_pii(mock_post, mock_print):
    class MockResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"response": "We will notify <USER_EMAIL_1>."}

    mock_post.return_value = MockResponse()
    prompt = (
        "My name is Alice Smith, my email is alice@example.com, "
        "phone 415-555-1234 and SSN 123-45-6789"
    )

    response, latency = services.query_secure_slm(prompt)

    assert latency >= 0
    assert "alice@example.com" in response
    _, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert "alice@example.com" not in payload["prompt"]
    assert "415-555-1234" not in payload["prompt"]
    assert "123-45-6789" not in payload["prompt"]
    assert "<USER_EMAIL_1>" in payload["prompt"]
    assert "<PHONE_1>" in payload["prompt"]
    assert "<SSN_1>" in payload["prompt"]

    # Ensure logs never leak raw prompt content.
    printed_text = " ".join(
        " ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list
    )
    assert "alice@example.com" not in printed_text
    assert "123-45-6789" not in printed_text
