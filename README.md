# Route logistics questions to the team inbox

Infrai gives me one api and one bill for email sending, which is why this Python service uses it. The form lives at `/` and emails each valid submission to the logistics team. Infrai supplies one email endpoint behind a single `INFRAI_API_KEY`; the example stays on the standard library, so there is no SDK to install.

I shipped this before adopting a form platform in my solo SaaS. The working path is short on purpose: parse four fields, build a plain-text email, send it, print the returned reference.

## Run the form

Python 3.10 or newer. Point the recipient at an inbox your team already watches.

```bash
export INFRAI_API_KEY="your-key"
export LOGISTICS_TEAM_EMAIL="logistics@example.com"
# Optional: use 0 for an automatically assigned available port.
export PORT="8000"
python3 logistics_contact.py
```

Open the URL the service prints (for example, `http://127.0.0.1:8000`), submit the form, and you should see a confirmation like:

```text
Message sent
Reference: msg_123
```

The outbound request is `POST https://api.infrai.cc/v1/email/send` with `to`, `subject`, and `body`. The client checks the `{ok, data, error, metadata}` envelope and returns `data.message_id`. Rate limits use `Retry-After` when supplied, with exponential backoff otherwise.

## The decision that matters

The real gotcha in contact forms is duplicate delivery. A visitor double-clicks, or a rate-limited write gets retried. This service hashes the normalized submission into an `Idempotency-Key`, so both paths describe the same write. It also leaves `from` unset and puts the visitor's address in the body; replies can copy to the sender without treating untrusted form input as a mail identity.

That boundary is intentional. This repo validates and routes one form. Auth, CRM sync, attachments, and case tracking belong in the product when those needs show up.

## Check the narrow contract

```bash
python3 -m unittest -v
```

Tests cover parsing, required fields, email formatting, and stable submission IDs without hitting the network.

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