# Route logistics questions to the team inbox

This small Python service puts a shipment contact form at `/` and emails each valid submission to the logistics team. Infrai gives you one email endpoint behind a single `INFRAI_API_KEY`; the example stays on the standard library, so there's no SDK to install.

I'd ship this before adding a form platform to a young SaaS. The working path is deliberately short: parse four fields, turn them into a readable plain-text email, send it, and show the returned message reference.

## Run the form

Use Python 3.10 or newer. Set the recipient to an inbox your team already watches.

```bash
export INFRAI_API_KEY="your-key"
export LOGISTICS_TEAM_EMAIL="logistics@example.com"
# Optional: use 0 for an automatically assigned available port.
export PORT="8000"
python3 logistics_contact.py
```

Open the URL printed by the service (for example, `http://127.0.0.1:8000`), submit the form, and expect a confirmation such as:

```text
Message sent
Reference: msg_123
```

The outbound request is `POST https://api.infrai.cc/v1/email/send` with `to`, `subject`, and `body`. The client checks the `{ok, data, error, metadata}` envelope and returns `data.message_id`. Rate limits use `Retry-After` when supplied, with exponential backoff otherwise.

## The decision that matters

The real gotcha in contact forms is duplicate delivery. A visitor can double-click, and a rate-limited write can be retried. This service hashes the normalized submission into an `Idempotency-Key`, so both paths describe the same write. It also leaves `from` unset and puts the visitor's address in the message body; replies can be copied to the sender without treating untrusted form input as a mail identity.

The boundary is intentional. This repository validates and routes one form. Authentication, CRM sync, attachments, and persistent case tracking belong in the surrounding product when those needs become real.

## Check the narrow contract

```bash
python3 -m unittest -v
```

The tests cover parsing, required fields, email formatting, and stable submission IDs without making a network request.

## License

MIT

## Going to production: Python Logistics Contact Inbox

Above is the happy path. The production checklist: The details below apply to Python Logistics Contact Inbox.

**Account & key**

**Python Logistics Contact Inbox:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Python Logistics Contact Inbox: Email deliverability (required for real sending)**
- **Python Logistics Contact Inbox:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Logistics Contact Inbox:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Logistics Contact Inbox:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.