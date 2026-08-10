# Frappe Flow

No-code automation builder for Frappe & ERPNext — Zapier / n8n style workflows.

## Install

```bash
cd /path/to/bench
./env/bin/pip install -e apps/frappe_flow
bench --site <site> install-app frappe_flow
```

## Quick test

1. Open **Frappe Flow** workspace → **Automation Center**
2. Install **Sales Quotation Follow-up Pack** template
3. Set DocType = Quotation, Trigger = on_submit, Status = Active
4. Open **Flow Builder** to customize nodes
5. Submit a Quotation — check **FF Flow Execution**

## AI Flow Builder

On **FF Flow Automation**, click **AI Generate Flow** and type:

```
When Quotation is submitted above 1 lakh, send WhatsApp to customer,
email Sales Manager, create follow-up after 3 days.
```

## Webhook API

```http
POST /api/method/frappe_flow.api.flow.webhook
?endpoint_path=frappe_flow/webhook/my-hook
Header: X-Flow-Secret: <secret>
```

## Roles

- **Flow Admin** — full access
- **Flow Designer** — build flows
- **Flow User** — view executions
