# Henrietta Dispatch Application

A BI-style web application to replace the legacy WWDispatch List Excel workbook for production planning and manufacturing management at the Henrietta facility.

## Overview

This application provides Kyle (Production Planner) and other team members with a streamlined daily workflow for:
- Engineering status tracking (unengineered jobs)
- Work-in-progress monitoring
- Inventory availability checking
- Material on-hand tracking
- Notes and comments management

## MVP Features (v1.0)

### ✅ Implemented
- **Orders Dashboard** - Main production planning view with color-coded status indicators
  - Excel-like grid layout showing all jobs
  - Color-coded status badges (Unengineered, In-Work, Not Started)
  - Sortable columns with job details
- **Quick Filter Bar** - Toggle filters for rapid data exploration
  - Unengineered jobs filter
  - In-Work jobs filter
  - ESI/Non-ESI filter dropdown
  - Customer filter dropdown
  - Clear all filters button
- **Notes/Comments System** - Persistent notes per job stored in SQLite
  - Add notes to any job via sidebar
  - View note history with timestamps and authors
  - Notes survive data refreshes
- **Action Icons** - Quick access to related documents
  - 📄 Drawing link placeholder (configured in settings)
  - 📋 Notes indicator
- **Theme Toggle** - Light/Dark mode support
- **Auto-Refresh** - Manual refresh button (auto-refresh capability built-in)
- **Statistics Panel** - Real-time job counts and metrics

### 🚧 Future Enhancements (Phase 2)
- Jobs View - Operations and labor tracking by work center
- Shipped View - Shipment tracking and pull-in analysis
- Shortages View - Material shortage monitoring
- Inventory-based status indicators (requires inventory data integration)
- Automatic background refresh every 5 minutes
- Clickable rows for inline note editing

## Installation & Deployment

### Prerequisites
- Python 3.9 or higher
- Access to Epicor data exports (CSV/XML files)
- Access to the Data folder with CSV files:
  - `Weco-West-MB_Shop_Orders.csv` (required)
  - `PK-LaborHistory.csv` (optional but recommended)
  - `Weco-West-ESC-OrderBacklog.csv` (optional for ESI filtering)

### Quick Start

1. **Navigate to the project directory:**
```bash
cd henrietta-dispatch
```

2. **Create a virtual environment (recommended):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Verify data paths:**
The application expects data files in `../Data/` (parent directory).
Current configuration in `config/settings.py` points to:
- `DATA_DIR = BASE_DIR.parent / "Data"`

If your data files are elsewhere, update `config/settings.py`:
```python
DATA_DIR = Path("/path/to/your/data/folder")
```

5. **Run the application:**
```bash
streamlit run app/main.py
```

The application will open in your default web browser at `http://localhost:8501`

### First Run

On first run, the application will:
1. Initialize the SQLite database for notes (in `database/` folder)
2. Load all data from CSV files
3. Calculate job statuses and enrichments
4. Display the Orders Dashboard

**Expected behavior:**
- Loading ~165 jobs from Shop Orders CSV
- Identifying labor history for jobs with recent activity
- Calculating status for each job based on engineering and completion data

### Troubleshooting

**Issue: "No data available"**
- Check that `config/settings.py` has correct `DATA_DIR` path
- Verify CSV files exist in the Data folder
- Check file permissions

**Issue: "Database I/O error"**
- Ensure `database/` folder has write permissions
- For network drives, you may need to use a local database path

**Issue: Module not found**
- Ensure you've activated the virtual environment
- Reinstall requirements: `pip install -r requirements.txt`

## Data Sources

The application reads from Epicor BAQ exports:
- `Weco-West-MB_Shop_Orders.csv` - Main orders data
- `Weco-West-ESC-OrderBacklog.csv` - Order backlog
- `WecoWest-CustomerShipments.csv` - Shipment history
- `Weco-West-MB_Open_PO.csv` - Open purchase orders
- `PK-LaborHistory.csv` - Labor tracking
- And others...

## Project Structure

```
henrietta-dispatch/
├── app/
│   ├── main.py              # Main Streamlit application
│   ├── pages/               # View pages (Orders, Jobs, etc.)
│   ├── components/          # Reusable UI components
│   └── utils/               # Data loading and helpers
├── config/                  # Configuration files
├── database/                # SQLite for notes/comments
├── docs/                    # Documentation
└── data/                    # Data files (not in git)
```

## Development

This project was created to replace the legacy WWDispatch List Excel workbook created by Mike B. The goal is to provide a supported, maintainable solution that preserves the key workflows identified in stakeholder interviews.

## License

Proprietary - Weco Industries
