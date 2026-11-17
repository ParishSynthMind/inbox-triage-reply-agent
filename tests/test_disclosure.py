"""Offline tests for the AI disclosure line on auto-sent replies. No mail server, no Claude."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import reply_loop  # noqa: E402
from disclosure import DEFAULT_AI_DISCLOSURE, disclosure_line, with_disclosure  # noqa: E402


def test_default_line_is_added_at_the_end_once():
    out = with_disclosure("Yes, Tuesday works.\n", env={})
    assert out == f"Yes, Tuesday works.\n\n{DEFAULT_AI_DISCLOSURE}"
    assert with_disclosure(out, env={}) == out


def test_custom_text():
    env = {"AI_DISCLOSURE": "Written by Acme's AI assistant."}
    assert with_disclosure("Hi", env=env).endswith("\n\nWritten by Acme's AI assistant.")


def test_blank_without_written_request_falls_back_to_default():
    assert disclosure_line({"AI_DISCLOSURE": ""}) == DEFAULT_AI_DISCLOSURE
    assert disclosure_line({"AI_DISCLOSURE": "   "}) == DEFAULT_AI_DISCLOSURE


def test_removed_only_with_recorded_written_request():
    env = {"AI_DISCLOSURE": "", "AI_DISCLOSURE_REMOVED_BY_WRITTEN_REQUEST": "2026-11-17 email from the owner"}
    assert with_disclosure("Hi", env=env) == "Hi"
    # A reference alone does not remove text that is still set.
    env["AI_DISCLOSURE"] = "Written by an AI assistant."
    assert with_disclosure("Hi", env=env).endswith("Written by an AI assistant.")


def test_every_sent_reply_carries_the_line(monkeypatch, tmp_path):
    monkeypatch.delenv("AI_DISCLOSURE", raising=False)
    monkeypatch.delenv("AI_DISCLOSURE_REMOVED_BY_WRITTEN_REQUEST", raising=False)
    monkeypatch.setattr(reply_loop, "LOG_FILE", tmp_path / "reply-log.md")
    monkeypatch.setattr(reply_loop, "TRUSTED_SENDERS", {"boss@example.com"})
    monkeypatch.setattr(reply_loop, "fetch_messages", lambda: [
        {"sender_addr": "boss@example.com", "subject": "Lunch?", "body": "Tuesday?"},
        {"sender_addr": "boss@example.com", "subject": "Re: Report", "body": "Done yet?"},
        {"sender_addr": "stranger@example.com", "subject": "Hello", "body": "Hi"},
    ])

    async def fake_reply(message):
        return "Sounds good."

    monkeypatch.setattr(reply_loop, "generate_reply", fake_reply)
    sent = []

    def fake_run(args, input=None, **kw):
        sent.append((args[2], args[3], input))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(reply_loop.subprocess, "run", fake_run)
    reply_loop.main()
    assert [(to, subj) for to, subj, _ in sent] == [("boss@example.com", "Re: Lunch?"), ("boss@example.com", "Re: Report")]
    assert all(body == f"Sounds good.\n\n{DEFAULT_AI_DISCLOSURE}" for _, _, body in sent)
