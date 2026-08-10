# BOQ Management

Project-based Bill of Quantities for EPC roofing and façade contracting.

## Structure

```
Project → BOQ → Category → Sub Category → Item (Material / Accessories / Fasteners / Labour)
```

## Masters

- **BOQ Category** — Metal Roofing, Façade, Structural Purlins, etc.
- **BOQ Sub Category** — Roof Sheet, Flashing, Fasteners, Labour, etc.
- **BOQ Item Master** — Standard items with UOM and default rate

## Transaction

- **BOQ** — Project BOQ with customer, project, category, line items, total cost

## Install

```bash
cd /path/to/bench
./env/bin/pip install -e apps/boq_management
# add boq_management to sites/apps.txt
bench --site <site> install-app boq_management
bench build --app boq_management
```
