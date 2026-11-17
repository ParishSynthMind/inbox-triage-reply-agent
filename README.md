# Inbox Triage & Reply Agent

A headless email loop that polls an inbox, filters by a trusted-sender allowlist, and generates context-aware replies using Claude - with real memory across emails, not amnesia between runs.

## Why this design

- **Trusted-sender allowlist, not "reply to everyone."** Auto-replying to an unknown third party with no human reviewing the draft first is a bad default. Anyone not on the allowlist is logged, never auto-replied to - the safe default for an unattended run is silence, not a guess.
- **Session continuity.** Replies are generated through the Claude Agent SDK's session-resume mechanism, so if the same trusted sender writes again next week, the agent still has the prior exchange in context instead of starting cold every single run.
- **Built to run headless, on a schedule.** No interactive approval step, no terminal session required - meant to be invoked every N minutes by cron/launchd/Task Scheduler and just do the triage work on its own.
- **Logs everything**, including what it chose *not* to act on - so a scheduled job that ran while nobody was watching still leaves an audit trail.

## Usage

```bash
export IMAP_USER=you@example.com
export IMAP_PASSWORD=your-app-password
export SMTP_USER=you@example.com
export SMTP_PASSWORD=your-app-password
export TRUSTED_SENDERS=you@example.com,your-other-address@example.com
export AI_DISCLOSURE="This reply was written by an AI assistant."   # optional, this is the default

python3 reply_loop.py
```

Schedule it (e.g. every 15 minutes) for continuous triage.

## AI disclosure (EU AI Act Article 50)

- Every reply the loop sends on its own ends with a short line: "This reply was written by an AI assistant."
- The text is set with `AI_DISCLOSURE` (see `disclosure.py`). Blanking it only removes the line when the client's recorded written request (date and who asked) is in `AI_DISCLOSURE_REMOVED_BY_WRITTEN_REQUEST`; otherwise the default line is used.
- Tested offline with `pytest` (`pip install -r requirements-dev.txt`; no mail server, no Claude): the line is on every sent reply, added once, and not removable without the reference.

## Stack

Python · IMAP/SMTP · Claude Agent SDK (session-resume for cross-email memory)

---
Part of a small portfolio of tested automation/AI builds — see [ParishSynthMind](https://github.com/ParishSynthMind) for the others.
