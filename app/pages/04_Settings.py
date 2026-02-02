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


def list_data_files(folder_path):
    """List data files (CSV, Excel) in a folder"""
    files = []
    if folder_path and os.path.exists(folder_path):
        try:
            for f in os.listdir(folder_path):
                if f.lower().endswith(('.csv', '.xlsx', '.xls', '.xml')):
                    files.append(f)
            files.sort()
        except Exception:
            pass
    return files


def find_matching_file(files, expected_filename):
    """Find a file that matches the expected filename (case-insensitive)"""
    expected_lower = expected_filename.lower()
    for f in files:
        if f.lower() == expected_lower:
            return f
    # Try partial match
    for f in files:
        if expected_lower in f.lower() or f.lower() in expected_lower:
            return f
    return None


def main():
    st.title("⚙️ Settings")
    st.caption("Configure data file paths and application settings")

    # Load current settings
    user_settings = load_user_settings()

    # Data folder section
    st.markdown("---")
    st.markdown("### 📁 Data Folders")
    st.caption("Set the folders where your data files are located. Common network paths are provided as defaults.")

    # Common network paths for quick selection
    COMMON_PATHS = {
        "Epicor Data": r"\\192.168.168.230\EpicorData\Companies\FTTMFG\Processes\MMINOIA",
        "WW Shop Load": r"\\192.168.168.88\Henfiles\Users Shared Folders\Leadership Team\WW Shop Load",
        "Local Data": str(DATA_PATHS.get('shop_orders', '').parent),
    }

    st.caption("**Quick Select:**")
    quick_cols = st.columns(len(COMMON_PATHS))
    for i, (name, path) in enumerate(COMMON_PATHS.items()):
        with quick_cols[i]:
            if st.button(f"📁 {name}", key=f"quick_{name}", use_container_width=True):
                st.session_state['quick_path'] = path

    # Check if quick select was used
    if 'quick_path' in st.session_state:
        quick_selected = st.session_state['quick_path']
        del st.session_state['quick_path']
    else:
        quick_selected = None

    default_data_dir = quick_selected or user_settings.get('data_dir', COMMON_PATHS["Epicor Data"])
    data_dir = st.text_input(
        "Primary Data Folder Path",
        value=default_data_dir,
        help="Main folder containing your CSV/Excel data files (e.g., Epicor exports)"
    )

    # Secondary data folder for files in different locations
    default_data_dir2 = user_settings.get('data_dir2', COMMON_PATHS["WW Shop Load"])
    data_dir2 = st.text_input(
        "Secondary Data Folder (WW Shop Load)",
        value=default_data_dir2,
        help="Additional folder for files like Shop Orders and Order Jobs"
    )

    # Show folder status
    col1, col2 = st.columns(2)
    with col1:
        if data_dir:
            if os.path.exists(data_dir):
                st.success(f"✅ Primary folder exists")
            else:
                st.warning(f"⚠️ Primary folder not found")
    with col2:
        if data_dir2:
            if os.path.exists(data_dir2):
                st.success(f"✅ Secondary folder exists")
            else:
                st.warning(f"⚠️ Secondary folder not found")

    # File browser expander
    available_files = []
    if data_dir and os.path.exists(data_dir):
        available_files.extend([(f, data_dir) for f in list_data_files(data_dir)])
    if data_dir2 and os.path.exists(data_dir2):
        available_files.extend([(f, data_dir2) for f in list_data_files(data_dir2)])

    if available_files:
        with st.expander(f"📂 Browse Available Files ({len(available_files)} data files found)", expanded=False):
            st.caption("Files found in your data folders:")
            # Group by folder
            if data_dir and os.path.exists(data_dir):
                files_in_dir1 = list_data_files(data_dir)
                if files_in_dir1:
                    st.markdown(f"**Primary folder:** `{data_dir}`")
                    for f in files_in_dir1:
                        st.text(f"  • {f}")
            if data_dir2 and os.path.exists(data_dir2):
                files_in_dir2 = list_data_files(data_dir2)
                if files_in_dir2:
                    st.markdown(f"**Secondary folder:** `{data_dir2}`")
                    for f in files_in_dir2:
                        st.text(f"  • {f}")
            st.info("💡 Copy the filename and paste into the path fields below, or the paths will auto-fill when you set the data folder.")

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

    def get_best_path(key, filename, saved_path):
        """Find the best path for a file, checking saved settings and both data folders"""
        # First check if user already has a saved path that exists
        if saved_path and os.path.exists(saved_path):
            return saved_path
        # Try primary data folder
        if data_dir:
            path1 = os.path.join(data_dir, filename)
            if os.path.exists(path1):
                return path1
        # Try secondary data folder
        if data_dir2:
            path2 = os.path.join(data_dir2, filename)
            if os.path.exists(path2):
                return path2
        # Return saved path or construct default
        if saved_path:
            return saved_path
        return os.path.join(data_dir, filename) if data_dir else ""

    core_settings = {}
    for key, config in core_files.items():
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            st.markdown(f"**{config['label']}**")
            st.caption(config['description'])
        with col2:
            st.text_input(
                "Expected filename",
                value=config['filename'],
                key=f"expected_{key}",
                disabled=True,
                label_visibility="collapsed"
            )
        with col3:
            saved_path = user_settings.get(key, "")
            default_path = get_best_path(key, config['filename'], saved_path)
            path = st.text_input(
                f"Path for {config['label']}",
                value=default_path,
                key=f"path_{key}",
                label_visibility="collapsed",
                placeholder="Enter full file path..."
            )
            core_settings[key] = path
        with col4:
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
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            st.markdown(f"**{config['label']}**")
            st.caption(config['description'])
        with col2:
            st.text_input(
                "Expected filename",
                value=config['filename'],
                key=f"expected_{key}",
                disabled=True,
                label_visibility="collapsed"
            )
        with col3:
            saved_path = user_settings.get(key, "")
            default_path = get_best_path(key, config['filename'], saved_path)
            path = st.text_input(
                f"Path for {config['label']}",
                value=default_path,
                key=f"path_{key}",
                label_visibility="collapsed",
                placeholder="Enter full file path..."
            )
            supporting_settings[key] = path
        with col4:
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
                'data_dir2': data_dir2,
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
