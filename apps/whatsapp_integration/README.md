# WhatsApp Integration

Send and receive WhatsApp messages from Frappe / ERPNext using Meta's WhatsApp Cloud API.

## Install

```bash
cd /path/to/bench
./env/bin/pip install -e apps/whatsapp_integration
bench --site <site> install-app whatsapp_integration
```

## Setup

1. Open **WhatsApp Settings** in Desk
2. Enter:
   - **Access Token** (Meta permanent / system user token)
   - **Phone Number ID**
   - **Business Account ID** (WABA ID)
   - **App ID**
   - **Webhook Verify Token** (any secret string you choose)
3. Enable the integration and Save
4. In Meta Developer Portal → WhatsApp → Configuration, set webhook URL:

```
https://<your-site>/api/method/whatsapp_integration.api.webhook.webhook
```

Subscribe to: `messages`

## Send a message (Python)

```python
import frappe
from whatsapp_integration.api.message import send_whatsapp_message

send_whatsapp_message(
    to="919876543210",
    message="Hello from Frappe!",
)
```

## Send a template

```python
send_whatsapp_message(
    to="919876543210",
    template="hello_world",
    language_code="en_US",
)
```

## Desk API

`POST /api/method/whatsapp_integration.api.message.send_whatsapp_message`

| Parameter | Description |
|-----------|-------------|
| `to` | Recipient in international format without `+` |
| `message` | Free-form text (24h window) |
| `template` | Template name (optional) |
| `language_code` | Template language (default `en_US`) |
| `components` | JSON string of template components (optional) |

## Roles

- **System Manager** — full access to settings and messages
- **WhatsApp Manager** — send messages, view logs
