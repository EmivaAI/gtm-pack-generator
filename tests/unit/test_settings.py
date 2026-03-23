"""
Tests for the Settings class (app.core.settings).

Covers:
- Valid provider + API key combinations (all 3 providers)
- Invalid/unsupported provider names
- Missing API key for the active provider
"""

import pytest
from pydantic import ValidationError

# API key env vars cleared before each test so the real environment doesn't leak in.
_API_KEY_ENV_VARS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY"]


@pytest.fixture(autouse=True)
def clear_api_key_env_vars(monkeypatch):
    for var in _API_KEY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


# _env_file=None skips .env; only the kwargs passed here are used.
def make_settings(**overrides):
    """Construct a Settings instance without reading .env."""
    from app.core.settings import Settings

    return Settings(
        llm_model_name="some-model",
        **overrides,
        _env_file=None,
    )


# ---------------------------------------------------------------------------
# Happy-path: valid provider + matching key present
# ---------------------------------------------------------------------------


class TestValidProviderWithKey:
    def test_openai_with_key(self):
        s = make_settings(llm_provider="openai", openai_api_key="sk-abc123")
        assert s.llm_provider == "openai"
        assert s.openai_api_key == "sk-abc123"

    def test_anthropic_with_key(self):
        s = make_settings(llm_provider="anthropic", anthropic_api_key="ant-key")
        assert s.llm_provider == "anthropic"

    def test_groq_with_key(self):
        s = make_settings(llm_provider="groq", groq_api_key="groq-key")
        assert s.llm_provider == "groq"


# ---------------------------------------------------------------------------
# Failure: unsupported provider name
# ---------------------------------------------------------------------------


class TestInvalidProvider:
    @pytest.mark.parametrize("bad_provider", ["gpt4", "gemini", "OPENAI"])
    def test_unsupported_provider_raises(self, bad_provider):
        with pytest.raises(ValidationError) as exc_info:
            make_settings(llm_provider=bad_provider, openai_api_key="sk-abc")
        assert "Unsupported LLM provider" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Failure: valid provider but corresponding API key is missing/empty
# ---------------------------------------------------------------------------


class TestMissingApiKey:
    def test_openai_without_key(self):
        with pytest.raises(ValidationError) as exc_info:
            make_settings(llm_provider="openai")
        assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_anthropic_without_key(self):
        with pytest.raises(ValidationError) as exc_info:
            make_settings(llm_provider="anthropic")
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_groq_without_key(self):
        with pytest.raises(ValidationError) as exc_info:
            make_settings(llm_provider="groq")
        assert "GROQ_API_KEY" in str(exc_info.value)

    def test_openai_with_wrong_provider_key(self):
        """Providing only the non-active provider's key should still fail."""
        with pytest.raises(ValidationError) as exc_info:
            make_settings(
                llm_provider="openai",
                openai_api_key="",  # active provider key — empty
                anthropic_api_key="ant",  # irrelevant key — ignored
            )
        assert "OPENAI_API_KEY" in str(exc_info.value)
