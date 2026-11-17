"""AI disclosure for auto-sent replies (EU AI Act Art. 50).

Every reply this loop sends on its own ends with a short line saying an AI
wrote it. The text comes from AI_DISCLOSURE. It can only be switched off by
setting AI_DISCLOSURE to an empty value AND recording the client's written
request in AI_DISCLOSURE_REMOVED_BY_WRITTEN_REQUEST (date + who asked). A blank
AI_DISCLOSURE without that reference falls back to the default line.
"""
import os

DEFAULT_AI_DISCLOSURE = "This reply was written by an AI assistant."


def disclosure_line(env=None) -> str:
    env = os.environ if env is None else env
    text = (env.get("AI_DISCLOSURE") or "").strip()
    if not text:
        if (env.get("AI_DISCLOSURE_REMOVED_BY_WRITTEN_REQUEST") or "").strip():
            return ""
        text = DEFAULT_AI_DISCLOSURE
    return text


def with_disclosure(reply: str, env=None) -> str:
    """The reply body as it will be sent: the disclosure line at the end, once."""
    line = disclosure_line(env)
    reply = reply.rstrip()
    if not line or reply.endswith(line):
        return reply
    return f"{reply}\n\n{line}"
