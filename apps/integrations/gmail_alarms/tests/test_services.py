from unittest.mock import Mock

from apps.integrations.gmail_alarms import services


def test_gmail_client_secret_file_resolves_relative_path(settings):
    settings.GOOGLE_CREDENTIALS_FILE = "Config/client_secret.json"

    assert services.gmail_client_secret_file() == settings.BASE_DIR / "Config" / "client_secret.json"


def test_check_gmail_oauth_returns_message_ids(settings, tmp_path, monkeypatch):
    client_secret_file = tmp_path / "client_secret.json"
    token_file = tmp_path / "token.pickle"
    client_secret_file.write_text("{}", encoding="utf-8")
    token_file.write_text("{}", encoding="utf-8")
    settings.GOOGLE_CREDENTIALS_FILE = str(client_secret_file)

    service = Mock()
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "resultSizeEstimate": 4,
        "messages": [{"id": "msg-1"}, {"id": "msg-2"}, {"id": "msg-3"}],
    }

    monkeypatch.setattr(services, "gmail_token_file", lambda: token_file)
    monkeypatch.setattr(services, "build_gmail_service", lambda: service)

    result = services.check_gmail_oauth(query="label:inbox", max_results=2)

    assert result == {
        "ok": True,
        "query": "label:inbox",
        "client_secret_file": str(client_secret_file),
        "token_file": str(token_file),
        "result_size_estimate": 4,
        "message_ids": ["msg-1", "msg-2"],
    }
    service.users.return_value.messages.return_value.list.assert_called_once_with(
        userId="me",
        q="label:inbox",
        includeSpamTrash=False,
        maxResults=2,
    )


def test_check_gmail_oauth_fails_when_token_file_is_missing(settings, tmp_path, monkeypatch):
    client_secret_file = tmp_path / "client_secret.json"
    client_secret_file.write_text("{}", encoding="utf-8")
    settings.GOOGLE_CREDENTIALS_FILE = str(client_secret_file)

    missing_token_file = tmp_path / "missing-token.pickle"
    monkeypatch.setattr(services, "gmail_token_file", lambda: missing_token_file)

    try:
        services.check_gmail_oauth()
    except FileNotFoundError as exc:
        assert str(missing_token_file) in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for a missing Gmail token file")
