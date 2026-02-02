# Henrietta Dispatch Application

A BI-style web application to replace the legacy WWDispatch List Excel workbook for production planning and manufacturing management at the Henrietta facility.

## Overview

This application provides Kyle (Production Planner) and other team members with a streamlined daily workflow for:
- Engineering status tracking (unengineered jobs)
- Work-in-progress monitoring
- Inventory availability checking
- Material on-hand tracking
- Notes and comments management

## Features

### Core Views
- **Orders Dashboard** - Main production planning view with color-coded status indicators
- **Jobs View** - Operations and labor tracking by work center
- **Shipped View** - Shipment tracking and pull-in analysis
- **Shortages View** - Material shortage monitoring (Purchasing)

### Key Capabilities
- Color-coded status indicators (Engineering, In-Work, Inventory)
- Filtering by ESI vs. Standard manufacturing
- Hyperlinks to drawings and purchase orders
- Persistent notes/comments per job
- Role-based views for different users

## Installation

### Prerequisites
- Python 3.9 or higher
- Access to Epicor data exports (CSV/XML files)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/henrietta-dispatch.git
cd henrietta-dispatch
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure data paths in `config/settings.py`

5. Run the application:
```bash
streamlit run app/main.py
```

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
