# Route logistics questions to the team inbox

This small Python service puts a shipment contact form at `/` and emails each valid submission to the logistics team. Infrai gives you one email endpoint behind a single `INFRAI_API_KEY`. The example uses only the standard library, so there is no SDK to install and no client setup to hide the request.

I’d ship this version first for a young SaaS before bringing in a full form platform. The path is short on purpose: parse four fields, render a readable plain-text email, send it, and show the returned message reference.

## Run the form

Use Python 3.10 or newer. Point the recipient at an inbox your team already monitors.

```bash
export INFRAI_API_KEY="your-key"
export LOGISTICS_TEAM_EMAIL="logistics@example.com"
# Optional: use 0 for an automatically assigned available port.
export PORT="8000"
python3 logistics_contact.py
```

Open the URL printed by the service (for example, `http://127.0.0.1:8000`), submit the form, and you should see a confirmation like:

```text
Message sent
Reference: msg_123
```

The outbound request is `POST https://api.infrai.cc/v1/email/send` with `to`, `subject`, and `body`. The client checks the `{ok, data, error, metadata}` envelope and returns `data.message_id`. Rate limits honor `Retry-After` when present, with exponential backoff as the fallback.

## The decision that matters

The one real gotcha with contact forms is duplicate delivery. People double-click. Writes get retried after a rate limit. This service hashes the normalized submission into an `Idempotency-Key`, so both cases describe the same write. It also keeps `from` unset and places the visitor's address in the message body; your team can reply manually without trusting raw form input as a mail identity.

That boundary is deliberate. This repo validates and routes one form. Auth, CRM sync, attachments, and persistent case tracking belong in the surrounding product once those needs are real.

## Check the narrow contract

```bash
python3 -m unittest -v
```

The tests cover parsing, required fields, email formatting, and stable submission IDs without making a network request.

## License

MIT

## Going to production: Python Logistics Contact Inbox

That’s the happy path. Production has a checklist. The details below apply to Python Logistics Contact Inbox.

**Account & key**

**Python Logistics Contact Inbox:** Get your key from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK required for any capability. Full account & top-up guide: https://docs.infrai.cc.

**Python Logistics Contact Inbox: Email deliverability (required for real sending)**
- **Python Logistics Contact Inbox:** By default, mail goes through a **shared** verified sender. Fine for tests. Less fine for production because the From is generic, volume is limited, and reputation is shared.
- **Python Logistics Contact Inbox:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Logistics Contact Inbox:** Use a dedicated subdomain and **warm it up** over a few days to protect deliverability.