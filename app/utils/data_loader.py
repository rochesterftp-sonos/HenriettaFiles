"""
Data loading utilities for Henrietta Dispatch Application
Handles reading CSV/Excel files and processing them for the application

This module replicates the logic from the WWDispatch spreadsheet VBA macros.
The primary data source is the Order_Jobs CSV which contains all order lines.
Shop Orders CSV provides additional job details (Engineered, Released, Qty Completed).
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import json
import os
import shutil
import time

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import DATA_PATHS, DATE_FORMAT, DATA_DIR, BASE_DIR

# User settings file
USER_SETTINGS_FILE = BASE_DIR / "config" / "user_settings.json"

# Local cache settings
CACHE_DIR = BASE_DIR / "data" / "cache"
CACHE_METADATA_FILE = CACHE_DIR / "cache_metadata.json"
CACHE_CHECK_INTERVAL = 300  # 5 minutes in seconds

# Files to cache (key must match DATA_PATHS keys)
CACHED_FILES = [
    "order_jobs",
    "shop_orders",
    "labor_history",
    "part_cost",
    "material_shortage",
    "material_not_issued",
    "customer_names",
    "comments_operations",
    "open_po",
    "order_backlog",
]


def ensure_cache_dir():
    """Create cache directory if it doesn't exist"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_cache_metadata():
    """Load cache metadata (timestamps, last check time)"""
    if CACHE_METADATA_FILE.exists():
        try:
            with open(CACHE_METADATA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_check": 0, "files": {}}


def save_cache_metadata(metadata):
    """Save cache metadata"""
    ensure_cache_dir()
    try:
        with open(CACHE_METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"Error saving cache metadata: {e}")


def get_file_timestamp(filepath):
    """Get file modification timestamp, returns 0 if file doesn't exist"""
    try:
        if filepath and os.path.exists(filepath):
            return os.path.getmtime(filepath)
    except Exception:
        pass
    return 0


def get_cached_path(key):
    """Get the local cache path for a file key"""
    user_settings = load_user_settings()

    # Get the original source path
    source_path = None
    if key in user_settings and user_settings[key]:
        source_path = user_settings[key]
    elif key in DATA_PATHS:
        source_path = str(DATA_PATHS[key])

    if not source_path:
        return None

    # Determine cache filename (preserve original extension)
    filename = os.path.basename(source_path)
    return CACHE_DIR / filename


def should_check_for_updates():
    """Check if enough time has passed to check for updates"""
    metadata = load_cache_metadata()
    last_check = metadata.get("last_check", 0)
    return (time.time() - last_check) >= CACHE_CHECK_INTERVAL


def update_cache_if_needed(force=False):
    """
    Check for file updates and copy new files to cache.
    Only checks every CACHE_CHECK_INTERVAL seconds unless force=True.

    Returns dict of {key: {"updated": bool, "source_time": timestamp, "cached": bool}}
    """
    ensure_cache_dir()
    metadata = load_cache_metadata()

    # Check if we should skip (not enough time passed)
    if not force and not should_check_for_updates():
        print(f"Skipping cache check (last check was {int(time.time() - metadata.get('last_check', 0))}s ago)")
        return metadata.get("files", {})

    print("Checking for data file updates...")
    metadata["last_check"] = time.time()

    user_settings = load_user_settings()
    results = {}

    for key in CACHED_FILES:
        # Get source path
        source_path = None
        if key in user_settings and user_settings[key]:
            source_path = user_settings[key]
        elif key in DATA_PATHS:
            source_path = str(DATA_PATHS[key])

        if not source_path:
            results[key] = {"updated": False, "source_time": 0, "cached": False, "error": "No path configured"}
            continue

        # Get timestamps
        source_time = get_file_timestamp(source_path)
        cached_path = get_cached_path(key)
        cached_time = get_file_timestamp(cached_path) if cached_path else 0

        # Get previous known source time
        prev_source_time = metadata.get("files", {}).get(key, {}).get("source_time", 0)

        result = {
            "source_path": source_path,
            "source_time": source_time,
            "source_time_str": datetime.fromtimestamp(source_time).strftime("%m/%d/%Y %I:%M %p") if source_time > 0 else "Not found",
            "cached": False,
            "updated": False,
            "error": None
        }

        if source_time == 0:
            result["error"] = "Source file not found"
            results[key] = result
            continue

        # Check if we need to update cache
        needs_update = (source_time > cached_time) or (source_time != prev_source_time)

        if needs_update:
            try:
                print(f"  Updating cache for {key}...")
                shutil.copy2(source_path, cached_path)
                result["updated"] = True
                result["cached"] = True
                print(f"  Copied {os.path.basename(source_path)} to cache")
            except Exception as e:
                result["error"] = str(e)
                print(f"  Error caching {key}: {e}")
        else:
            result["cached"] = os.path.exists(cached_path) if cached_path else False

        results[key] = result

    # Save updated metadata
    metadata["files"] = results
    save_cache_metadata(metadata)

    return results


def get_data_path_with_cache(key, default=None):
    """
    Get the path for a data file, using cache if available.
    Returns cached path if file is cached, otherwise returns source path.
    """
    cached_path = get_cached_path(key)

    # If cached file exists and is newer, use it
    if cached_path and os.path.exists(cached_path):
        return str(cached_path)

    # Fall back to original get_data_path logic
    return get_data_path(key, default)


def get_cache_status():
    """
    Get current cache status for all files.
    Returns dict with file info for Settings page display.
    """
    metadata = load_cache_metadata()
    files_info = metadata.get("files", {})

    # Add current status
    result = {}
    for key in CACHED_FILES:
        cached_path = get_cached_path(key)
        info = files_info.get(key, {})

        result[key] = {
            "source_path": info.get("source_path", "Not configured"),
            "source_time": info.get("source_time_str", "Unknown"),
            "cached": os.path.exists(cached_path) if cached_path else False,
            "cache_path": str(cached_path) if cached_path else None,
            "last_updated": info.get("updated", False),
            "error": info.get("error")
        }

    result["_last_check"] = metadata.get("last_check", 0)
    result["_last_check_str"] = datetime.fromtimestamp(metadata.get("last_check", 0)).strftime("%m/%d/%Y %I:%M:%S %p") if metadata.get("last_check", 0) > 0 else "Never"

    return result


def load_user_settings():
    """Load user-configured settings from JSON file"""
    if USER_SETTINGS_FILE.exists():
        try:
            with open(USER_SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_data_path(key, default=None, use_cache=True):
    """
    Get the path for a data file, checking cache first, then user settings.
    Falls back to DATA_PATHS from settings.py if not configured.

    Args:
        key: The data file key (e.g., "shop_orders")
        default: Default path if not found
        use_cache: If True, return cached path if available
    """
    # Check cache first
    if use_cache and key in CACHED_FILES:
        cached_path = get_cached_path(key)
        if cached_path and os.path.exists(cached_path):
            return str(cached_path)

    # Check user settings
    user_settings = load_user_settings()
    if key in user_settings and user_settings[key]:
        path = user_settings[key]
        if os.path.exists(path):
            return path

    # Fall back to default DATA_PATHS
    if key in DATA_PATHS:
        return DATA_PATHS[key]

    # Use provided default
    return default


def get_source_path(key):
    """
    Get the original source path for a data file (not cached).
    Used for checking file timestamps.
    """
    return get_data_path(key, use_cache=False)


def load_part_inventory():
    """
    Load part inventory (Qty On Hand) from the Part Cost CSV.
    Returns a dictionary mapping Part number to Qty On Hand.
    Used to determine if orders can ship from existing stock.
    Takes the maximum Qty On Hand when a part has multiple rows.
    """
    try:
        df = pd.read_csv(get_data_path("part_cost"), on_bad_lines='skip')
        if 'Part' in df.columns and 'Qty On Hand' in df.columns:
            df['Qty On Hand'] = pd.to_numeric(df['Qty On Hand'], errors='coerce').fillna(0)
            # Take max Qty On Hand per part (some parts have multiple rows)
            return df.groupby('Part')['Qty On Hand'].max().to_dict()
        return {}
    except Exception as e:
        print(f"Error loading part inventory: {str(e)}")
        return {}


def load_mb_comments():
    """
    Load MB Comments from Excel file.
    Returns a dictionary mapping Order L-R to comments dict with:
    - 'purchasing': Purchasing Comments (Column S)
    - 'operations': Operation's Comments and Action Items (Column V)
    """
    comments = {}
    try:
        df = pd.read_excel(get_data_path("comments_operations"), header=1)

        if 'Order L-R' not in df.columns:
            print("Warning: 'Order L-R' column not found in MB Comments")
            return {}

        purch_col = 'Purchasing Comments'
        ops_col = "Operation's Comments and Action Items"

        for _, row in df.iterrows():
            order_lr = row.get('Order L-R')
            if pd.isna(order_lr):
                continue

            order_lr = str(order_lr).strip()
            purch_comment = row.get(purch_col, '')
            ops_comment = row.get(ops_col, '')

            # Only add if there's at least one comment
            if pd.notna(purch_comment) or pd.notna(ops_comment):
                comments[order_lr] = {
                    'purchasing': str(purch_comment) if pd.notna(purch_comment) else '',
                    'operations': str(ops_comment) if pd.notna(ops_comment) else ''
                }

        return comments
    except FileNotFoundError:
        print(f"Warning: MB Comments file not found at {DATA_PATHS.get('comments_operations')}")
        return {}
    except Exception as e:
        print(f"Error loading MB Comments: {str(e)}")
        return {}


def load_material_shortages():
    """
    Load jobs with material shortages from the Material Not Issued XML.
    Returns a set of job numbers that have material shortages.
    """
    try:
        import xml.etree.ElementTree as ET
        xml_path = get_data_path("material_not_issued")
        if not xml_path or not xml_path.exists():
            return set()

        tree = ET.parse(xml_path)
        root = tree.getroot()

        jobs_with_shortage = set()
        for result in root.findall('.//Results'):
            job_num = result.find('JobMtl_JobNum')
            required = result.find('JobMtl_RequiredQty')
            issued = result.find('JobMtl_IssuedQty')

            if job_num is not None:
                job = job_num.text
                req_qty = float(required.text) if required is not None and required.text else 0
                iss_qty = float(issued.text) if issued is not None and issued.text else 0

                # If required > issued, there's a shortage
                if req_qty > iss_qty:
                    jobs_with_shortage.add(job)

        return jobs_with_shortage

    except Exception as e:
        print(f"Error loading material shortages: {str(e)}")
        return set()


def get_material_shortage_details(job_number):
    """
    Get detailed material shortage information for a specific job.
    Returns a list of dictionaries with shortage details.
    """
    try:
        import xml.etree.ElementTree as ET
        xml_path = get_data_path("material_not_issued")
        if not xml_path or not xml_path.exists():
            return []

        tree = ET.parse(xml_path)
        root = tree.getroot()

        shortages = []
        for result in root.findall('.//Results'):
            job_num = result.find('JobMtl_JobNum')
            if job_num is not None and job_num.text == str(job_number):
                required = result.find('JobMtl_RequiredQty')
                issued = result.find('JobMtl_IssuedQty')
                part = result.find('JobMtl_PartNum')
                desc = result.find('Part_PartDescription')

                req_qty = float(required.text) if required is not None and required.text else 0
                iss_qty = float(issued.text) if issued is not None and issued.text else 0

                # Only include if there's actually a shortage
                if req_qty > iss_qty:
                    shortages.append({
                        'Part': part.text if part is not None else 'Unknown',
                        'Description': desc.text if desc is not None else '',
                        'Required': req_qty,
                        'Issued': iss_qty,
                        'Short': req_qty - iss_qty
                    })

        return shortages

    except Exception as e:
        print(f"Error getting shortage details for job {job_number}: {str(e)}")
        return []


def get_job_operations(job_number):
    """
    Get all operations for a specific job from Shop Orders.
    Returns a DataFrame with operation details.
    """
    try:
        df = pd.read_csv(get_data_path("shop_orders"))

        # Filter for the specific job
        job_ops = df[df['Job'] == job_number].copy()

        if job_ops.empty:
            return pd.DataFrame()

        # Select relevant operation columns
        op_cols = ['Opr', 'Operation Description', 'Qty Completed', 'Run Qty',
                   'Est. Prod Hours', 'Est. Setup Hours', 'Labor Type', 'Labor Hrs']
        op_cols = [c for c in op_cols if c in job_ops.columns]

        result = job_ops[op_cols].drop_duplicates()

        # Sort by operation number
        if 'Opr' in result.columns:
            result = result.sort_values('Opr')

        return result

    except Exception as e:
        print(f"Error loading operations for job {job_number}: {str(e)}")
        return pd.DataFrame()


def load_order_jobs():
    """
    Load order jobs data from CSV file - the primary source showing all order lines.
    This matches the WWDispatch spreadsheet's "Orders" sheet which shows all order lines
    including those without jobs assigned yet ("No Job").

    Returns a DataFrame with one row per order line (Order/Line/Rel combination).
    """
    try:
        order_jobs_path = get_data_path("order_jobs", DATA_DIR / "Weco-West-MB_Order_Jobs.csv")
        df = pd.read_csv(order_jobs_path)

        # Rename columns to match our standard format
        df = df.rename(columns={
            'Job Number': 'Job',
            'Part Description': 'Description',
            'Rel': 'Release',
        })

        # Create Order-Line-Release key (matches spreadsheet's "Order L-R" column)
        df['OrderLineRel'] = df['Order'].astype(str) + '-' + df['Line'].astype(str) + '-' + df['Release'].astype(str)

        # Convert date columns
        date_columns = ['Need By', 'Ship By', 'Order Date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Convert numeric columns
        numeric_columns = ['Selling Requested Qty', 'Unit Price', 'Total Rel Dollar']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Rename Selling Requested Qty to Order Qty for consistency with spreadsheet
        df = df.rename(columns={'Selling Requested Qty': 'Order Qty'})

        return df

    except FileNotFoundError:
        print(f"Error: Order jobs file not found at {DATA_DIR / 'Weco-West-MB_Order_Jobs.csv'}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading order jobs: {str(e)}")
        return pd.DataFrame()


def load_hen_eng_jobs():
    """
    Load HenEngJobs data which contains additional job information
    not always present in Shop_Orders.
    """
    try:
        hen_path = DATA_DIR / "HenEngJobs-Copy.csv"
        df = pd.read_csv(hen_path, on_bad_lines='skip')

        # Convert boolean columns
        bool_columns = ['Engineered', 'Released', 'Closed']
        for col in bool_columns:
            if col in df.columns:
                df[col] = df[col].map({'True': True, 'False': False, True: True, False: False})

        return df

    except FileNotFoundError:
        print(f"Warning: HenEngJobs file not found at {DATA_DIR / 'HenEngJobs-Copy.csv'}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading HenEngJobs: {str(e)}")
        return pd.DataFrame()


def get_stock_jobs_by_part(shop_orders_df, hen_eng_jobs_df=None):
    """
    Get a mapping of Part number to stock job numbers.
    Stock jobs are jobs with Order=0 (not linked to a specific order line).
    The spreadsheet VBA uses these to find jobs for order lines by Part number.

    Uses both Shop_Orders and HenEngJobs as sources.
    """
    part_to_job = {}

    # From Shop_Orders: Stock jobs have Order = 0
    if not shop_orders_df.empty:
        stock_jobs = shop_orders_df[shop_orders_df['Order'] == 0].copy()
        shop_mapping = stock_jobs.groupby('Part')['Job'].first().to_dict()
        part_to_job.update(shop_mapping)

    # From HenEngJobs: All jobs are potential matches
    # HenEngJobs contains jobs not yet in Shop_Orders
    if hen_eng_jobs_df is not None and not hen_eng_jobs_df.empty:
        hen_mapping = hen_eng_jobs_df.groupby('Part')['Job'].first().to_dict()
        # Only add if not already in part_to_job (Shop_Orders takes precedence)
        for part, job in hen_mapping.items():
            if part not in part_to_job:
                part_to_job[part] = str(job)

    return part_to_job


def get_jobs_by_order(shop_orders_df):
    """
    Get a mapping of Order number to job numbers.
    Some orders have jobs created with numeric job numbers (like 52707)
    that are linked by Order number rather than being stock jobs.
    """
    order_to_job = {}

    if shop_orders_df.empty:
        return order_to_job

    # Get jobs where Order > 0 and job is a numeric (stock-style) job
    order_jobs = shop_orders_df[shop_orders_df['Order'] > 0].copy()

    # Group by Order and get the first numeric job (5-digit jobs like 52707)
    for order_num in order_jobs['Order'].unique():
        order_subset = order_jobs[order_jobs['Order'] == order_num]
        # Look for numeric jobs (stock-style)
        numeric_jobs = order_subset[order_subset['Job'].str.match(r'^\d{5}$', na=False)]
        if not numeric_jobs.empty:
            order_to_job[int(order_num)] = numeric_jobs['Job'].iloc[0]

    return order_to_job


def load_shop_orders():
    """
    Load shop orders data from CSV file.
    This provides job-level details like Engineered, Released, and Qty Completed.
    Returns a processed DataFrame with one row per job (not per operation).
    """
    try:
        # Read the CSV file
        df = pd.read_csv(get_data_path("shop_orders"))

        # Convert boolean strings to actual booleans
        bool_columns = ['Engineered', 'Released']
        for col in bool_columns:
            if col in df.columns:
                df[col] = df[col].map({'True': True, 'False': False, True: True, False: False})

        # Convert date columns
        date_columns = ['Req. By', 'Due Date', 'Need By', 'Ship By']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Convert numeric columns
        numeric_columns = ['Run Qty', 'Qty Completed', 'Est. Prod Hours',
                          'Est. Setup Hours', 'Selling Requested Qty', 'Labor Hrs']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Group by Job to get one row per job (not per operation)
        # Take the first row for most fields, sum for quantities
        agg_dict = {
            'Order': 'first',
            'Line': 'first',
            'Release': 'first',
            'Part': 'first',
            'Description': 'first',
            'Engineered': 'first',
            'Released': 'first',
            'Run Qty': 'sum',
            'Qty Completed': 'max',  # Max qty completed across operations
            'Selling Requested Qty': 'first',
            'Due Date': 'first',
            'Need By': 'first',
            'Ship By': 'first',
            'Name': 'first',  # Customer name
            'CommentText': 'first',
        }

        # Add Labor Type if it exists - used to determine "In Work" status
        # Labor Type = 'P' means production labor has been recorded
        if 'Labor Type' in df.columns:
            agg_dict['Labor Type'] = 'first'

        job_df = df.groupby('Job', as_index=False).agg(agg_dict)

        return job_df

    except FileNotFoundError:
        print(f"Error: Shop orders file not found at {DATA_PATHS['shop_orders']}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading shop orders: {str(e)}")
        return pd.DataFrame()


def load_labor_history():
    """
    Load labor history to determine last labor date per job
    Returns a DataFrame with Job and LastLaborDate
    """
    try:
        # Labor history file has no header, so we need to specify column names
        # Based on the data structure observed
        df = pd.read_csv(
            get_data_path("labor_history"),
            header=None,
            names=['Employee', 'Date', 'Type', 'Code', 'Hours', 'Job', 'Comment']
        )

        # Convert date column
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        # Get the most recent labor date per job
        labor_df = df.groupby('Job', as_index=False).agg({
            'Date': 'max',
            'Hours': 'sum'
        })
        labor_df.rename(columns={'Date': 'LastLaborDate', 'Hours': 'TotalLaborHours'}, inplace=True)

        return labor_df

    except FileNotFoundError:
        print(f"Warning: Labor history file not found at {DATA_PATHS['labor_history']}")
        return pd.DataFrame(columns=['Job', 'LastLaborDate', 'TotalLaborHours'])
    except Exception as e:
        print(f"Error loading labor history: {str(e)}")
        return pd.DataFrame(columns=['Job', 'LastLaborDate', 'TotalLaborHours'])


def load_esi_customers():
    """
    Load ESI (medical) customer names from Customer Names Excel file.
    ESI customers are identified by Business = "MED" in the History MED sheet.

    Returns a set of customer names that are ESI (medical) customers.
    """
    esi_customers = set()

    try:
        # Read the History MED sheet which has customer type info
        df = pd.read_excel(get_data_path("customer_names"), sheet_name="History MED", header=1)

        # The "Business" column contains MED/MFG/Not FTT/etc.
        if 'Business' in df.columns and 'Customer' in df.columns:
            med_customers = df[df['Business'] == 'MED']['Customer'].dropna()
            esi_customers = set(med_customers.astype(str).str.strip())

    except FileNotFoundError:
        print(f"Warning: Customer names file not found at {DATA_PATHS['customer_names']}")
    except Exception as e:
        print(f"Error loading ESI customers: {str(e)}")

    return esi_customers


def calculate_status(row):
    """
    Calculate the status of a job based on business rules.
    Matches the logic from the WWDispatch spreadsheet.

    Status Logic:
    - If Job is "No Job": "no_job" (order line without job assigned)
    - If not Engineered: "unengineered"
    - If Labor Type = 'P' OR Qty Completed > 0: "in_work"
    - Otherwise: "not_started"

    Note: Inventory-based statuses (Can Ship, Partial) will be added
    when inventory data becomes available
    """
    # Check for "No Job" first
    if row.get('Job') == 'No Job':
        return 'no_job'

    # Check Engineered status
    eng = row.get('Engineered')
    if pd.isna(eng) or eng == False or eng == 'No Job':
        return 'unengineered'

    # Check if in work - Labor Type = 'P' means production labor recorded
    labor_type = row.get('Labor Type', '')
    qty_completed = row.get('Qty Completed', 0)

    if labor_type == 'P':
        return 'in_work'
    if pd.notna(qty_completed) and qty_completed > 0:
        return 'in_work'

    return 'not_started'


def is_past_due(due_date):
    """Check if a due date is in the past"""
    if pd.isna(due_date):
        return False
    return due_date < pd.Timestamp.now()


def enrich_orders_data(orders_df, shop_orders_df, hen_eng_jobs_df, labor_df, esi_jobs, material_shortages=None, part_inventory=None, mb_comments=None):
    """
    Enrich orders data with calculated fields and joined data.
    Matches the WWDispatch spreadsheet logic.

    Args:
        orders_df: DataFrame of order lines from Order_Jobs CSV (primary source)
        shop_orders_df: DataFrame of job details from Shop_Orders CSV
        hen_eng_jobs_df: DataFrame from HenEngJobs (additional job source)
        labor_df: DataFrame of labor history
        esi_jobs: Set of ESI job numbers
        mb_comments: Dict mapping Order L-R to comments
        material_shortages: Set of job numbers with material shortages
        part_inventory: Dict mapping Part number to Qty On Hand

    Returns:
        Enriched DataFrame matching the WWDispatch spreadsheet structure
    """
    df = orders_df.copy()

    # Build set of valid jobs (jobs that actually exist in job system)
    valid_jobs = set()
    if not shop_orders_df.empty:
        valid_jobs.update(shop_orders_df['Job'].astype(str).unique())
    if hen_eng_jobs_df is not None and not hen_eng_jobs_df.empty:
        valid_jobs.update(hen_eng_jobs_df['Job'].astype(str).unique())

    # Get stock jobs by part number (for order lines without jobs)
    # Uses both Shop_Orders and HenEngJobs as sources
    part_to_job = get_stock_jobs_by_part(shop_orders_df, hen_eng_jobs_df)

    # Get jobs by order number (for orders with numeric jobs like 52707)
    order_to_job = get_jobs_by_order(shop_orders_df)

    # Process each order line
    # 1. If Job from Order_Jobs exists in valid_jobs, use it
    # 2. Else try to find a job by Order number
    # 3. Else try to find a stock job by Part number
    # 4. Else mark as "No Job"
    for idx in df.index:
        job = df.loc[idx, 'Job']
        job_str = str(job) if pd.notna(job) and job != '' else None

        if job_str and job_str in valid_jobs:
            # Job exists in system, keep it
            df.loc[idx, 'Job'] = job_str
        else:
            # Job doesn't exist in system, try Order lookup first
            order_num = int(df.loc[idx, 'Order'])
            if order_num in order_to_job:
                df.loc[idx, 'Job'] = order_to_job[order_num]
            else:
                # Try Part lookup
                part = df.loc[idx, 'Part']
                if part in part_to_job:
                    df.loc[idx, 'Job'] = part_to_job[part]
                else:
                    df.loc[idx, 'Job'] = 'No Job'

    # Build combined job details from Shop_Orders and HenEngJobs
    job_details = pd.DataFrame()

    if not shop_orders_df.empty:
        shop_cols = ['Job', 'Engineered', 'Released', 'Qty Completed', 'Run Qty', 'CommentText', 'Labor Type']
        shop_cols = [c for c in shop_cols if c in shop_orders_df.columns]
        job_details = shop_orders_df[shop_cols].copy()

    # Add jobs from HenEngJobs that aren't in Shop_Orders
    if hen_eng_jobs_df is not None and not hen_eng_jobs_df.empty:
        hen_cols = ['Job', 'Engineered', 'Released']
        hen_subset = hen_eng_jobs_df[hen_cols].copy()
        hen_subset['Job'] = hen_subset['Job'].astype(str)
        hen_subset['Qty Completed'] = 0
        hen_subset['Run Qty'] = 0
        hen_subset['CommentText'] = None

        if not job_details.empty:
            # Only add jobs not already in job_details
            existing_jobs = set(job_details['Job'].astype(str))
            hen_subset = hen_subset[~hen_subset['Job'].isin(existing_jobs)]
            job_details = pd.concat([job_details, hen_subset], ignore_index=True)
        else:
            job_details = hen_subset

    # Merge job details
    if not job_details.empty:
        job_details['Job'] = job_details['Job'].astype(str)
        df['Job'] = df['Job'].astype(str)
        df = df.merge(job_details, on='Job', how='left')

        # For "No Job" rows, set Engineered/Released to special marker
        df.loc[df['Job'] == 'No Job', 'Engineered'] = 'No Job'
        df.loc[df['Job'] == 'No Job', 'Released'] = 'No Job'
    else:
        df['Engineered'] = None
        df['Released'] = None
        df['Qty Completed'] = 0
        df['Run Qty'] = 0
        df['CommentText'] = None

    # Fill NaN values for Qty Completed
    df['Qty Completed'] = df['Qty Completed'].fillna(0)

    # Calculate Remaining Qty (Order Qty - Qty Completed)
    df['Rem Qty'] = df['Order Qty'] - df['Qty Completed']
    df['Rem Qty'] = df['Rem Qty'].clip(lower=0)  # Don't go negative

    # Merge with labor history
    df = df.merge(labor_df, on='Job', how='left')

    # Calculate status
    df['Status'] = df.apply(calculate_status, axis=1)

    # Identify ESI jobs - either job starts with "ESI" or customer is a MED customer
    df['IsESI'] = (
        df['Job'].astype(str).str.upper().str.startswith('ESI') |
        df['Name'].astype(str).str.strip().isin(esi_jobs)
    )

    # Calculate past due flag using Ship By date (like spreadsheet)
    df['IsPastDue'] = df['Ship By'].apply(is_past_due)

    # Mark jobs with material shortages
    if material_shortages:
        df['MaterialShort'] = df['Job'].astype(str).isin(material_shortages)
    else:
        df['MaterialShort'] = False

    # Check if order can ship from inventory (Qty On Hand >= Remaining Qty)
    if part_inventory:
        df['QtyOnHand'] = df['Part'].map(part_inventory).fillna(0)
        df['CanShip'] = df['QtyOnHand'] >= df['Rem Qty']
    else:
        df['QtyOnHand'] = 0
        df['CanShip'] = False

    # Add MB Comments (Purchasing and Operations comments)
    if mb_comments:
        df['PurchasingComments'] = df['OrderLineRel'].map(
            lambda x: mb_comments.get(x, {}).get('purchasing', '')
        )
        df['OperationsComments'] = df['OrderLineRel'].map(
            lambda x: mb_comments.get(x, {}).get('operations', '')
        )
        # Flag if there are any comments
        df['HasComments'] = (df['PurchasingComments'] != '') | (df['OperationsComments'] != '')
    else:
        df['PurchasingComments'] = ''
        df['OperationsComments'] = ''
        df['HasComments'] = False

    # Format dates for display
    for col in ['Need By', 'Ship By', 'Order Date', 'LastLaborDate']:
        if col in df.columns:
            df[f'{col}_Display'] = df[col].dt.strftime('%m/%d/%Y').fillna('')

    return df


def load_all_data():
    """
    Main function to load and process all data.
    Uses Order_Jobs as the primary source (matches WWDispatch spreadsheet)
    and merges in job details from Shop_Orders and HenEngJobs.

    Checks for file updates and caches locally for faster loading.

    Returns a fully enriched DataFrame ready for display.
    """
    # Check for updates and cache files (only checks every 5 minutes)
    print("Checking data cache...")
    cache_status = update_cache_if_needed()

    # Load order lines (primary source - all order lines including "No Job")
    print("Loading order jobs (primary source)...")
    orders_df = load_order_jobs()

    if orders_df.empty:
        print("No order jobs data loaded. Check data file paths.")
        return pd.DataFrame()

    print(f"Loaded {len(orders_df)} order lines")

    # Load shop orders for job details (Engineered, Released, Qty Completed)
    print("Loading shop orders (for job details)...")
    shop_orders_df = load_shop_orders()
    print(f"Loaded {len(shop_orders_df)} jobs from shop orders")

    # Load HenEngJobs for additional job details
    print("Loading HenEngJobs (additional job source)...")
    hen_eng_jobs_df = load_hen_eng_jobs()
    print(f"Loaded {len(hen_eng_jobs_df)} jobs from HenEngJobs")

    # Load labor history
    print("Loading labor history...")
    labor_df = load_labor_history()
    print(f"Loaded labor history for {len(labor_df)} jobs")

    # Load ESI jobs
    print("Loading ESI (medical) customers...")
    esi_customers = load_esi_customers()
    print(f"Identified {len(esi_customers)} ESI customer names")

    # Load material shortages
    print("Loading material shortages...")
    material_shortages = load_material_shortages()
    print(f"Identified {len(material_shortages)} jobs with material shortages")

    # Load MB Comments
    print("Loading MB Comments...")
    mb_comments = load_mb_comments()
    print(f"Loaded comments for {len(mb_comments)} orders")

    # Load part inventory
    print("Loading part inventory...")
    part_inventory = load_part_inventory()
    print(f"Loaded inventory for {len(part_inventory)} parts")

    # Enrich the data
    print("Enriching data...")
    enriched_df = enrich_orders_data(orders_df, shop_orders_df, hen_eng_jobs_df, labor_df, esi_customers, material_shortages, part_inventory, mb_comments)

    print(f"Data loading complete. {len(enriched_df)} order lines ready.")
    return enriched_df


# ============================================================================
# PURCHASING DATA FUNCTIONS
# ============================================================================

def load_open_pos():
    """
    Load open purchase orders from Weco-West-MB_Open_PO.csv.
    Calculates IsOverdue and DaysOverdue fields.

    Returns DataFrame with PO details and overdue status.
    """
    try:
        df = pd.read_csv(get_data_path("open_po"))

        # Parse Due Date
        df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce')
        df['Promise Date'] = pd.to_datetime(df['Promise Date'], errors='coerce')

        # Calculate overdue status
        today = pd.Timestamp.now().normalize()
        df['IsOverdue'] = df['Due Date'] < today
        df['DaysOverdue'] = (today - df['Due Date']).dt.days
        df['DaysOverdue'] = df['DaysOverdue'].fillna(0).astype(int)

        # Calculate days until due (negative means overdue)
        df['DaysUntilDue'] = -df['DaysOverdue']

        # Warning flag for due within 7 days
        df['IsDueSoon'] = (df['DaysUntilDue'] >= 0) & (df['DaysUntilDue'] <= 7)

        # Format dates for display
        df['Due Date_Display'] = df['Due Date'].dt.strftime('%m/%d/%Y').fillna('')
        df['Promise Date_Display'] = df['Promise Date'].dt.strftime('%m/%d/%Y').fillna('')

        # Convert numeric columns
        df['Supplier Qty'] = pd.to_numeric(df['Supplier Qty'], errors='coerce').fillna(0)

        # Clean up Job column (empty strings to None)
        df['Job'] = df['Job'].replace('', pd.NA)

        return df

    except FileNotFoundError:
        print(f"Error: Open PO file not found at {DATA_PATHS.get('open_po')}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading open POs: {str(e)}")
        return pd.DataFrame()


def get_supplier_metrics(open_pos_df):
    """
    Calculate supplier performance metrics from open POs.

    Returns DataFrame with per-supplier metrics:
    - TotalPOs, TotalLines, TotalQty
    - OverdueLines, OnTimeRate
    - LinkedJobs (count of POs linked to jobs)
    """
    if open_pos_df.empty:
        return pd.DataFrame()

    metrics = open_pos_df.groupby('Name').agg({
        'PO': 'nunique',
        'Line': 'count',
        'Supplier Qty': 'sum',
        'IsOverdue': 'sum',
        'Job': lambda x: x.notna().sum()
    }).reset_index()

    metrics.columns = ['Supplier', 'TotalPOs', 'TotalLines', 'TotalQty', 'OverdueLines', 'LinkedJobs']

    # Calculate on-time rate
    metrics['OnTimeRate'] = ((metrics['TotalLines'] - metrics['OverdueLines']) / metrics['TotalLines'] * 100).round(1)

    # Sort by overdue lines descending
    metrics = metrics.sort_values('OverdueLines', ascending=False)

    return metrics


def get_po_job_linkage(open_pos_df, shop_orders_df=None):
    """
    Create linkage between POs and jobs waiting on materials.

    Returns DataFrame showing:
    - PO, Part, Supplier, Due Date
    - Job(s) linked, Job Ship By dates
    """
    if open_pos_df.empty:
        return pd.DataFrame()

    # Filter to only POs with linked jobs
    linked_pos = open_pos_df[open_pos_df['Job'].notna()].copy()

    if linked_pos.empty:
        return pd.DataFrame()

    # Select relevant columns
    result = linked_pos[[
        'PO', 'Part Num', 'Name', 'Due Date_Display', 'DaysUntilDue',
        'Supplier Qty', 'Job', 'IsOverdue'
    ]].copy()

    result.columns = ['PO', 'Part', 'Supplier', 'Due Date', 'Days Until Due',
                      'Qty', 'Job', 'IsOverdue']

    return result


# ============================================================================
# SCHEDULING DATA FUNCTIONS
# ============================================================================

def load_scheduling_data():
    """
    Load and prepare data for Gantt chart visualization.
    Merges Shop Orders with Order Jobs for complete scheduling view.

    Returns DataFrame with job scheduling information.
    """
    # Load the enriched dispatch data (already has all the merges)
    df = load_all_data()

    if df.empty:
        return pd.DataFrame()

    # Add scheduling-specific fields
    # Use Order Date as start, Ship By as end
    df['Start'] = df.get('Order Date', pd.NaT)
    df['End'] = df.get('Ship By', pd.NaT)

    # For jobs without Order Date, use today - 7 days
    today = pd.Timestamp.now().normalize()
    df['Start'] = df['Start'].fillna(today - timedelta(days=7))

    # For jobs without Ship By, use Need By or today + 30 days
    df['End'] = df['End'].fillna(df.get('Need By', today + timedelta(days=30)))
    df['End'] = df['End'].fillna(today + timedelta(days=30))

    # Calculate progress percentage
    df['Progress'] = (df['Qty Completed'] / df['Order Qty'] * 100).fillna(0).clip(0, 100).round(1)

    # Ensure we have all needed columns
    needed_cols = ['Job', 'Part', 'Description', 'Name', 'Status',
                   'Order Qty', 'Qty Completed', 'Rem Qty', 'Progress',
                   'Start', 'End', 'Ship By', 'Need By', 'IsPastDue',
                   'Engineered', 'Released', 'MaterialShort']

    for col in needed_cols:
        if col not in df.columns:
            df[col] = None

    return df


def prepare_gantt_data(df, group_by='ship_date'):
    """
    Transform jobs into Gantt-compatible format.

    Args:
        df: DataFrame from load_scheduling_data()
        group_by: 'ship_date', 'customer', or 'work_center'

    Returns DataFrame with Start, End, Group, Status for Plotly timeline.
    """
    if df.empty:
        return pd.DataFrame()

    result = df.copy()

    if group_by == 'ship_date':
        # Group by week of Ship By date
        result['Group'] = result['End'].dt.to_period('W').apply(
            lambda x: f"Week of {x.start_time.strftime('%m/%d')}" if pd.notna(x) else "No Date"
        )
    elif group_by == 'customer':
        # Group by customer name
        result['Group'] = result['Name'].fillna('Unknown Customer')
    elif group_by == 'work_center':
        # For now, use first word of Description as work center proxy
        # In future, could map to actual work centers
        result['Group'] = result['Description'].fillna('').apply(
            lambda x: x.split()[0] if x else 'Unknown'
        )
    else:
        result['Group'] = 'All Jobs'

    # Ensure Start and End are datetime
    result['Start'] = pd.to_datetime(result['Start'], errors='coerce')
    result['End'] = pd.to_datetime(result['End'], errors='coerce')

    # Fill any remaining NaT values
    today = pd.Timestamp.now().normalize()
    result['Start'] = result['Start'].fillna(today)
    result['End'] = result['End'].fillna(today + timedelta(days=7))

    # Ensure End is after Start
    result.loc[result['End'] <= result['Start'], 'End'] = result['Start'] + timedelta(days=1)

    return result


def get_work_centers():
    """
    Get unique work centers from Shop Orders Operation Description.

    Returns list of unique work center/operation names.
    """
    try:
        df = pd.read_csv(get_data_path("shop_orders"))
        if 'Operation Description' in df.columns:
            work_centers = df['Operation Description'].dropna().unique().tolist()
            return sorted(work_centers)
        return []
    except Exception as e:
        print(f"Error loading work centers: {str(e)}")
        return []


if __name__ == "__main__":
    # Test the data loader
    df = load_all_data()
    print("\nData sample:")
    print(df.head())
    print("\nColumns:")
    print(df.columns.tolist())
    print("\nStatus distribution:")
    print(df['Status'].value_counts())
