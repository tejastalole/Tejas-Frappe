# BOQ Management — How It Works & How to Use It

This guide explains the **BOQ Management** app for EPC / contracting companies (roofing, façade, ceiling, structural systems). The BOQ is **project-based**, not product-catalog based — each BOQ belongs to a **Customer** and **Project**.

---

## 1. What This App Does

A **Bill of Quantities (BOQ)** lists every material, accessory, fastener, labour, and equipment item required for a construction project, with quantities, rates, and total cost.

This app helps you:

- Build **per-unit rate breakdowns** (e.g. cost per m²) with materials, labour, and equipment
- Maintain standard **categories**, **sub-categories**, and an **item master**
- Create **project BOQs** linked to ERPNext Customer and Project
- Auto-calculate line amounts, overheads, contractor profit, and **final rate**
- Load templates with one click (**Rate Buildup** or **Category**)

---

## 2. App Structure (Hierarchy)

```
BOQ Management
│
├── Masters (setup once, reuse on every project)
│     ├── BOQ Category          → Metal Roofing, Façade Systems, Louvers, etc.
│     ├── BOQ Sub Category      → Roof Sheet, Flashing, Fasteners, Labour, etc.
│     └── BOQ Item Master       → Roof Sheet 0.5 mm TCT, Gutter, Installation Labour, etc.
│
├── Transaction
│     └── BOQ                   → One BOQ per project / system estimate
│           ├── Components      → Component | Unit | Qty | Rate (₹) | Amount (₹)
│           ├── Rate Summary      → Visual buildup table
│           └── Costing           → Sub Total → Overheads → Profit → Final Rate
│
└── Setup
      └── BOQ Settings          → Defaults, UOM, overhead %, profit %
```

### BOQ form layout (rate buildup style)

```
┌─────────────────────────────────────────────────────────────────┐
│  COMPONENTS TABLE                                               │
│  Component              | Unit | Qty  | Rate (₹) | Amount (₹)  │
│  Standing Seam Sheet    | m2   | 1.00 | 1,450    | 1,450       │
│  Thermal Insulation     | m2   | 1.00 | 320      | 320         │
│  Clips & Fasteners      | Set  | 1.00 | 180      | 180         │
│  Sealant & Accessories  | LS   | 1.00 | 45       | 45          │
│  Labour (Installation)  | m2   | 1.00 | 350      | 350         │
├─────────────────────────────────────────────────────────────────┤
│  RATE BUILDUP SUMMARY        (auto-generated visual table)      │
├─────────────────────────────────────────────────────────────────┤
│  Sub Total                                        ₹ 2,520       │
│  Overheads (10%)                                  ₹   252       │
│  Contractor Profit (15%)                          ₹   378       │
│  Final Rate Per m2                                ₹ 3,150       │
└─────────────────────────────────────────────────────────────────┘
```

### How data flows

```
1. You define masters (optional) OR use rate buildup lines directly
2. You create a BOQ for a Project
3. You add component lines (template or manual) with Qty = 1 per m² buildup
4. System calculates Amount, Sub Total, Overheads, Profit, Final Rate
5. You submit the BOQ when ready
```

---

## 3. DocTypes Explained

| DocType | What it is | Example |
|---------|------------|---------|
| **BOQ Category** | Main system / scope of work | Metal Roofing, Structural Purlins |
| **BOQ Sub Category** | Grouping inside a category | Roof Sheet, Flashing, Labour |
| **BOQ Item Master** | Standard item with UOM and default rate | Roof Sheet 0.5 mm TCT — m2 |
| **BOQ** | Project estimate / rate buildup document | BOQ-2026-00001 for ABC Tower |
| **BOQ Item** | One component line | Standing Seam Sheet — m2 × ₹1,450 |
| **BOQ Settings** | Global app configuration | Overhead %, profit %, default UOM |

### Pre-loaded categories (after install)

1. Metal Roofing  
2. Insulated Metal Roofing  
3. Structural Purlins  
4. Structural Decking  
5. Fire Protection Systems  
6. Metal False Ceiling  
7. Façade Systems  
8. Louvers  
9. Add-On Roofs  

Each category comes with relevant sub-categories and sample items (76+ items seeded).

---

## 4. Units of Measurement (UOM)

The app ships with BOQ-specific UOMs:

| UOM | Use for | Example |
|-----|---------|---------|
| **m2** | Area-based components (per m² buildup) | Roof sheet, insulation, labour |
| **Set** | Fixed kit / assembly | Clips & fasteners |
| **LS** | Lump sum items | Sealant & accessories |

Other ERPNext UOMs (Meter, Nos, Kg, etc.) also work. Ensure UOMs exist under **Stock → UOM**.

---

## 5. Costing Formula

| Field | Calculation |
|-------|-------------|
| **Amount (₹)** | Qty × Rate (per line) |
| **Sub Total** | Sum of all line amounts |
| **Overheads Amount** | Sub Total × Overheads % |
| **Contractor Profit Amount** | Sub Total × Contractor Profit % |
| **Final Rate** | Sub Total + Overheads + Contractor Profit |
| **Final Rate UOM** | Usually **m2** (cost per square metre) |

### Example (Standing Seam roof per m²)

| Component | Unit | Qty | Rate | Amount |
|-----------|------|-----|------|--------|
| Standing Seam Aluminium Sheet (0.9 mm) | m2 | 1 | 1,450 | 1,450 |
| Thermal Insulation (50 mm Glass Wool) | m2 | 1 | 320 | 320 |
| Vapour Barrier | m2 | 1 | 55 | 55 |
| Clips & Fasteners | Set | 1 | 180 | 180 |
| Sealant & Accessories | LS | 1 | 45 | 45 |
| Labour (Installation) | m2 | 1 | 350 | 350 |
| Equipment (Lifting, Tools, Machines) | m2 | 1 | 120 | 120 |
| **Sub Total** | | | | **2,520** |
| Overheads (10%) | | | | **252** |
| Contractor Profit (15%) | | | | **378** |
| **Final Rate Per m2** | | | | **₹3,150** |

---

## 6. Roles

| Role | Can do |
|------|--------|
| **BOQ Manager** | Full access — create, edit, submit, cancel BOQ and masters |
| **BOQ User** | Create and edit BOQ and masters |
| **System Manager** | Full access |

Assign roles: **User** → select user → **Roles** → add `BOQ Manager` or `BOQ User`.

---

## 7. First-Time Setup

### Step 1 — Open the workspace

Desk → sidebar → **BOQ Management**

### Step 2 — Configure BOQ Settings

Go to **BOQ Settings** and set:

| Setting | Recommended value |
|---------|-------------------|
| Default Company | Your company |
| BOQ Naming Series | `BOQ-.YYYY.-.#####` |
| Project Mandatory on BOQ | Enabled |
| Default Overheads (%) | 10 |
| Default Contractor Profit (%) | 15 |
| Default Final Rate UOM | m2 |

### Step 3 — Review masters (optional)

- **BOQ Category** — 9 pre-loaded categories  
- **BOQ Sub Category** — grouped by category  
- **BOQ Item Master** — items with UOM and default rates  

Add or edit items for your company rates in **BOQ Item Master**.

---

## 8. How to Create a Rate Buildup BOQ (Per m²)

Use this when you need a **system rate per m²** (like Standing Seam roofing).

**Step 1 — Create Customer & Project (ERPNext)**

- **Selling → Customer** → e.g. `ABC Builders`
- **Projects → Project** → e.g. `ABC Tower – Phase 1`

**Step 2 — New BOQ**

1. **BOQ Management** → **BOQ** → **New**
2. Fill header: Customer, Project, Company, BOQ Date
3. Set **Final Rate UOM** = `m2`

**Step 3 — Load Rate Buildup Template**

1. Save the BOQ (draft)
2. Click **Templates → Load Rate Buildup Template**
3. Seven component lines are added (Standing Seam example)
4. Each line has **Qty = 1** for per-m² costing

**Step 4 — Review costing**

- **Components** table shows Component | Unit | Qty | Rate (₹) | Amount (₹)
- **Rate Buildup Summary** shows the visual summary table
- Adjust **Overheads (%)** and **Contractor Profit (%)** if needed
- **Final Rate** updates automatically

**Step 5 — Submit**

Click **Submit** when the rate buildup is final.

---

## 9. How to Create a Category-Based BOQ (Project Quantities)

Use this when you have **actual project quantities** (e.g. 1,200 m² roof area).

**Step 1 — New BOQ** with Primary Category = `Metal Roofing`

**Step 2 — Load Category Template**

1. Save the BOQ
2. Click **Templates → Load Category Template**
3. All Metal Roofing master items are added

**Step 3 — Enter project quantities**

| Component | Unit | Qty | Rate | Amount |
|-----------|------|-----|------|--------|
| Roof Sheet 0.5 mm TCT | m2 | 1200 | 450 | auto |
| Ridge Flashing | Meter | 180 | 120 | auto |
| Installation Labour | m2 | 1200 | 85 | auto |

Multiply final rate by area, or use lines with actual Qty for total project cost.

---

## 10. Adding Component Lines Manually

1. In the **Components** table, click **Add Row**
2. Enter **Component** name (e.g. `PUF Sandwich Panel`)
3. Select **Unit** — `m2`, `Set`, `LS`, `Meter`, `Nos`, etc.
4. Enter **Qty** (use `1` for per-m² buildup, or actual qty for project BOQ)
5. Enter **Rate (₹)** — amount calculates automatically

### Optional: link to Item Master

Expand the row to set **Category**, **Sub Category**, and **Item Master** — this auto-fills component name, unit, and rate.

### Cascading filters (when using masters)

- **Category** filters **Sub Category**
- **Sub Category** filters **Item Master**
- Selecting **Item Master** auto-fills component, unit, and rate

---

## 11. Managing Masters

### Add a new item

1. **BOQ Item Master** → **New**
2. Item Name: `Roof Sheet 0.7 mm TCT`
3. BOQ Category + Sub Category
4. Default UOM: `m2`
5. Default Rate: your standard rate

### Add a new sub-category

1. **BOQ Sub Category** → **New**
2. Name: `Insulation`, Category: `Metal Roofing`, Item Type: `Material`

### Add a new category

1. **BOQ Category** → **New**
2. Name: `Walkable Roof System`

---

## 12. UOM Reference

| Item type | Recommended UOM |
|-----------|-----------------|
| Roof sheets, panels, insulation, labour | **m2** |
| Clips, fastener kits | **Set** |
| Sealant, accessories (lump sum) | **LS** |
| Flashing, gutter, trim | Meter |
| Screws, vents, anchors | Nos |
| Purlins, steel | Kg / Ton |

---

## 13. BOQ Status Workflow

| Status | Meaning |
|--------|---------|
| **Draft** | BOQ is being prepared |
| **Submitted** | BOQ is finalized (docstatus = 1) |
| **Approved** | Internal approval tracking |
| **Cancelled** | BOQ was cancelled |

---

## 14. Real Project Example (Multi-System)

```
Project: Commercial Building – Roof & Façade

BOQ-2026-00001  →  Standing Seam rate buildup (per m2)
BOQ-2026-00002  →  Metal Roofing quantities (1,200 m2)
BOQ-2026-00003  →  Façade Systems (category template)
```

---

## 15. Tips & Best Practices

1. **Per m² buildup** — use Qty = 1 on each component line, then read **Final Rate Per m2**
2. **Project BOQ** — use actual quantities in the Components table
3. **Use Load Rate Buildup Template** for quick Standing Seam / system costing
4. **Use Load Category Template** for full category item lists
5. **Set overhead & profit in BOQ Settings** — defaults apply to every new BOQ
6. **Always link Project** — keeps BOQ project-based
7. **Review Rate Buildup Summary** before submit

---

## 16. Troubleshooting

| Issue | Solution |
|-------|----------|
| Workspace not visible | Refresh browser; check **BOQ Management** in PUBLIC sidebar |
| Project field required | Toggle in **BOQ Settings → Project Mandatory** |
| UOM m2 / Set / LS missing | Run seed: `bench --site site1.local execute boq_management.api.seed.run_seed` |
| Template buttons missing | Save BOQ first; only on draft (not submitted) |
| Final Rate not updating | Change a Qty or Rate, or edit Overheads / Profit % |
| Item not in dropdown | Check item is **Active** and matches Category + Sub Category |

---

## 17. Re-seed Master Data

```bash
cd /home/frappe/tejas
bench --site site1.local execute boq_management.api.seed.run_seed
```

Reloads categories, sub-categories, sample items, and UOMs (m2, Set, LS).

---

## 18. Quick Reference

| Task | Path |
|------|------|
| Create BOQ | BOQ Management → BOQ → New |
| Load per-m² template | BOQ → Templates → Load Rate Buildup Template |
| Load category items | BOQ → Templates → Load Category Template |
| Edit default rates | BOQ Item Master |
| Set overhead / profit defaults | BOQ Settings |
| View all BOQs | BOQ Management → BOQ (list) |

---

## 19. Summary

**BOQ Management** supports two estimating workflows:

**A. Rate Buildup (per m²)**
```
Components (Qty=1) → Sub Total → Overheads → Profit → Final Rate per m2
```

**B. Project BOQ (with quantities)**
```
Masters → Category Template → Actual Qty × Rate → Sub Total → Final Cost
```

It is built for **EPC contractors** who design, supply, and install roofing and façade systems. Every BOQ is tied to a **project**, supports **m2 / Set / LS** units, and produces a professional **rate buildup summary** ready for quoting and estimation.
