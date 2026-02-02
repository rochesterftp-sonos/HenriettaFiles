"""
Data loading utilities for Henrietta Dispatch Application
Handles reading CSV/Excel files and processing them for the application
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import DATA_PATHS, DATE_FORMAT


def load_shop_orders():
    """
    Load shop orders data from CSV file
    Returns a processed DataFrame with one row per job (not per operation)
    """
    try:
        # Read the CSV file
        df = pd.read_csv(DATA_PATHS["shop_orders"])

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
        job_df = df.groupby('Job', as_index=False).agg({
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
        })

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
            DATA_PATHS["labor_history"],
            header=None,
            names=['Employee', 'Date', 'Type', 'Job', 'Hours', 'Col6', 'Col7']
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


def load_esi_jobs():
    """
    Load ESI/ESC order backlog to identify ESI jobs
    Returns a set of job numbers that are ESI-related
    """
    try:
        df = pd.read_csv(DATA_PATHS["order_backlog"])

        # Get unique job numbers (if the column exists)
        if 'Job' in df.columns:
            return set(df['Job'].dropna().astype(str))
        else:
            return set()

    except FileNotFoundError:
        print(f"Warning: ESI backlog file not found at {DATA_PATHS['order_backlog']}")
        return set()
    except Exception as e:
        print(f"Error loading ESI jobs: {str(e)}")
        return set()


def calculate_status(row):
    """
    Calculate the status of a job based on business rules

    Status Logic:
    - If not Engineered: "Unengineered"
    - If Qty Completed > 0: "In-Work"
    - Otherwise: "Not Started"

    Note: Inventory-based statuses (Can Ship, Partial) will be added
    when inventory data becomes available
    """
    if pd.isna(row['Engineered']) or row['Engineered'] == False:
        return 'unengineered'
    elif row['Qty Completed'] > 0:
        return 'in_work'
    else:
        return 'not_started'


def is_past_due(due_date):
    """Check if a due date is in the past"""
    if pd.isna(due_date):
        return False
    return due_date < pd.Timestamp.now()


def enrich_orders_data(orders_df, labor_df, esi_jobs):
    """
    Enrich orders data with calculated fields and joined data

    Args:
        orders_df: DataFrame of orders
        labor_df: DataFrame of labor history
        esi_jobs: Set of ESI job numbers

    Returns:
        Enriched DataFrame
    """
    # Merge with labor history
    df = orders_df.merge(labor_df, on='Job', how='left')

    # Calculate status
    df['Status'] = df.apply(calculate_status, axis=1)

    # Identify ESI jobs
    df['IsESI'] = df['Job'].astype(str).isin(esi_jobs)

    # Calculate past due flag
    df['IsPastDue'] = df['Due Date'].apply(is_past_due)

    # Calculate remaining quantity
    df['RemainingQty'] = df['Selling Requested Qty'] - df['Qty Completed']

    # Format dates for display
    for col in ['Due Date', 'Need By', 'Ship By', 'LastLaborDate']:
        if col in df.columns:
            df[f'{col}_Display'] = df[col].dt.strftime('%m/%d/%Y').fillna('')

    return df


def load_all_data():
    """
    Main function to load and process all data
    Returns a fully enriched DataFrame ready for display
    """
    print("Loading shop orders...")
    orders_df = load_shop_orders()

    if orders_df.empty:
        print("No orders data loaded. Check data file paths.")
        return pd.DataFrame()

    print(f"Loaded {len(orders_df)} orders")

    print("Loading labor history...")
    labor_df = load_labor_history()
    print(f"Loaded labor history for {len(labor_df)} jobs")

    print("Loading ESI jobs...")
    esi_jobs = load_esi_jobs()
    print(f"Identified {len(esi_jobs)} ESI jobs")

    print("Enriching data...")
    enriched_df = enrich_orders_data(orders_df, labor_df, esi_jobs)

    print(f"Data loading complete. {len(enriched_df)} orders ready.")
    return enriched_df


if __name__ == "__main__":
    # Test the data loader
    df = load_all_data()
    print("\nData sample:")
    print(df.head())
    print("\nColumns:")
    print(df.columns.tolist())
    print("\nStatus distribution:")
    print(df['Status'].value_counts())
