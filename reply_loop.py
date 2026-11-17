#!/usr/bin/env python3
"""Headless email triage + auto-reply loop, designed to run every N minutes
on a schedule (cron / launchd / Task Scheduler) rather than inside a
long-lived chat session.

Scope: only ever auto-replies to senders on an explicit trusted allowlist
(read from the TRUSTED_SENDERS env var). Any other sender is logged but
never auto-replied to - there's nobody present in a headless run to review
a draft before it goes to a third party, so the safe default for unknown
senders is silence, not a guess.

Session continuity: reuses the Claude Agent SDK's session-resume mechanism
so the reply conversation has real memory across emails - if the same
sender writes again tomorrow, the agent still has the prior exchange in
context, rather than starting from amnesia every run.

This is a trimmed, generic version of a production triage loop - the
original plugs into a specific mailbox and a specific assistant persona;
this version keeps the pattern (poll -> filter by trust -> generate with
memory -> reply -> log) without any of that specific configuration.

AI disclosure (EU AI Act Art. 50): every auto-sent reply ends with the line
from AI_DISCLOSURE (see disclosure.py).
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import Path

from disclosure import with_disclosure

HERE = Path(__file__).parent
SESSION_FILE = HERE / ".reply_session_id"
LOG_FILE = HERE / "reply-log.md"
FETCH_SCRIPT = HERE / "fetch_new_mail.py"
SEND_EMAIL = HERE / "send_email.py"

TRUSTED_SENDERS = {
    addr.strip().lower()
    for addr in os.environ.get("TRUSTED_SENDERS", "").split(",")
    if addr.strip()
}

REPLY_DISCIPLINE = (
    "This is a real email reply, not a chat message - reply like an email. "
    "Direct and complete, no markdown headers or bullet walls unless the "
    "content genuinely needs structure. No greeting line, no sign-off "
    "needed - just the reply body. If the message asks something you can "
    "actually check, check it for real rather than guessing. If it's "
    "something only a human can decide, say so plainly."
)


def log(line: str):
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with open(LOG_FILE, "a") as f:
        f.write(f"- {ts}: {line}\n")


def fetch_messages():
    """Returns list of dicts: sender_name, sender_addr, subject, date, body."""
    proc = subprocess.run(["python3", str(FETCH_SCRIPT)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"fetch_new_mail.py failed: {proc.stderr}")
    out = proc.stdout
    if "NO_NEW_MAIL" in out:
        return []
    messages = []
    for block in out.split("=== NEW MESSAGE ===")[1:]:
        block = block.split("=== END MESSAGE ===")[0]
        m = {}
        lines = block.strip().splitlines()
        for i, line in enumerate(lines):
            if line.startswith("From: "):
                name, addr = parseaddr(line[len("From: "):])
                m["sender_name"], m["sender_addr"] = name, addr
            elif line.startswith("Subject: "):
                m["subject"] = line[len("Subject: "):]
            elif line.startswith("Date: "):
                m["date"] = line[len("Date: "):]
            elif line.strip() == "Body:":
                m["body"] = "\n".join(lines[i + 1:]).strip()
                break
        if m:
            messages.append(m)
    return messages


async def generate_reply(message: str) -> str:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient  # lazy: tests need no SDK

    resume_id = SESSION_FILE.read_text().strip() if SESSION_FILE.exists() else None
    resume_id = resume_id or None

    def make_options(resume):
        return ClaudeAgentOptions(
            system_prompt={"type": "preset", "preset": "claude_code", "append": REPLY_DISCIPLINE},
            permission_mode="bypassPermissions",
            resume=resume,
            # A single large tool result (e.g. examining an attachment) can
            # blow past the SDK's default 1MB stdout JSON buffer and kill
            # the message reader - raise it for headless safety.
            max_buffer_size=25 * 1024 * 1024,
        )

    client = ClaudeSDKClient(options=make_options(resume_id))
    try:
        await client.connect()
    except Exception:
        SESSION_FILE.unlink(missing_ok=True)
        client = ClaudeSDKClient(options=make_options(None))
        await client.connect()

    try:
        await client.query(message)
        reply_text = ""
        new_session_id = None
        async for msg in client.receive_response():
            t = type(msg).__name__
            if t == "AssistantMessage":
                for block in getattr(msg, "content", []):
                    if type(block).__name__ == "TextBlock":
                        reply_text += block.text
            elif t == "ResultMessage":
                new_session_id = getattr(msg, "session_id", None)
        if new_session_id:
            SESSION_FILE.write_text(new_session_id)
        return reply_text.strip() or "(no text response)"
    finally:
        await client.disconnect()


def main():
    import asyncio

    try:
        messages = fetch_messages()
    except Exception as e:
        log(f"ERROR fetching mail: {e}")
        sys.exit(1)

    if not messages:
        return  # silent no-op, nothing new

    for m in messages:
        sender = m.get("sender_addr", "").lower()
        subject = m.get("subject", "(no subject)")
        body = m.get("body", "")

        if sender not in TRUSTED_SENDERS:
            log(f"Skipped (not on trusted allowlist): {sender} | {subject}")
            continue

        log(f"Received from trusted sender: {subject}")
        try:
            reply = asyncio.run(generate_reply(
                f"Email, subject \"{subject}\":\n\n{body}"
            ))
        except Exception as e:
            log(f"ERROR generating reply to '{subject}': {e}")
            continue

        reply = with_disclosure(reply)
        reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        proc = subprocess.run(
            ["python3", str(SEND_EMAIL), sender, reply_subject, "-"],
            input=reply, text=True, capture_output=True,
        )
        if proc.returncode != 0:
            log(f"ERROR sending reply to '{subject}': {proc.stderr}")
            continue
        log(f"Replied to: {subject}")


if __name__ == "__main__":
    main()
