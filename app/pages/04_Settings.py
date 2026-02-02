"""
Settings Page - Configure data file paths and show file versions
"""
import streamlit as st
import json
import os
import platform
from pathlib import Path
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

from config.settings import APP_TITLE, PAGE_ICON, DATA_PATHS, BASE_DIR

st.set_page_config(
    page_title=f"Settings - {APP_TITLE}",
    page_icon=PAGE_ICON,
    layout="wide"
)

SETTINGS_FILE = BASE_DIR / "config" / "user_settings.json"

# Key data files we care about
KEY_FILES = {
    "order_jobs": ("Order Jobs", "Weco-West-MB_Order_Jobs.csv"),
    "shop_orders": ("Shop Orders", "Weco-West-MB_Shop_Orders.csv"),
    "labor_history": ("Labor History", "PK-LaborHistory.csv"),
    "part_cost": ("Part Cost / Inventory", "WECO-West-PartCost.csv"),
    "material_shortage": ("Material Shortage", "wecoWest-materialshortage.csv"),
    "customer_names": ("Customer Names", "Customer Names.xlsx"),
    "comments_operations": ("MB Comments", "MB Comments.xlsx"),
    "open_po": ("Open POs", "Weco-West-MB_Open_PO.csv"),
}


def load_user_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_user_settings(settings):
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving: {e}")
        return False


def get_file_info(path):
    """Get file info without blocking - returns cached info or pending"""
    if not path:
        return {"status": "⚪", "time": "Not configured", "exists": False}
    try:
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            time_str = datetime.fromtimestamp(mtime).strftime("%m/%d/%Y %I:%M %p")
            return {"status": "✅", "time": time_str, "exists": True}
        else:
            return {"status": "❌", "time": "File not found", "exists": False}
    except:
        return {"status": "⚠️", "time": "Error checking", "exists": False}


def main():
    st.title("⚙️ Settings")

    user_settings = load_user_settings()

    # OS-specific default paths
    if IS_MAC:
        default_primary = "/Volumes/EpicorData/Companies/FTTMFG/Processes/MMINOIA"
        default_secondary = "/Volumes/Henfiles/Users Shared Folders/Leadership Team/WW Shop Load"
        default_esi = "/Volumes/Drawings/ESI Drawings/ESI Drawings"
        default_non_esi = "/Volumes/Drawings/Customers"
    else:
        default_primary = r"\\192.168.168.230\EpicorData\Companies\FTTMFG\Processes\MMINOIA"
        default_secondary = r"\\192.168.168.88\Henfiles\Users Shared Folders\Leadership Team\WW Shop Load"
        default_esi = r"\\200.200.200.230\Drawings\ESI Drawings\ESI Drawings"
        default_non_esi = r"\\200.200.200.230\Drawings\Customers"

    # Data Folders
    st.markdown("### 📁 Data Folders")
    data_dir = st.text_input("Primary Data Folder", value=user_settings.get('data_dir', default_primary))
    data_dir2 = st.text_input("Secondary Data Folder", value=user_settings.get('data_dir2', default_secondary))

    # Drawing Paths
    st.markdown("### 🖼️ Drawing Paths")
    esi_path = st.text_input("ESI Drawings", value=user_settings.get('esi_drawing_path', default_esi))
    non_esi_path = st.text_input("Non-ESI Drawings", value=user_settings.get('non_esi_drawing_path', default_non_esi))

    # Save button
    if st.button("💾 Save Settings", type="primary"):
        settings = {
            'data_dir': data_dir,
            'data_dir2': data_dir2,
            'esi_drawing_path': esi_path,
            'non_esi_drawing_path': non_esi_path,
        }
        # Add file paths
        for key, (label, filename) in KEY_FILES.items():
            path1 = os.path.join(data_dir, filename) if data_dir else ""
            path2 = os.path.join(data_dir2, filename) if data_dir2 else ""
            # Use whichever path exists, prefer primary
            if os.path.exists(path1):
                settings[key] = path1
            elif os.path.exists(path2):
                settings[key] = path2
            else:
                settings[key] = path1  # Default to primary

        if save_user_settings(settings):
            st.success("✅ Settings saved!")

    # File Status Section
    st.markdown("---")
    st.markdown("### 📊 Data Files Being Used")
    st.caption("Click 'Check Files' to verify file locations and see timestamps")

    if st.button("✅ Check Files"):
        st.session_state.check_files = True

    if st.session_state.get('check_files'):
        with st.spinner("Checking files..."):
            # Table header
            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                st.markdown("**Status**")
            with col2:
                st.markdown("**File**")
            with col3:
                st.markdown("**Last Modified**")

            st.markdown("---")

            found_count = 0
            for key, (label, filename) in KEY_FILES.items():
                # Check both folders
                path1 = os.path.join(data_dir, filename) if data_dir else ""
                path2 = os.path.join(data_dir2, filename) if data_dir2 else ""

                # Get info for whichever exists
                if path1 and os.path.exists(path1):
                    info = get_file_info(path1)
                    used_path = "Primary"
                elif path2 and os.path.exists(path2):
                    info = get_file_info(path2)
                    used_path = "Secondary"
                else:
                    info = get_file_info(path1)  # Will show not found
                    used_path = ""

                if info['exists']:
                    found_count += 1

                col1, col2, col3 = st.columns([1, 3, 2])
                with col1:
                    st.markdown(info['status'])
                with col2:
                    st.markdown(f"**{label}**")
                    if used_path:
                        st.caption(f"From {used_path} folder")
                with col3:
                    st.text(info['time'])

            st.markdown("---")
            st.metric("Files Found", f"{found_count}/{len(KEY_FILES)}")


if __name__ == "__main__":
    main()
