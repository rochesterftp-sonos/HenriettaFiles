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
    "order_jobs": DATA_DIR / "Weco-West-MB_Order_Jobs.csv",
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
    "no_job": "#FFA500",            # Orange - order lines without jobs
    "unengineered": "#ADD8E6",      # Light blue - unengineered jobs
    "in_work": "#90EE90",           # Green - jobs in work
    "not_started": "#FFFFFF",       # White - not started
    "can_ship": "#90EE90",          # Green - inventory sufficient
    "cannot_ship": "#FFB6C1",       # Light red - inventory insufficient
    "esi_job": "#87CEEB",           # Sky blue - ESI jobs
    "late": "#FF6B6B",              # Red - past due
    "warning": "#FFD93D",           # Yellow - approaching due date

    # Purchasing colors
    "po_overdue": "#FF6B6B",        # Red - overdue POs
    "po_warning": "#FFD93D",        # Yellow - due within 7 days
    "po_ontime": "#90EE90",         # Green - on time

    # Scheduling colors
    "gantt_today": "#FF0000",       # Red - today line
    "gantt_completed": "#4CAF50",   # Dark green - completed
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
    "no_job": "No Job",
    "unengineered": "Unengineered",
    "in_work": "In-Work",
    "can_ship": "Can Ship",
    "partial": "Partial",
    "not_started": "Not Started",
}
