# Product Requirements Document (PRD)
# Henrietta Dispatch Application

> **Version:** 1.0
> **Date:** February 2, 2026
> **Status:** Ready for Development

---

## 1. Overview

### 1.1 Problem Statement
The Henrietta manufacturing facility relies on a legacy Excel workbook (WWDispatch List) created by a former employee. This workbook is unsupported, contains complex VBA macros, and poses a business continuity risk. Leadership does not trust data from unsupported tools.

### 1.2 Solution
Build a standalone web application that replicates Kyle's (Production Planner) daily workflow while providing a supported, maintainable platform.

### 1.3 Success Criteria
- Kyle can complete his morning workflow in ≤30 minutes
- Data is trusted by leadership
- Application is maintainable by IT/developers
- Zero learning curve for existing Excel users

---

## 2. Users & Personas

### Primary User: Kyle (Production Planner)
- **Daily workflow:** 15-30 minute morning review
- **Key needs:** Speed, color-coded status, filtering, notes
- **Current tool:** WWDispatch List Excel (Orders tab primarily)

### Secondary Users
| User | Role | Primary Need |
|------|------|--------------|
| Amy | Purchasing | Material shortages, PO tracking |
| Richard | Production Supervisor | Labor hours, idle time monitoring |
| Dan/Zach | Shipping | What's ready to ship, shipment tracking |
| Pete | Leadership | KPIs, on-time delivery, trustworthy data |

---

## 3. Features & Requirements

### 3.1 Core Features (MVP)

#### 3.1.1 Orders Dashboard
The primary view that replicates the Excel "Orders" tab.

**Data Display:**
- Excel-like grid layout (familiar, dense)
- Infinite scroll (load more as user scrolls)
- Auto-refresh every 5 minutes
- Last updated timestamp visible

**Columns to Display:**
| Column | Source Field | Notes |
|--------|--------------|-------|
| Job | `Job` | Primary identifier |
| Part | `Part` | Clickable → drawing link |
| Description | `Description` | Part description |
| Status | Calculated | Color-coded badge |
| Order Qty | `Selling Requested Qty` | |
| Completed | `Qty Completed` | |
| Due Date | `Due Date` | Highlight if past due |
| Need By | `Need By` | |
| Customer | `Name` | |
| Last Labor | From labor history | Date of last labor entry |
| Notes | From database | User-entered notes |
| Actions | - | 📄 Drawing, 📋 PO icons |

**Status Calculation Logic:**
```
IF Engineered = False THEN "Unengineered" (Light Blue)
ELSE IF Qty Completed > 0 THEN "In-Work" (Green)
ELSE IF Inventory >= Order Qty THEN "Can Ship" (Green)
ELSE IF Inventory > 0 THEN "Partial" (Yellow)
ELSE "Not Started" (Gray)
```

**Color Coding:**
| Status | Background Color | Hex Code |
|--------|-----------------|----------|
| Unengineered | Light Blue | `#ADD8E6` |
| In-Work | Light Green | `#90EE90` |
| Can Ship | Light Green | `#90EE90` |
| Partial Inventory | Yellow | `#FFD93D` |
| Past Due | Light Red | `#FFB6C1` |
| ESI Job | Sky Blue | `#87CEEB` |

#### 3.1.2 Quick Filter Bar
Row of filter controls above the data table.

**Filter Options:**
| Filter | Type | Options |
|--------|------|---------|
| Unengineered | Toggle button | Show only unengineered jobs |
| In-Work | Toggle button | Show only jobs with labor |
| Can Ship | Toggle button | Show jobs with sufficient inventory |
| ESI | Dropdown | All / ESI Only / Non-ESI Only |
| Customer | Dropdown/Search | Filter by customer name |
| Date Range | Date picker | Filter by due date range |
| Clear All | Button | Reset all filters |

**Behavior:**
- Filters are additive (AND logic)
- Active filters shown as highlighted buttons
- Filter state persists during session
- Count of filtered results shown

#### 3.1.3 Notes/Comments System
Modal dialog for adding/viewing notes per job.

**Trigger:** Click anywhere on a row (except action icons)

**Modal Contents:**
- Job header (Job #, Part #, Description)
- Scrollable list of existing notes (newest first)
- Each note shows: Date, Author, Text
- Text input for new note
- Save / Cancel buttons

**Data Storage:**
- SQLite database (local)
- Table: `notes`
  - `id` (INTEGER PRIMARY KEY)
  - `job_number` (TEXT)
  - `note_text` (TEXT)
  - `created_at` (DATETIME)
  - `created_by` (TEXT)

#### 3.1.4 Action Icons
Small icons in each row for quick actions.

| Icon | Action | Behavior |
|------|--------|----------|
| 📄 | Open Drawing | Opens drawing URL in new tab |
| 📋 | Open PO | Opens PO in Epicor (or PO document) |

**Drawing URL Pattern:**
```
\\server\drawings\{PartNumber}.pdf
OR
https://drawings.weco.com/{PartNumber}
```
*(To be configured in settings)*

#### 3.1.5 Theme Toggle
Light/Dark mode switch in header.

**Default:** Light mode
**Persistence:** Saved to browser localStorage

---

### 3.2 Secondary Features (Phase 2)

#### 3.2.1 Jobs View
Operations and labor tracking by work center.

**Purpose:** See what step each job is on, hours worked

**Data Source:** `Weco-West-MB_Shop_Orders.csv` (includes operation details)

#### 3.2.2 Shipped View
Shipment tracking and pull-in analysis.

**Purpose:** Track what's shipped, analyze early shipments

**Data Source:** `WecoWest-CustomerShipments.csv`

#### 3.2.3 Shortages View
Material shortage monitoring.

**Purpose:** Purchasing team tracks material needs

**Data Source:** `wecoWest-materialshortage.csv`, `Weco-West-MaterialNotIssued.xml`

---

### 3.3 Future Features (Phase 3)

- Labor Hours dashboard (Richard)
- KPI Dashboard (Pete) - On-time delivery, Sales $/Labor Hour
- Bookings view
- Multi-facility support (Ontario)

---

## 4. Technical Specifications

### 4.1 Technology Stack
| Component | Technology |
|-----------|------------|
| Frontend | Streamlit (Python) |
| Backend | Python 3.9+ |
| Database | SQLite (notes/comments) |
| Data Source | CSV/XML files from Epicor BAQ exports |
| Hosting | Local server or internal VM |

### 4.2 Data Files

**Primary Data:**
| File | Purpose | Refresh |
|------|---------|---------|
| `Weco-West-MB_Shop_Orders.csv` | Orders, jobs, operations | Daily |
| `Weco-West-ESC-OrderBacklog.csv` | Order backlog | Daily |
| `WecoWest-CustomerShipments.csv` | Shipment history | Daily |
| `PK-LaborHistory.csv` | Labor tracking | Daily |

**Supporting Data:**
| File | Purpose |
|------|---------|
| `Customer Names.xlsx` | Customer name lookup |
| `MB Comments.xlsx` | Legacy comments (import once) |
| `Purch Comments.xlsx` | Legacy purchasing comments |

### 4.3 Data Schema

**Shop Orders CSV Columns:**
```
Order, Line, Release, Job, Seq, Part, Description, Engineered,
Released, Run Qty, Qty Completed, Opr, Operation Description,
Req. By, Due Date, Est. Prod Hours, Est. Setup Hours, Need By,
Ship By, Selling Requested Qty, Name, Labor Type, Labor Hrs, CommentText
```

**Customer Shipments CSV Columns:**
```
Ship Date, Name, Ship To, Packing Slip, Line, Part, Rev, Description,
QtyShip, Our Requested Qty, Ship By, Need By, OnTime, Description,
Complete, PO Line, Warehouse, Bin, Qty from Inv, Job, Job Ship Qty,
Order, Line, Rel, PO, Ready to invoice, Invoiced, Cust. ID,
Tracking Number, Cust Part, Rev, Entry Person, InvoiceSum,
Order Date, Value Shipped, Ext Price Rel
```

### 4.4 Performance Requirements
| Metric | Target |
|--------|--------|
| Initial load | < 3 seconds |
| Filter response | < 500ms |
| Auto-refresh | Every 5 minutes |
| Data volume | ~500-1000 orders |

---

## 5. User Interface Specifications

### 5.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER                                                          │
│  Logo/Title                              Refresh | Theme Toggle │
├─────────────────────────────────────────────────────────────────┤
│ FILTER BAR                                                      │
│  [Unengineered] [In-Work] [Can Ship] [ESI ▼] [Customer ▼] [Clear]│
├─────────────────────────────────────────────────────────────────┤
│ DATA TABLE                                                      │
│  Column headers (sortable)                                      │
│  ───────────────────────────────────────────────────────────────│
│  Data rows with color coding                                    │
│  ...                                                            │
│  [Infinite scroll loads more]                                   │
├─────────────────────────────────────────────────────────────────┤
│ FOOTER                                                          │
│  "Showing X of Y jobs | Last updated: HH:MM AM/PM"              │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Responsive Behavior
- **Desktop (1200px+):** Full layout as shown
- **Tablet (768-1199px):** Collapse some columns, horizontal scroll
- **Mobile:** Not required for MVP (shop floor use is desktop)

### 5.3 Accessibility
- Keyboard navigation for filters
- High contrast mode (via dark theme)
- Screen reader compatible table structure

---

## 6. User Workflows

### 6.1 Kyle's Morning Workflow

```
1. Open application (bookmarked)
2. Data loads automatically (< 3 sec)
3. ENGINEERING CHECK:
   - Click [Unengineered] filter
   - Review list of jobs needing engineering
   - Click rows to add notes if needed
   - Click 📄 to check drawings
4. Clear filter, click [In-Work] filter
5. IN-WORK CHECK:
   - Review jobs currently being worked
   - Check "Last Labor" column for activity
   - Flag any jobs idle > 2 days
6. Clear filter, click [Can Ship] filter
7. INVENTORY CHECK:
   - Review jobs ready to ship
   - Verify quantities
   - Add notes for shipping team
8. Clear all filters
9. Quick scan of full list
10. Close or leave open for reference
```

**Total time target: ≤ 30 minutes**

---

## 7. Data Flow

```
┌─────────────────┐
│   Epicor ERP    │
│   (On-Prem)     │
└────────┬────────┘
         │ Scheduled BAQ exports (daily)
         ▼
┌─────────────────┐
│   CSV/XML       │
│   Files         │
│ (Network share) │
└────────┬────────┘
         │ Read on load + every 5 min
         ▼
┌─────────────────┐     ┌─────────────────┐
│   Streamlit     │────▶│    SQLite       │
│   Application   │◀────│   (Notes DB)    │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│   Web Browser   │
│   (Kyle, etc.)  │
└─────────────────┘
```

---

## 8. Configuration

### 8.1 Configurable Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `DATA_PATH` | `./data/` | Location of CSV files |
| `REFRESH_INTERVAL` | `300` | Auto-refresh seconds |
| `DRAWING_URL_PATTERN` | `{server}/{part}.pdf` | Drawing link pattern |
| `PO_URL_PATTERN` | `{epicor}/po/{po}` | PO link pattern |
| `DEFAULT_THEME` | `light` | Default color theme |

### 8.2 Environment Variables
```
DISPATCH_DATA_PATH=/path/to/data/files
DISPATCH_DB_PATH=/path/to/database.db
```

---

## 9. Acceptance Criteria

### 9.1 MVP Acceptance
- [ ] Orders dashboard displays all jobs from CSV
- [ ] Color coding matches specification
- [ ] All 6 filters work correctly
- [ ] Filters can be combined (AND logic)
- [ ] Notes can be added and persist across sessions
- [ ] Drawing/PO icons open correct links
- [ ] Auto-refresh works every 5 minutes
- [ ] Light/Dark theme toggle works
- [ ] Initial load < 3 seconds
- [ ] Kyle can complete workflow in ≤ 30 minutes

### 9.2 User Acceptance Testing
- [ ] Kyle reviews and approves
- [ ] Amy reviews shortages view (Phase 2)
- [ ] Richard reviews labor view (Phase 2)
- [ ] Pete reviews and trusts the data source

---

## 10. Appendix

### 10.1 Reference Documents
- `WWDispatch_List_Analysis.md` - Original Excel workbook analysis
- `WWDispatch_Data_Sources.md` - Data source file paths
- `Weco hen spreadsheet meeting 1.txt` - Stakeholder interview transcript

### 10.2 Glossary
| Term | Definition |
|------|------------|
| ESI | A separate business unit operating within Henrietta |
| BAQ | Business Activity Query (Epicor report/export) |
| Unengineered | Job not yet reviewed/released by engineering |
| In-Work | Job has labor transactions recorded |
| Pull-in | Shipping an order before its due date |

---

## 11. Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | | | |
| Primary User | Kyle | | |
| Developer | | | |
| IT/Operations | | | |
