"""
Configuration settings for Henrietta Dispatch Application
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR.parent / "Data"  # Points to actual data folder
DATABASE_DIR = BASE_DIR / "database"

# Data file paths - Update these to match your environment
# For development, point to local copies
# For production, point to network shares
DATA_PATHS = {
    # Core data files
    "shop_orders": DATA_DIR / "Weco-West-MB_Shop_Orders.csv",
    "order_backlog": DATA_DIR / "Weco-West-ESC-OrderBacklog.csv",
    "order_backlog_v2": DATA_DIR / "Weco-West-ESC-OrderBacklogv2.csv",
    "customer_shipments": DATA_DIR / "WecoWest-CustomerShipments.csv",
    "open_po": DATA_DIR / "Weco-West-MB_Open_PO.csv",
    "labor_history": DATA_DIR / "PK-LaborHistory.csv",
    "bookings": DATA_DIR / "Weco-West_BookSalesOrderSumDtl.csv",
    "part_cost": DATA_DIR / "WECO-West-PartCost.csv",
    "stock_jobs": DATA_DIR / "Weco-West-MM-StockJobs-Dev.csv",
    "material_shortage": DATA_DIR / "wecoWest-materialshortage.csv",
    "material_not_issued": DATA_DIR / "Weco-West-MaterialNotIssued.xml",

    # Supporting files
    "customer_date": DATA_DIR / "Weco-CustomerDate.csv",
    "customer_names": DATA_DIR / "Customer Names.xlsx",

    # Comments files
    "comments_operations": DATA_DIR / "MB Comments.xlsx",
    "comments_purchasing": DATA_DIR / "Purch Comments.xlsx",
}

# Database settings
DATABASE_PATH = DATABASE_DIR / "dispatch.db"

# Application settings
APP_TITLE = "Henrietta Dispatch"
PAGE_ICON = "🏭"

# Color coding settings (matching original Excel)
COLORS = {
    "unengineered": "#ADD8E6",      # Light blue - unengineered jobs
    "in_work": "#90EE90",           # Green - jobs in work
    "can_ship": "#90EE90",          # Green - inventory sufficient
    "cannot_ship": "#FFB6C1",       # Light red - inventory insufficient
    "esi_job": "#87CEEB",           # Sky blue - ESI jobs
    "late": "#FF6B6B",              # Red - past due
    "warning": "#FFD93D",           # Yellow - approaching due date
}

# User roles
ROLES = {
    "production_planner": ["Kyle"],
    "purchasing": ["Amy"],
    "production_supervisor": ["Richard"],
    "shipping": ["Dan", "Zach"],
    "operator": ["Tom Roshuck"],
}

# Date formats
DATE_FORMAT = "%m/%d/%Y"
DATETIME_FORMAT = "%m/%d/%Y %H:%M"

# Refresh settings (in seconds)
REFRESH_INTERVAL = 300  # 5 minutes

# URL patterns for external links
DRAWING_URL_PATTERN = "\\\\server\\drawings\\{part}.pdf"
PO_URL_PATTERN = "{epicor}/po/{po}"

# Default theme
DEFAULT_THEME = "light"

# Status display names
STATUS_NAMES = {
    "unengineered": "Unengineered",
    "in_work": "In-Work",
    "can_ship": "Can Ship",
    "partial": "Partial",
    "not_started": "Not Started",
}
