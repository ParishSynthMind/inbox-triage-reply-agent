#!/usr/bin/env python3
"""Sends a plain-text email via SMTP.

Usage: send_email.py <to_addr> <subject> <body_file_or_'-'_for_stdin>

Env vars: SMTP_HOST (default smtp.gmail.com), SMTP_PORT (default 587),
SMTP_USER, SMTP_PASSWORD (an app password, not your real account password).
"""
import os
import smtplib
import sys
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]


def main():
    to_addr, subject, body_arg = sys.argv[1], sys.argv[2], sys.argv[3]
    body = sys.stdin.read() if body_arg == "-" else open(body_arg).read()

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_addr

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


if __name__ == "__main__":
    sys.exit(main())
