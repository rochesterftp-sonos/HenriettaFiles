# Henrietta Dispatch - Project Plan

> **Last Updated:** February 2, 2026
> **Status:** Planning Phase

---

## Project Overview

**Goal:** Replace the legacy WWDispatch List Excel workbook (created by Mike B, now unsupported) with a standalone BI-style web application.

**Primary User:** Kyle (Production Planner)
**Other Users:** Amy (Purchasing), Richard (Production Supervisor), Dan/Zach (Shipping)

**Data Source:** Epicor (on-prem) via BAQ exports to CSV/XML files

---

## Decisions Made

### Technology Stack
- **Framework:** Python + Streamlit
- **Database:** SQLite (for notes/comments)
- **Data Source:** CSV/XML files from Epicor BAQ exports
- **Repository:** GitHub (private) - `henrietta-dispatch`

### Why Streamlit?
- Fast to develop
- Handles data tables with color coding
- Supports filtering via sidebar
- Can integrate notes/comments with database
- Runs in browser (accessible to multiple users)
- Can read CSV/XML directly

---

## Data Files Available

Located in: `OperationsData/Data/`

### Core Data Files
| File | Purpose | Size |
|------|---------|------|
| `Weco-West-MB_Shop_Orders.csv` | Main shop orders | 161 KB |
| `Weco-West-ESC-OrderBacklog.csv` | Order backlog | 40 KB |
| `WecoWest-CustomerShipments.csv` | Shipments | 2.9 MB |
| `Weco-West-MB_Open_PO.csv` | Open POs | 31 KB |
| `PK-LaborHistory.csv` | Labor tracking | 5.5 MB |
| `Weco-West_BookSalesOrderSumDtl.csv` | Bookings | 332 KB |
| `WECO-West-PartCost.csv` | Part costs | 1.5 MB |

### Supporting Files
| File | Purpose |
|------|---------|
| `MB Comments.xlsx` | Operations comments (Kyle's notes) |
| `Purch Comments.xlsx` | Purchasing comments (Amy's notes) |
| `Customer Names.xlsx` | Customer name lookup |
| `Weco-CustomerDate.csv` | Customer date lookup |

---

## Kyle's Daily Workflow (From Meeting Transcript)

Kyle's morning routine takes 15-30 minutes and involves 3 mental checklists:

### 1. Engineering Check
- Filter Orders tab for **unengineered jobs** (light blue text)
- These need engineering before manufacturing can start
- May generate emails or calls to engineering

### 2. What's on the Floor
- Filter for jobs **in work** (green highlighting in Column A)
- Check **last labor date** (Column W) - was there activity yesterday?
- If no activity for 2+ weeks, might be out for subcontracting

### 3. Inventory Check
- Check **remaining quantity** (Column H)
- Check **inventory on hand** (Column Y)
- Green = can ship full order
- Red = insufficient inventory
- Also checks material on hand for future jobs

### Key Features He Relies On
- Quick links to drawings via part number
- Links to purchase orders (for rev number verification - CRITICAL)
- Notes/comments per job (saved via Control-K macro)
- Color-coded status indicators
- Filtering by ESI vs. non-ESI jobs

---

## Application Views (Planned)

### Phase 1 - Core (Kyle's Daily Workflow)
1. **Orders Dashboard** - Main view with all filters
   - Engineering status filter
   - In-work status filter
   - Inventory check indicators
   - Material on hand view
   - Notes/comments per job
   - Hyperlinks to drawings/POs

2. **Jobs View** - Operations and labor by work center

3. **Shipped View** - What's gone out, pull-in analysis

### Phase 2 - Extended
4. **Shortages View** - Material shortages (Amy/Purchasing)
5. **Labor Hours View** - Labor tracking (Richard)
6. **KPI Dashboard** - On-time delivery, sales $/labor hour (Pete)

---

## Color Coding Scheme

| Color | Meaning | Used For |
|-------|---------|----------|
| Light Blue (`#ADD8E6`) | Unengineered | Jobs needing engineering |
| Green (`#90EE90`) | In Work / Can Ship | Active jobs, sufficient inventory |
| Light Red (`#FFB6C1`) | Cannot Ship | Insufficient inventory |
| Sky Blue (`#87CEEB`) | ESI Job | ESI-related work |
| Red (`#FF6B6B`) | Late | Past due date |
| Yellow (`#FFD93D`) | Warning | Approaching due date |

---

## Project Structure

```
henrietta-dispatch/
├── app/
│   ├── main.py              # Main Streamlit app
│   ├── pages/
│   │   ├── orders.py        # Orders Dashboard
│   │   ├── jobs.py          # Jobs View
│   │   └── shipped.py       # Shipped View
│   ├── components/
│   │   ├── filters.py       # Sidebar filters
│   │   ├── data_table.py    # Color-coded tables
│   │   └── notes.py         # Notes/comments component
│   └── utils/
│       ├── data_loader.py   # Load CSV/XML files
│       └── database.py      # SQLite for notes
├── config/
│   └── settings.py          # Configuration
├── data/                    # CSV/XML files (not in git)
├── database/                # SQLite database
├── docs/
│   └── PROJECT_PLAN.md      # This file
└── requirements.txt
```

---

## Next Steps

1. [ ] Create GitHub repository (private, named `henrietta-dispatch`)
2. [ ] Push initial project structure
3. [ ] Analyze CSV column structures
4. [ ] Build Orders Dashboard prototype
5. [ ] Test with Kyle
6. [ ] Iterate based on feedback

---

## Reference Documents

- `WWDispatch_List_Analysis.md` - Detailed analysis of the Excel workbook
- `WWDispatch_Data_Sources.md` - List of all data source file paths
- `Weco hen spreadsheet meeting 1.txt` - Original meeting transcript

---

## Notes

- Pete (leadership) has "inherent distrust" of Mike B's tools - new app needs to be trustworthy
- Ontario facility uses different workflow (per work center dispatch) - future consideration
- Margin data in current system is unreliable (burden rates not maintained)
