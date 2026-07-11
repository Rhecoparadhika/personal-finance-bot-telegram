import asyncio

from app.llm.transaction_parser import parse_text_to_transactions


def test_parse_text_returns_warning_when_llm_provider_is_not_configured(monkeypatch):
    def _raise_configuration_error() -> None:
        raise RuntimeError("OpenAI API key is not configured. Set OPENAI_API_KEY to a real key in .env.")

    monkeypatch.setattr("app.llm.transaction_parser.get_llm_provider", _raise_configuration_error)

    result = asyncio.run(parse_text_to_transactions("makan bakso 25rb"))

    assert result.transactions == []
    assert "OpenAI API key is not configured" in result.warning
