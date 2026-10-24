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

python3 reply_loop.py
```

Schedule it (e.g. every 15 minutes) for continuous triage.

## Stack

Python · IMAP/SMTP · Claude Agent SDK (session-resume for cross-email memory)

---
Part of a small portfolio of tested automation/AI builds — see [ParishSynthMind](https://github.com/ParishSynthMind) for the others.
