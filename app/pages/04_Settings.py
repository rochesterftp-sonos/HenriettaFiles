"""
Settings Page - Configure data file paths and application settings
"""
import streamlit as st
import json
import os
import platform
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Detect operating system
IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

from config.settings import APP_TITLE, PAGE_ICON, DATA_PATHS, BASE_DIR
from app.utils.data_loader import get_cache_status, update_cache_if_needed

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


def open_folder_picker(title="Select Folder", initial_dir=None):
    """Open a native folder picker dialog"""
    try:
        import tkinter as tk
        from tkinter import filedialog

        # Create a hidden root window
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Bring dialog to front

        # Set initial directory
        if initial_dir and os.path.exists(initial_dir):
            start_dir = initial_dir
        elif IS_MAC:
            start_dir = "/Volumes"
        else:
            start_dir = "C:\\"

        # Open the folder picker
        folder_path = filedialog.askdirectory(
            title=title,
            initialdir=start_dir
        )

        root.destroy()
        return folder_path if folder_path else None
    except Exception as e:
        st.error(f"Could not open folder picker: {e}")
        return None


def open_file_picker(title="Select File", initial_dir=None, filetypes=None):
    """Open a native file picker dialog"""
    try:
        import tkinter as tk
        from tkinter import filedialog

        # Create a hidden root window
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        # Set initial directory
        if initial_dir and os.path.exists(initial_dir):
            start_dir = initial_dir
        elif IS_MAC:
            start_dir = "/Volumes"
        else:
            start_dir = "C:\\"

        # Default filetypes
        if filetypes is None:
            filetypes = [
                ("Data files", "*.csv *.xlsx *.xls *.xml"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*")
            ]

        # Open the file picker
        file_path = filedialog.askopenfilename(
            title=title,
            initialdir=start_dir,
            filetypes=filetypes
        )

        root.destroy()
        return file_path if file_path else None
    except Exception as e:
        st.error(f"Could not open file picker: {e}")
        return None


def main():
    st.title("⚙️ Settings")
    st.caption("Configure data file paths and application settings")

    # Load current settings
    user_settings = load_user_settings()

    # Data folder section
    st.markdown("---")
    st.markdown("### 📁 Data Folders")

    # Show current OS
    os_name = "macOS" if IS_MAC else "Windows" if IS_WINDOWS else "Linux"
    st.caption(f"Detected OS: **{os_name}** - Use the Browse buttons to select folders from Finder/Explorer")

    # Common network paths - different for Mac vs Windows
    if IS_MAC:
        # Mac paths - network shares mounted in /Volumes
        COMMON_PATHS = {
            "Epicor Data": "/Volumes/EpicorData/Companies/FTTMFG/Processes/MMINOIA",
            "WW Shop Load": "/Volumes/Henfiles/Users Shared Folders/Leadership Team/WW Shop Load",
            "Local Data": str(DATA_PATHS.get('shop_orders', '').parent),
        }
    else:
        # Windows UNC paths
        COMMON_PATHS = {
            "Epicor Data": r"\\192.168.168.230\EpicorData\Companies\FTTMFG\Processes\MMINOIA",
            "WW Shop Load": r"\\192.168.168.88\Henfiles\Users Shared Folders\Leadership Team\WW Shop Load",
            "Local Data": str(DATA_PATHS.get('shop_orders', '').parent),
        }

    st.caption("**Quick Select (preset paths):**")
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

    # Primary data folder with browse button
    st.markdown("**Primary Data Folder**")
    col_input1, col_browse1 = st.columns([5, 1])
    with col_input1:
        default_data_dir = quick_selected or user_settings.get('data_dir', COMMON_PATHS["Epicor Data"])
        data_dir = st.text_input(
            "Primary Data Folder Path",
            value=default_data_dir,
            help="Main folder containing your CSV/Excel data files (e.g., Epicor exports)",
            label_visibility="collapsed"
        )
    with col_browse1:
        if st.button("📂 Browse", key="browse_primary", use_container_width=True):
            selected = open_folder_picker("Select Primary Data Folder")
            if selected:
                st.session_state['selected_primary'] = selected
                st.rerun()

    # Check if folder was just selected
    if 'selected_primary' in st.session_state:
        data_dir = st.session_state['selected_primary']
        del st.session_state['selected_primary']

    # Secondary data folder with browse button
    st.markdown("**Secondary Data Folder (WW Shop Load)**")
    col_input2, col_browse2 = st.columns([5, 1])
    with col_input2:
        default_data_dir2 = user_settings.get('data_dir2', COMMON_PATHS["WW Shop Load"])
        data_dir2 = st.text_input(
            "Secondary Data Folder",
            value=default_data_dir2,
            help="Additional folder for files like Shop Orders and Order Jobs",
            label_visibility="collapsed"
        )
    with col_browse2:
        if st.button("📂 Browse", key="browse_secondary", use_container_width=True):
            selected = open_folder_picker("Select Secondary Data Folder")
            if selected:
                st.session_state['selected_secondary'] = selected
                st.rerun()

    # Check if folder was just selected
    if 'selected_secondary' in st.session_state:
        data_dir2 = st.session_state['selected_secondary']
        del st.session_state['selected_secondary']

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
        col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 0.5, 0.5])
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
            # Check if file was just selected via picker
            picker_key = f"picked_file_{key}"
            if picker_key in st.session_state:
                default_path = st.session_state[picker_key]
                del st.session_state[picker_key]
            else:
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
            if st.button("📄", key=f"pick_{key}", help="Browse for file"):
                selected = open_file_picker(
                    title=f"Select {config['label']}",
                    initial_dir=data_dir if data_dir else None
                )
                if selected:
                    st.session_state[f"picked_file_{key}"] = selected
                    st.rerun()
        with col5:
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
        col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 0.5, 0.5])
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
            # Check if file was just selected via picker
            picker_key = f"picked_file_{key}"
            if picker_key in st.session_state:
                default_path = st.session_state[picker_key]
                del st.session_state[picker_key]
            else:
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
            if st.button("📄", key=f"pick_{key}", help="Browse for file"):
                selected = open_file_picker(
                    title=f"Select {config['label']}",
                    initial_dir=data_dir if data_dir else None
                )
                if selected:
                    st.session_state[f"picked_file_{key}"] = selected
                    st.rerun()
        with col5:
            status = check_file_exists(path)
            st.markdown(status)

    # Drawing Paths section
    st.markdown("---")
    st.markdown("### 🖼️ Drawing / Image File Paths")
    st.caption("Network paths for part drawings and image files (wecofiles server: 200.200.200.230)")

    # Default drawing paths based on OS
    # wecofiles server IP: 200.200.200.230
    if IS_MAC:
        # Mac paths - network shares mounted in /Volumes
        # The share name may vary - common mount points
        default_esi_path = "/Volumes/Drawings/ESI Drawings/ESI Drawings"
        default_non_esi_path = "/Volumes/Drawings/Customers"
    else:
        # Windows UNC paths using IP address
        default_esi_path = r"\\200.200.200.230\Drawings\ESI Drawings\ESI Drawings"
        default_non_esi_path = r"\\200.200.200.230\Drawings\Customers"

    # ESI Drawings path
    st.markdown("**ESI Drawings Base Path**")
    col1a, col1b = st.columns([5, 1])
    with col1a:
        # Check if folder was just selected via picker
        if 'picked_esi_drawing' in st.session_state:
            esi_default = st.session_state['picked_esi_drawing']
            del st.session_state['picked_esi_drawing']
        else:
            esi_default = user_settings.get('esi_drawing_path', default_esi_path)

        esi_drawing_path = st.text_input(
            "ESI Drawings Path",
            value=esi_default,
            help="Path to ESI drawings folder. Part number folder will be appended.",
            label_visibility="collapsed"
        )
    with col1b:
        if st.button("📂 Browse", key="browse_esi_drawings"):
            selected = open_folder_picker("Select ESI Drawings Folder")
            if selected:
                st.session_state['picked_esi_drawing'] = selected
                st.rerun()

    # Non-ESI Drawings path
    st.markdown("**Non-ESI Drawings Base Path**")
    col2a, col2b = st.columns([5, 1])
    with col2a:
        # Check if folder was just selected via picker
        if 'picked_non_esi_drawing' in st.session_state:
            non_esi_default = st.session_state['picked_non_esi_drawing']
            del st.session_state['picked_non_esi_drawing']
        else:
            non_esi_default = user_settings.get('non_esi_drawing_path', default_non_esi_path)

        non_esi_drawing_path = st.text_input(
            "Non-ESI Drawings Path",
            value=non_esi_default,
            help="Path to customer drawings. Customer name and part number folders will be appended.",
            label_visibility="collapsed"
        )
    with col2b:
        if st.button("📂 Browse", key="browse_non_esi_drawings"):
            selected = open_folder_picker("Select Non-ESI Drawings Folder")
            if selected:
                st.session_state['picked_non_esi_drawing'] = selected
                st.rerun()

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

    # Data Cache & File Timestamps Section
    st.markdown("---")
    st.markdown("### 🕐 Data Cache & File Timestamps")
    st.caption("Files are cached locally for faster loading. Cache is checked for updates every 5 minutes.")

    # Get cache status
    try:
        cache_status = get_cache_status()
        last_check = cache_status.get("_last_check_str", "Never")
        st.info(f"Last cache check: **{last_check}**")

        # Force refresh button
        col_refresh1, col_refresh2 = st.columns([1, 3])
        with col_refresh1:
            if st.button("🔄 Force Refresh Cache", use_container_width=True):
                with st.spinner("Checking for updates..."):
                    update_cache_if_needed(force=True)
                    st.success("Cache refreshed!")
                    st.rerun()

        # Display file timestamps in a table
        file_labels = {
            "order_jobs": "Order Jobs",
            "shop_orders": "Shop Orders",
            "labor_history": "Labor History",
            "part_cost": "Part Cost / Inventory",
            "material_shortage": "Material Shortage",
            "material_not_issued": "Material Not Issued (XML)",
            "customer_names": "Customer Names",
            "comments_operations": "MB Comments",
            "open_po": "Open POs",
            "order_backlog": "ESC Order Backlog",
        }

        st.markdown("**File Status:**")

        # Create columns for the table header
        hcol1, hcol2, hcol3, hcol4 = st.columns([2, 3, 1, 1])
        with hcol1:
            st.markdown("**File**")
        with hcol2:
            st.markdown("**Last Modified**")
        with hcol3:
            st.markdown("**Cached**")
        with hcol4:
            st.markdown("**Status**")

        for key, label in file_labels.items():
            info = cache_status.get(key, {})
            source_time = info.get("source_time", "Unknown")
            is_cached = info.get("cached", False)
            error = info.get("error")

            col1, col2, col3, col4 = st.columns([2, 3, 1, 1])
            with col1:
                st.text(label)
            with col2:
                st.text(source_time)
            with col3:
                st.text("✅" if is_cached else "❌")
            with col4:
                if error:
                    st.text(f"⚠️ {error[:20]}")
                elif is_cached:
                    st.text("✅ OK")
                else:
                    st.text("⏳ Pending")

    except Exception as e:
        st.warning(f"Could not load cache status: {e}")


if __name__ == "__main__":
    main()
