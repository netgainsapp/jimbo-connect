"""Tests for the generation orchestration. The actual Claude call needs a key
and is not exercised here; these cover the dormant-safe behavior and helpers.
Run from backend/: python -m pytest tests/test_generate.py
"""
import asyncio

from blog.generate import MODEL, is_configured, run_once, _user_prompt


def test_model_is_the_chosen_one():
    assert MODEL == "claude-sonnet-4-6"


def test_user_prompt_includes_the_title():
    prompt = _user_prompt({"id": "x", "title": "How to Network at Conferences"})
    assert "How to Network at Conferences" in prompt


def test_is_configured_reads_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert is_configured() is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert is_configured() is True


def test_run_once_is_dormant_without_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = asyncio.run(run_once())
    assert out == {"ok": False, "skipped": "no_api_key"}
