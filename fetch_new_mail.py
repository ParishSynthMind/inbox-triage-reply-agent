#!/usr/bin/env python3
"""Fetches unseen messages from an IMAP inbox and prints them in the
delimited plain-text format reply_loop.py expects to parse.

Env vars: IMAP_HOST, IMAP_USER, IMAP_PASSWORD (an app password, not your
real account password).
"""
import email
import imaplib
import os
import sys

IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.environ["IMAP_USER"]
IMAP_PASSWORD = os.environ["IMAP_PASSWORD"]


def main():
    conn = imaplib.IMAP4_SSL(IMAP_HOST)
    conn.login(IMAP_USER, IMAP_PASSWORD)
    conn.select("INBOX")

    status, data = conn.search(None, "UNSEEN")
    ids = data[0].split()
    if not ids:
        print("NO_NEW_MAIL")
        return

    for msg_id in ids:
        status, msg_data = conn.fetch(msg_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="replace")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="replace")

        print("=== NEW MESSAGE ===")
        print(f"From: {msg.get('From', '')}")
        print(f"Subject: {msg.get('Subject', '')}")
        print(f"Date: {msg.get('Date', '')}")
        print("Body:")
        print(body.strip())
        print("=== END MESSAGE ===")

    conn.close()
    conn.logout()


if __name__ == "__main__":
    sys.exit(main())
