# Bulk Data Tools

Select a DocType and bulk-manage its records in Frappe / ERPNext.

## Features

1. **Count Records** — how many rows match
2. **Preview Sample** — show latest 20 names
3. **Export Names (CSV)** — download matching names before delete
4. **Delete All Matching** — delete every matching record (with Dry Run + type `DELETE`)
5. **Clear Recycle Bin** — permanently remove soft-deleted docs for that DocType
6. **Filters** — optional JSON filters + Draft/Submitted/Cancelled filter
7. **Protected DocTypes** — system list + your extra list cannot be deleted
8. **Operation Log** — audit trail of every action

## Install

```bash
cd /path/to/bench
./env/bin/pip install -e apps/bulk_data_tools
bench --site your-site install-app bulk_data_tools
```

## How to use (simple)

1. Desk → **Bulk Data Tools** → **Bulk Data Tool**
2. Select a **DocType**
3. Click **Count Records**
4. Keep **Dry Run** checked and click **Delete All Matching** to preview
5. Uncheck **Dry Run**, type `DELETE` in confirm box, click **Delete All Matching** again

## Safety

- Only **System Manager** / **Bulk Data Manager**
- Protected DocTypes: User, DocType, Company, Role, etc.
- Default mode is **Dry Run** (no real delete)
- Real delete requires typing **DELETE**
- Deletes run in batches (default 100)

## Filter example

```json
[["status", "=", "Draft"], ["company", "=", "My Company"]]
```
