# BOQ DocType — Field Reference

This document explains **every field** on the **BOQ** DocType and its child table **BOQ Item** in the BOQ Management app.

---

## DocType Overview

| Property | Value |
|----------|-------|
| **DocType Name** | BOQ |
| **Module** | BOQ Management |
| **Type** | Submittable document |
| **Naming** | Naming Series (`BOQ-.YYYY.-.#####`) |
| **Child Table** | BOQ Item (labelled **Components** on the form) |
| **Purpose** | Project-based Bill of Quantities with rate buildup, overheads, and final rate per unit |

---

## Form Sections

The BOQ form is divided into five logical sections:

1. **Header** — project and document identity  
2. **Components** — line-item breakdown (child table)  
3. **Rate Buildup Summary** — read-only visual summary  
4. **Costing** — sub total, overheads, contractor profit  
5. **Final Rate** — final rate per unit and remarks  

---

# Part A — BOQ Header Fields

## 1. Series (`naming_series`)

| | |
|---|---|
| **Label** | Series |
| **Field Type** | Select |
| **Required** | No (defaults automatically) |
| **Default** | `BOQ-.YYYY.-.#####` |
| **Read Only** | No |

**What it does**  
Controls how the BOQ document ID is generated when you save a new record.

**Example output**  
`BOQ-2026-00001`, `BOQ-2026-00002`

**When to change**  
Only if your company uses a different numbering convention. Configure the default series in **BOQ Settings**.

---

## 2. Customer (`customer`)

| | |
|---|---|
| **Label** | Customer |
| **Field Type** | Link → Customer (ERPNext) |
| **Required** | Yes |
| **List View** | Yes |
| **Filter** | Yes |

**What it does**  
Links the BOQ to the client / customer for whom the estimate is prepared.

**How to use**  
Select an existing ERPNext Customer. Create new customers via **Selling → Customer**.

**Why it matters**  
Every BOQ is tied to a business relationship. Used for reporting, filtering, and future quotation / invoice linkage.

---

## 3. Project (`project`)

| | |
|---|---|
| **Label** | Project |
| **Field Type** | Link → Project (ERPNext) |
| **Required** | Conditional (mandatory if enabled in BOQ Settings) |
| **List View** | Yes |
| **Filter** | Yes |

**What it does**  
Links the BOQ to a specific construction project. This makes the BOQ **project-based**, not a generic price list.

**How to use**  
Select the ERPNext Project (e.g. `ABC Tower – Phase 1`). Create projects via **Projects → Project**.

**Validation**  
If **BOQ Settings → Project Mandatory on BOQ** is enabled, saving without a Project will show an error.

**Why it matters**  
One customer may have multiple projects. Each BOQ should belong to exactly one project scope.

---

## 4. Company (`company`)

| | |
|---|---|
| **Label** | Company |
| **Field Type** | Link → Company (ERPNext) |
| **Required** | Yes |
| **Default** | User's default company (auto-filled on save) |

**What it does**  
Identifies which legal entity / branch is preparing this BOQ.

**How to use**  
Auto-filled from your user defaults. Change only for multi-company setups.

**Why it matters**  
Currency, accounts, and permissions are company-specific in ERPNext.

---

## 5. Primary Category (`boq_category`)

| | |
|---|---|
| **Label** | Primary Category |
| **Field Type** | Link → BOQ Category |
| **Required** | No |
| **List View** | Yes |

**What it does**  
Sets the main system type for this BOQ (e.g. Metal Roofing, Façade Systems, Louvers).

**How to use**  
- Select the primary scope of work  
- Required before using **Load Category Template** button  
- Optional for **Load Rate Buildup Template** (per-m² buildup)

**Examples**  
`Metal Roofing`, `Insulated Metal Roofing`, `Façade Systems`

**Why it matters**  
Helps classify BOQs and loads the correct item master template for that system.

---

## 6. BOQ Date (`boq_date`)

| | |
|---|---|
| **Label** | BOQ Date |
| **Field Type** | Date |
| **Required** | No (defaults to today) |
| **Default** | Today |
| **List View** | Yes |

**What it does**  
The date the BOQ was prepared or issued.

**How to use**  
Auto-set to today's date on new documents. Change for backdated or future-dated estimates.

**Why it matters**  
Used for sorting, reporting, and version tracking of estimates over time.

---

## 7. Status (`status`)

| | |
|---|---|
| **Label** | Status |
| **Field Type** | Select |
| **Required** | No |
| **Default** | Draft |
| **Read Only** | Yes |
| **List View** | Yes |

**Options**

| Status | When set |
|--------|----------|
| **Draft** | New or unsaved BOQ |
| **Submitted** | After clicking Submit |
| **Approved** | Can be set manually for internal workflow |
| **Cancelled** | After document is cancelled |

**What it does**  
Shows the lifecycle stage of the BOQ. Updated automatically on submit and cancel.

---

# Part B — Components Table (`items`)

The **Components** field is a child table (DocType: **BOQ Item**). Each row is one line in the rate buildup or quantity estimate.

## Child Table: BOQ Item — Field Reference

### 8. Sr (`sr`)

| | |
|---|---|
| **Label** | Sr |
| **Field Type** | Integer |
| **Required** | No (auto-set) |
| **Read Only** | Effectively yes (auto-numbered) |

**What it does**  
Serial number of the line item (1, 2, 3…). Auto-assigned on save in row order.

---

### 9. Component (`item_description`)

| | |
|---|---|
| **Label** | Component |
| **Field Type** | Data (text) |
| **Required** | Yes |
| **List View** | Yes |

**What it does**  
The name / description of the component, material, labour, or equipment on this line.

**Examples**  
- `Standing Seam Aluminium Sheet (0.9 mm)`  
- `Thermal Insulation (50 mm Glass Wool)`  
- `Clips & Fasteners`  
- `Labour (Installation)`  

**How to use**  
- Type manually for rate buildup lines  
- Auto-filled when selecting **Item Master**  

---

### 10. Unit (`uom`)

| | |
|---|---|
| **Label** | Unit |
| **Field Type** | Link → UOM |
| **Required** | Yes |
| **List View** | Yes |

**What it does**  
Unit of measurement for this component line.

**Common values in BOQ Management**

| UOM | Used for |
|-----|----------|
| **m2** | Area items — sheets, insulation, labour per m² |
| **Set** | Kits — clips & fasteners |
| **LS** | Lump sum — sealant & accessories |
| **Meter** | Flashing, gutter, trim |
| **Nos** | Individual pieces, vents, anchors |
| **Kg** | Steel, purlins |

**How to use**  
Select from ERPNext UOM list. App installs `m2`, `Set`, and `LS` by default.

---

### 11. Qty (`qty`)

| | |
|---|---|
| **Label** | Qty |
| **Field Type** | Float |
| **Required** | No |
| **Default** | 1 |
| **Precision** | 2 decimal places |
| **List View** | Yes |

**What it does**  
Quantity for this component line.

**How to use**

| Scenario | Typical Qty |
|----------|-------------|
| Per-m² rate buildup | `1.00` on every line |
| Project BOQ with drawings | Actual quantity (e.g. `1200` m²) |
| Lump sum item | `1.00` |

**Effect on calculation**  
`Amount = Qty × Rate`

---

### 12. Rate (₹) (`rate`)

| | |
|---|---|
| **Label** | Rate (₹) |
| **Field Type** | Currency |
| **Required** | No |
| **List View** | Yes |

**What it does**  
Unit rate in company currency (₹) for one unit of the component.

**Examples**  
- Roof sheet: `1450` per m2  
- Clips: `180` per Set  
- Sealant: `45` per LS  

**How to use**  
- Enter manually  
- Auto-filled from **BOQ Item Master** default rate  
- Pre-filled by **Load Rate Buildup Template**  

---

### 13. Amount (₹) (`amount`)

| | |
|---|---|
| **Label** | Amount (₹) |
| **Field Type** | Currency |
| **Required** | No |
| **Read Only** | Yes |
| **List View** | Yes |

**What it does**  
Line total. Calculated automatically.

**Formula**  
```
Amount = Qty × Rate
```

**Example**  
Qty `1` × Rate `1450` = Amount `₹1,450`

---

### 14. Category (`boq_category`) — optional row field

| | |
|---|---|
| **Label** | Category |
| **Field Type** | Link → BOQ Category |
| **Required** | No |
| **In grid** | Hidden (expand row to see) |

**What it does**  
Links this line to a BOQ Category master. Used when loading items from the item master.

**How to use**  
Optional for simple rate buildup lines. Required when using master-based item selection.

---

### 15. Sub Category (`boq_sub_category`) — optional row field

| | |
|---|---|
| **Label** | Sub Category |
| **Field Type** | Link → BOQ Sub Category |
| **Required** | No |

**What it does**  
Further classifies the line (Roof Sheet, Flashing, Fasteners, Labour, etc.).

**Filter behaviour**  
Only sub-categories belonging to the selected **Category** are shown.

---

### 16. Item Master (`boq_item_master`) — optional row field

| | |
|---|---|
| **Label** | Item Master |
| **Field Type** | Link → BOQ Item Master |
| **Required** | No |

**What it does**  
Links the line to a pre-defined standard item. Selecting an item auto-fills:

- Component (item name)  
- Specification  
- Unit  
- Rate  
- Category and Sub Category (if empty)  

**Filter behaviour**  
Filtered by selected Category and Sub Category.

---

### 17. Specification (`specification`) — optional row field

| | |
|---|---|
| **Label** | Specification |
| **Field Type** | Small Text |
| **Required** | No |

**What it does**  
Technical specification or notes for the component (e.g. `0.5 mm TCT`, `50 mm Glass Wool`).

**How to use**  
Optional detail field. Auto-filled from Item Master when linked.

---

# Part C — Rate Buildup Summary

## 18. Rate Summary (`rate_summary_html`)

| | |
|---|---|
| **Label** | Rate Summary |
| **Field Type** | HTML (read-only display) |
| **Required** | No |
| **Editable** | No |

**What it does**  
Displays a formatted table summarising all component lines plus costing totals. Updates live as you edit the BOQ.

**Shows**

| Column | Source |
|--------|--------|
| Component | `item_description` |
| Unit | `uom` |
| Qty | `qty` |
| Rate (₹) | `rate` |
| Amount (₹) | `amount` |
| Sub Total | `sub_total` |
| Overheads | `overhead_percent` + `overhead_amount` |
| Contractor Profit | `contractor_profit_percent` + `contractor_profit_amount` |
| Final Rate Per [UOM] | `final_rate` + `final_rate_uom` |

**Why it matters**  
Provides a printable, presentation-ready rate buildup view matching standard EPC estimating format.

---

# Part D — Costing Fields

## 19. Sub Total (`sub_total`)

| | |
|---|---|
| **Label** | Sub Total |
| **Field Type** | Currency |
| **Required** | No |
| **Read Only** | Yes |

**What it does**  
Sum of all component line amounts before overheads and profit.

**Formula**  
```
Sub Total = Sum of all Amount (₹) in Components table
```

**Example**  
7 lines totalling ₹2,520

---

## 20. Overheads (%) (`overhead_percent`)

| | |
|---|---|
| **Label** | Overheads (%) |
| **Field Type** | Percent |
| **Required** | No |
| **Default** | 10 |

**What it does**  
Percentage added to sub total for site overheads, supervision, indirect costs, etc.

**How to use**  
Enter your company's standard overhead %. Default comes from **BOQ Settings**.

**Effect**  
Recalculates **Overheads Amount** and **Final Rate** immediately.

---

## 21. Overheads Amount (`overhead_amount`)

| | |
|---|---|
| **Label** | Overheads Amount |
| **Field Type** | Currency |
| **Required** | No |
| **Read Only** | Yes |

**Formula**  
```
Overheads Amount = Sub Total × Overheads (%) ÷ 100
```

**Example**  
Sub Total ₹2,520 × 10% = **₹252**

---

## 22. Contractor Profit (%) (`contractor_profit_percent`)

| | |
|---|---|
| **Label** | Contractor Profit (%) |
| **Field Type** | Percent |
| **Required** | No |
| **Default** | 15 |

**What it does**  
Percentage profit margin applied on the sub total.

**How to use**  
Enter your target profit %. Default comes from **BOQ Settings**.

**Note**  
Profit is calculated on **Sub Total**, not on Sub Total + Overheads.

---

## 23. Contractor Profit Amount (`contractor_profit_amount`)

| | |
|---|---|
| **Label** | Contractor Profit Amount |
| **Field Type** | Currency |
| **Required** | No |
| **Read Only** | Yes |

**Formula**  
```
Contractor Profit Amount = Sub Total × Contractor Profit (%) ÷ 100
```

**Example**  
Sub Total ₹2,520 × 15% = **₹378**

---

# Part E — Final Rate & Remarks

## 24. Final Rate UOM (`final_rate_uom`)

| | |
|---|---|
| **Label** | Final Rate UOM |
| **Field Type** | Link → UOM |
| **Required** | No |
| **Default** | From BOQ Settings (typically `m2`) |

**What it does**  
Defines the unit for the final rate display (e.g. cost **per m2**, per Set, per LS).

**How to use**  
Set to `m2` for area-based system rates. Shown in the summary as **Final Rate Per m2**.

---

## 25. Final Rate (`final_rate`)

| | |
|---|---|
| **Label** | Final Rate |
| **Field Type** | Currency |
| **Required** | No |
| **Read Only** | Yes |
| **Bold** | Yes |

**What it does**  
The all-in rate after materials, labour, equipment, overheads, and profit.

**Formula**  
```
Final Rate = Sub Total + Overheads Amount + Contractor Profit Amount
```

**Example**  
₹2,520 + ₹252 + ₹378 = **₹3,150 per m2**

**How to use**  
- For per-m² buildup (Qty = 1 on all lines): this is your **selling rate per m2**  
- For project BOQ: multiply by total area or use as unit rate in quotation  

---

## 26. Total Cost (`total_cost`)

| | |
|---|---|
| **Label** | Total Cost |
| **Field Type** | Currency |
| **Required** | No |
| **Read Only** | Yes |
| **Hidden on form** | Yes (shown in list view) |

**What it does**  
Mirrors **Final Rate**. Used in BOQ list view for quick reference.

**Formula**  
```
Total Cost = Final Rate
```

---

## 27. Remarks (`remarks`)

| | |
|---|---|
| **Label** | Remarks |
| **Field Type** | Small Text |
| **Required** | No |

**What it does**  
Free-text notes for internal use or estimate assumptions.

**Examples**  
- `Rates valid for 30 days`  
- `Excludes scaffolding`  
- `Based on 0.9 mm aluminium standing seam system`  

---

# Part F — System Fields (Automatic)

These fields exist on every Frappe document and are not shown as editable form fields:

| Field | Description |
|-------|-------------|
| **name** | Document ID (e.g. `BOQ-2026-00001`) |
| **owner** | User who created the BOQ |
| **creation** | Date/time created |
| **modified** | Date/time last modified |
| **modified_by** | User who last modified |
| **docstatus** | 0 = Draft, 1 = Submitted, 2 = Cancelled |

---

# Part G — Buttons & Actions

| Button | When visible | What it does |
|--------|--------------|--------------|
| **Load Rate Buildup Template** | Draft BOQ, after save | Loads 7 Standing Seam per-m² component lines |
| **Load Category Template** | Draft BOQ, after save | Loads all Item Master rows for Primary Category |
| **Submit** | Draft BOQ with valid data | Locks BOQ, sets Status = Submitted |
| **Cancel** | Submitted BOQ | Sets Status = Cancelled |

---

# Part H — Complete Calculation Chain

```
For each Component row:
    Amount = Qty × Rate

Sub Total = Σ (all Amounts)

Overheads Amount     = Sub Total × Overheads % ÷ 100
Profit Amount        = Sub Total × Contractor Profit % ÷ 100

Final Rate           = Sub Total + Overheads Amount + Profit Amount
Total Cost           = Final Rate
```

### Worked example

| Step | Value |
|------|-------|
| Line amounts sum | ₹2,520 |
| Overheads 10% | ₹252 |
| Profit 15% | ₹378 |
| **Final Rate per m2** | **₹3,150** |

---

# Part I — Field Dependency Map

```
Customer ──────────────┐
Project ───────────────┤
Company ───────────────┼──► BOQ Header
Primary Category ──────┤
BOQ Date / Status ─────┘
         │
         ▼
Components (BOQ Item child table)
  Component + Unit + Qty + Rate
         │
         ▼
    Amount (auto)
         │
         ▼
    Sub Total (auto)
         │
    ┌────┴────┐
    ▼         ▼
Overheads %  Profit %
    │         │
    ▼         ▼
Overheads ₹  Profit ₹
         │
         ▼
    Final Rate (auto)
    Final Rate UOM
```

---

# Part J — Quick Field Checklist (New BOQ)

| # | Field | Action |
|---|-------|--------|
| 1 | Customer | Select client |
| 2 | Project | Select project |
| 3 | Company | Verify (auto) |
| 4 | Primary Category | Select system (for category template) |
| 5 | BOQ Date | Verify (auto = today) |
| 6 | Components | Load template or add rows |
| 7 | Unit | Use m2 / Set / LS as applicable |
| 8 | Qty | 1 for per-m² buildup, or actual qty |
| 9 | Rate | Enter or accept from master |
| 10 | Overheads % | Default 10% or adjust |
| 11 | Contractor Profit % | Default 15% or adjust |
| 12 | Final Rate UOM | Set to m2 |
| 13 | Final Rate | Review auto-calculated value |
| 14 | Remarks | Add notes if needed |
| 15 | Submit | Finalise BOQ |

---

## Related Documents

- [README_EXPLANATION.md](README_EXPLANATION.md) — full app usage guide  
- [README.md](README.md) — install instructions  
