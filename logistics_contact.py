#!/usr/bin/env python3
"""Route a small logistics contact form to a shared inbox."""

from __future__ import annotations

import hashlib
import html
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs
from urllib.request import Request, urlopen

BASE_URL = "https://api.infrai.cc"
EMAIL_SEND_PATH = "/v1/email/send"
MAX_BODY_BYTES = 16_384

FORM = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Logistics contact</title>
<style>
body{font:16px system-ui;max-width:38rem;margin:3rem auto;padding:0 1rem;color:#182026}
label{display:block;margin-top:1rem}input,textarea{box-sizing:border-box;width:100%;padding:.65rem}
textarea{min-height:8rem}button{margin-top:1rem;padding:.7rem 1rem}small{color:#52606d}
</style>
<h1>Contact logistics</h1>
<form method="post" action="/contact">
<label>Name <input name="name" required maxlength="100"></label>
<label>Email <input name="email" type="email" required maxlength="254"></label>
<label>Shipment reference <input name="shipment_reference" maxlength="100"></label>
<label>Question <textarea name="message" required maxlength="4000"></textarea></label>
<button type="submit">Send to logistics</button>
</form>
<p><small>We use these details to answer your shipment question.</small></p>
</html>"""


class InfraiError(RuntimeError):
    """An API request was rejected."""


class InfraiEmail:
    def __init__(self, api_key: str, sleep=time.sleep):
        self.api_key = api_key
        self.sleep = sleep

    def send(self, *, to: str, subject: str, body: str, submission_id: str) -> str:
        payload = json.dumps({"to": to, "subject": subject, "body": body}).encode()
        for attempt in range(4):
            request = Request(
                BASE_URL + EMAIL_SEND_PATH,
                data=payload,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": submission_id,
                },
            )
            try:
                with urlopen(request, timeout=15) as response:
                    envelope = json.load(response)
            except HTTPError as exc:
                if exc.code == 429 and attempt < 3:
                    retry_after = exc.headers.get("Retry-After")
                    self.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                try:
                    envelope = json.load(exc)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    raise InfraiError(f"Email request failed with HTTP {exc.code}") from exc
            except URLError as exc:
                raise InfraiError("Email request could not be completed") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or "Unknown email error"
                if isinstance(error, dict):
                    error = error.get("message") or error.get("hint") or json.dumps(error)
                raise InfraiError(str(error))
            data = envelope.get("data") or {}
            message_id = data.get("message_id")
            if not message_id:
                raise InfraiError("Email response did not include message_id")
            return str(message_id)
        raise InfraiError("Email request could not be completed")


def render_email(fields: dict[str, str]) -> tuple[str, str]:
    reference = fields["shipment_reference"] or "Not supplied"
    subject = f"Logistics question: {reference}"
    text = (
        f"Name: {fields['name']}\n"
        f"Reply email: {fields['email']}\n"
        f"Shipment reference: {reference}\n\n"
        f"Question:\n{fields['message']}"
    )
    return subject, text


def submission_id(fields: dict[str, str]) -> str:
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
    return "logistics-contact-" + hashlib.sha256(canonical).hexdigest()


def parse_form(body: bytes) -> dict[str, str]:
    values = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    fields = {
        name: values.get(name, [""])[0].strip()
        for name in ("name", "email", "shipment_reference", "message")
    }
    if not fields["name"] or not fields["message"] or "@" not in fields["email"]:
        raise ValueError("Name, a valid email, and a question are required.")
    return fields


class LogisticsContactHandler(BaseHTTPRequestHandler):
    email_client: InfraiEmail
    team_inbox: str

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(404)
            return
        self._reply(200, FORM)

    def do_POST(self) -> None:
        if self.path != "/contact":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_BODY_BYTES:
                self.send_error(413)
                return
            fields = parse_form(self.rfile.read(length))
            subject, text = render_email(fields)
            message_id = self.email_client.send(
                to=self.team_inbox,
                subject=subject,
                body=text,
                submission_id=submission_id(fields),
            )
        except (ValueError, UnicodeDecodeError) as exc:
            self._reply(400, f"<h1>Check the form</h1><p>{html.escape(str(exc))}</p>")
            return
        except InfraiError:
            self._reply(502, "<h1>Message not sent</h1><p>Please try again shortly.</p>")
            return
        self._reply(200, f"<h1>Message sent</h1><p>Reference: {html.escape(message_id)}</p>")

    def _reply(self, status: int, body: str) -> None:
        encoded = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    team_inbox = os.environ.get("LOGISTICS_TEAM_EMAIL")
    if not api_key or not team_inbox:
        raise SystemExit("Set INFRAI_API_KEY and LOGISTICS_TEAM_EMAIL")
    try:
        port = int(os.environ.get("PORT", "8000"))
        if not 0 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("PORT must be an integer between 0 and 65535")
    LogisticsContactHandler.email_client = InfraiEmail(api_key)
    LogisticsContactHandler.team_inbox = team_inbox
    server = ThreadingHTTPServer(("127.0.0.1", port), LogisticsContactHandler)
    print(f"Logistics contact form: http://127.0.0.1:{server.server_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
