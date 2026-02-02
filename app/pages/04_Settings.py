"""
Settings Page - Configure data file paths and application settings
"""
import streamlit as st
import json
import os
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.settings import APP_TITLE, PAGE_ICON, DATA_PATHS, BASE_DIR

# Page configuration
st.set_page_config(
    page_title=f"Settings - {APP_TITLE}",
    page_icon=PAGE_ICON,
    layout="wide"
)

# Settings file location
SETTINGS_FILE = BASE_DIR / "config" / "user_settings.json"


def load_user_settings():
    """Load user settings from JSON file"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading settings: {e}")
    return {}


def save_user_settings(settings):
    """Save user settings to JSON file"""
    try:
        # Ensure config directory exists
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving settings: {e}")
        return False


def check_file_exists(path):
    """Check if a file exists and return status"""
    if not path:
        return "⚪ Not configured"
    if os.path.exists(path):
        return "✅ Found"
    return "❌ Not found"


def main():
    st.title("⚙️ Settings")
    st.caption("Configure data file paths and application settings")

    # Load current settings
    user_settings = load_user_settings()

    # Data folder section
    st.markdown("---")
    st.markdown("### 📁 Data Folder")
    st.caption("Set the base folder where your data files are located, or configure each file individually below.")

    default_data_dir = user_settings.get('data_dir', str(DATA_PATHS.get('shop_orders', '').parent))
    data_dir = st.text_input(
        "Data Folder Path",
        value=default_data_dir,
        help="Base folder containing your CSV/Excel data files"
    )

    if data_dir:
        if os.path.exists(data_dir):
            st.success(f"✅ Folder exists: {data_dir}")
        else:
            st.warning(f"⚠️ Folder not found: {data_dir}")

    # Core Data Files section
    st.markdown("---")
    st.markdown("### 📄 Core Data Files")
    st.caption("These files are required for the main Dispatch functionality")

    # Define file configurations with descriptions
    core_files = {
        "shop_orders": {
            "label": "Shop Orders",
            "filename": "Weco-West-MB_Shop_Orders.csv",
            "description": "Job and operation details",
            "required": True
        },
        "order_jobs": {
            "label": "Order Jobs",
            "filename": "Weco-West-MB_Order_Jobs.csv",
            "description": "Order line information (primary dispatch data)",
            "required": True
        },
        "labor_history": {
            "label": "Labor History",
            "filename": "PK-LaborHistory.csv",
            "description": "Employee labor records",
            "required": True
        },
        "part_cost": {
            "label": "Part Cost / Inventory",
            "filename": "WECO-West-PartCost.csv",
            "description": "Part inventory levels (Qty On Hand)",
            "required": True
        },
        "material_shortage": {
            "label": "Material Shortage",
            "filename": "wecoWest-materialshortage.csv",
            "description": "Jobs with material shortages",
            "required": True
        },
    }

    core_settings = {}
    for key, config in core_files.items():
        col1, col2, col3 = st.columns([2, 3, 1])
        with col1:
            st.markdown(f"**{config['label']}**")
            st.caption(config['description'])
        with col2:
            default_path = user_settings.get(key, os.path.join(data_dir, config['filename']) if data_dir else "")
            path = st.text_input(
                f"Path for {config['label']}",
                value=default_path,
                key=f"path_{key}",
                label_visibility="collapsed"
            )
            core_settings[key] = path
        with col3:
            status = check_file_exists(path)
            st.markdown(status)

    # Supporting Files section
    st.markdown("---")
    st.markdown("### 📋 Supporting Files")
    st.caption("Additional files for enhanced functionality")

    supporting_files = {
        "customer_names": {
            "label": "Customer Names",
            "filename": "Customer Names.xlsx",
            "description": "Customer list with ESI/MED classification"
        },
        "comments_operations": {
            "label": "MB Comments",
            "filename": "MB Comments.xlsx",
            "description": "Operations and purchasing comments"
        },
        "open_po": {
            "label": "Open POs",
            "filename": "Weco-West-MB_Open_PO.csv",
            "description": "Open purchase orders (for Purchasing page)"
        },
        "order_backlog": {
            "label": "ESC Order Backlog",
            "filename": "Weco-West-ESC-OrderBacklog.csv",
            "description": "ESC/ESI order backlog"
        },
    }

    supporting_settings = {}
    for key, config in supporting_files.items():
        col1, col2, col3 = st.columns([2, 3, 1])
        with col1:
            st.markdown(f"**{config['label']}**")
            st.caption(config['description'])
        with col2:
            default_path = user_settings.get(key, os.path.join(data_dir, config['filename']) if data_dir else "")
            path = st.text_input(
                f"Path for {config['label']}",
                value=default_path,
                key=f"path_{key}",
                label_visibility="collapsed"
            )
            supporting_settings[key] = path
        with col3:
            status = check_file_exists(path)
            st.markdown(status)

    # Drawing Paths section
    st.markdown("---")
    st.markdown("### 🖼️ Drawing Paths")
    st.caption("Network paths for part drawings")

    col1, col2 = st.columns(2)
    with col1:
        esi_drawing_path = st.text_input(
            "ESI Drawings Base Path",
            value=user_settings.get('esi_drawing_path', '//wecofiles.weco.com/Drawings/ESI Drawings/ESI Drawings'),
            help="Path to ESI drawings folder. Part number folder will be appended."
        )
    with col2:
        non_esi_drawing_path = st.text_input(
            "Non-ESI Drawings Base Path",
            value=user_settings.get('non_esi_drawing_path', '//200.200.200.230/Drawings/Customers'),
            help="Path to customer drawings. Customer name and part number folders will be appended."
        )

    # Save button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            all_settings = {
                'data_dir': data_dir,
                'esi_drawing_path': esi_drawing_path,
                'non_esi_drawing_path': non_esi_drawing_path,
                **core_settings,
                **supporting_settings
            }
            if save_user_settings(all_settings):
                st.success("✅ Settings saved! Restart the app to apply changes.")
                st.balloons()

    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            if SETTINGS_FILE.exists():
                os.remove(SETTINGS_FILE)
                st.success("Settings reset to defaults. Refresh the page.")
                st.rerun()

    # Status Summary
    st.markdown("---")
    st.markdown("### 📊 Status Summary")

    all_paths = {**core_settings, **supporting_settings}
    found = sum(1 for p in all_paths.values() if p and os.path.exists(p))
    total = len(all_paths)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Files Found", f"{found}/{total}")
    with col2:
        missing = [k for k, v in core_settings.items() if not v or not os.path.exists(v)]
        st.metric("Missing Core Files", len(missing))
    with col3:
        if found == total:
            st.success("All files configured!")
        elif found >= len(core_settings):
            st.info("Core files ready")
        else:
            st.warning("Some core files missing")


if __name__ == "__main__":
    main()
