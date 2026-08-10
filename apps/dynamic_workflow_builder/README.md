# Dynamic Workflow Builder

Smart approval engine for Frappe / ERPNext with dynamic rules, visual workflow builder, SLA tracking, escalation, and delegation.

## Install

```bash
cd /path/to/bench
./env/bin/pip install -e apps/dynamic_workflow_builder
bench --site <site> install-app dynamic_workflow_builder
```

## Quick test (Quotation example)

1. Open **DWB Approval Rule** → New
2. DocType: **Quotation**, Trigger: **Submit**
3. Condition: `grand_total` `>` `100000`
4. Level 1: Role Based → **Sales Manager**, SLA 24h
5. Level 2: Specific User → CEO user, SLA 48h
6. Submit a Quotation above ₹1,00,000
7. Check **Approval Center** and approve from form buttons

## Modules

- Approval Rule Builder with conditions & levels
- Visual Workflow Builder page
- Automatic Approval Request creation on Save/Submit/Update
- Approve / Reject / Delegate / Request Changes from any form
- Delegation, SLA, Escalation (hourly scheduler)
- Approval Center dashboard & reports

## Roles

- **Approval Manager** — rules, delegation, reports
- **Approver** — approve/reject/delegate
- **Approval Employee** — view own requests
