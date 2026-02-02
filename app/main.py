"""
Henrietta Dispatch Application - Main Entry Point
A Streamlit-based web application for production planning and dispatch management
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import time
import base64
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import (
    APP_TITLE, PAGE_ICON, COLORS, STATUS_NAMES,
    REFRESH_INTERVAL, DRAWING_URL_PATTERN, PO_URL_PATTERN
)
from app.utils.data_loader import load_all_data, get_job_operations, get_material_shortage_details, load_user_settings
from app.utils.database import init_database, add_note, get_notes, get_notes_count


def get_drawing_folder(part_number, customer_name, is_esi):
    """Get the folder path for part drawings based on ESI status"""
    import platform

    if not part_number:
        return None

    # Load user settings for custom paths
    user_settings = load_user_settings()

    # Detect OS for default paths
    is_mac = platform.system() == "Darwin"

    if is_esi:
        # ESI path - wecofiles server (200.200.200.230)
        if is_mac:
            default_path = "/Volumes/Drawings/ESI Drawings/ESI Drawings"
        else:
            default_path = r"\\200.200.200.230\Drawings\ESI Drawings\ESI Drawings"
        base_path = user_settings.get('esi_drawing_path', default_path)
        folder = os.path.join(base_path, part_number)
    else:
        # Non-ESI path - wecofiles server (200.200.200.230)
        if is_mac:
            default_path = "/Volumes/Drawings/Customers"
        else:
            default_path = r"\\200.200.200.230\Drawings\Customers"
        base_path = user_settings.get('non_esi_drawing_path', default_path)
        customer = customer_name if customer_name else "Unknown"
        folder = os.path.join(base_path, customer, part_number)

    return folder


def list_drawing_files(folder_path):
    """List files in a drawing folder (PDFs and common image formats)"""
    files = []
    try:
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            for f in os.listdir(folder_path):
                # Filter to common drawing file types
                if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.dwg', '.dxf')):
                    files.append(f)
            files.sort()
    except Exception as e:
        print(f"Error listing files: {e}")
    return files


def display_pdf_in_modal(pdf_path):
    """Display a PDF file in the modal using base64 encoding"""
    try:
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Error loading PDF: {str(e)}")
        return False


def display_image_in_modal(image_path):
    """Display an image file in the modal"""
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_data = f.read()
            base64_img = base64.b64encode(image_data).decode('utf-8')
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.tif': 'image/tiff',
                '.tiff': 'image/tiff',
            }.get(ext, 'image/png')
            st.image(f"data:{mime_type};base64,{base64_img}", use_container_width=True)
            return True
        return False
    except Exception as e:
        st.error(f"Error loading image: {str(e)}")
        return False

# Page configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = None
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'
if 'filters' not in st.session_state:
    st.session_state.filters = {
        'unengineered': False,
        'in_work': False,
        'can_ship': False,
        'esi': 'All',
        'customer': 'All',
        'date_range': None,
        'remaining': 'All'  # All, Material Shortage, Can Ship
    }
if 'selected_job' not in st.session_state:
    st.session_state.selected_job = None
if 'show_drawing' not in st.session_state:
    st.session_state.show_drawing = None
if 'selected_drawing_file' not in st.session_state:
    st.session_state.selected_drawing_file = None


def load_data():
    """Load data and update session state"""
    with st.spinner('Loading data...'):
        st.session_state.data = load_all_data()
        st.session_state.last_refresh = datetime.now()


def get_status_color(status, theme='light'):
    """Get color for status badge"""
    if theme == 'light':
        return COLORS.get(status, '#D3D3D3')
    else:
        # For dark theme, use darker colors
        dark_colors = {
            'unengineered': '#1E5F8C',
            'in_work': '#2D5F2E',
            'can_ship': '#2D5F2E',
            'partial': '#8B7500',
            'not_started': '#4A4A4A',
        }
        return dark_colors.get(status, '#4A4A4A')


def apply_filters(df):
    """Apply active filters to the dataframe"""
    filtered_df = df.copy()

    # Unengineered filter
    if st.session_state.filters['unengineered']:
        filtered_df = filtered_df[filtered_df['Status'] == 'unengineered']

    # In-Work filter
    if st.session_state.filters['in_work']:
        filtered_df = filtered_df[filtered_df['Status'] == 'in_work']

    # Can Ship filter (currently disabled as we don't have inventory data)
    # if st.session_state.filters['can_ship']:
    #     filtered_df = filtered_df[filtered_df['Status'] == 'can_ship']

    # ESI filter
    if st.session_state.filters['esi'] == 'ESI Only':
        filtered_df = filtered_df[filtered_df['IsESI'] == True]
    elif st.session_state.filters['esi'] == 'Non-ESI Only':
        filtered_df = filtered_df[filtered_df['IsESI'] == False]

    # Customer filter
    if st.session_state.filters['customer'] != 'All':
        filtered_df = filtered_df[filtered_df['Name'] == st.session_state.filters['customer']]

    # Remaining column filter (by color/status)
    if st.session_state.filters.get('remaining') == 'Material Shortage':
        filtered_df = filtered_df[filtered_df['MaterialShort'] == True]
    elif st.session_state.filters.get('remaining') == 'Can Ship':
        filtered_df = filtered_df[filtered_df['CanShip'] == True]

    return filtered_df


def render_header():
    """Render the application header"""
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.title(f"{PAGE_ICON} {APP_TITLE}")

    with col2:
        if st.session_state.last_refresh:
            refresh_time = st.session_state.last_refresh.strftime("%I:%M %p")
            st.caption(f"Last updated: {refresh_time}")

    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            load_data()
            st.rerun()


def render_filter_bar(df):
    """Render the quick filter bar"""
    st.markdown("### Quick Filters")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        uneng_count = len(df[df['Status'] == 'unengineered'])
        if st.button(
            f"📘 Unengineered ({uneng_count})",
            type="primary" if st.session_state.filters['unengineered'] else "secondary",
            use_container_width=True
        ):
            st.session_state.filters['unengineered'] = not st.session_state.filters['unengineered']
            st.rerun()

    with col2:
        inwork_count = len(df[df['Status'] == 'in_work'])
        if st.button(
            f"🟢 In-Work ({inwork_count})",
            type="primary" if st.session_state.filters['in_work'] else "secondary",
            use_container_width=True
        ):
            st.session_state.filters['in_work'] = not st.session_state.filters['in_work']
            st.rerun()

    with col3:
        # Remaining column filter (by color)
        shortage_count = len(df[df['MaterialShort'] == True])
        canship_count = len(df[df['CanShip'] == True])
        remaining_options = [
            'All',
            f'Material Shortage ({shortage_count})',
            f'Can Ship ({canship_count})'
        ]
        # Map display names to filter values
        remaining_map = {
            'All': 'All',
            f'Material Shortage ({shortage_count})': 'Material Shortage',
            f'Can Ship ({canship_count})': 'Can Ship'
        }
        current_remaining = st.session_state.filters.get('remaining', 'All')
        # Find display option for current filter
        display_option = 'All'
        for opt, val in remaining_map.items():
            if val == current_remaining:
                display_option = opt
                break
        remaining_selection = st.selectbox(
            "Material Status",
            remaining_options,
            index=remaining_options.index(display_option) if display_option in remaining_options else 0,
            placeholder="Material Status"
        )
        new_remaining = remaining_map.get(remaining_selection, 'All')
        if new_remaining != current_remaining:
            st.session_state.filters['remaining'] = new_remaining
            st.rerun()

    with col4:
        esi_options = ['All', 'ESI Only', 'Non-ESI Only']
        current_esi = st.session_state.filters['esi']
        esi_selection = st.selectbox(
            "Sub Company",
            esi_options,
            index=esi_options.index(current_esi),
            placeholder="Sub Company"
        )
        if esi_selection != current_esi:
            st.session_state.filters['esi'] = esi_selection
            st.rerun()

    with col5:
        customers = ['All'] + sorted(df['Name'].dropna().unique().tolist())
        current_customer = st.session_state.filters['customer']
        if current_customer not in customers:
            current_customer = 'All'
        customer_selection = st.selectbox(
            "Customer",
            customers,
            index=customers.index(current_customer),
            placeholder="Customer"
        )
        if customer_selection != current_customer:
            st.session_state.filters['customer'] = customer_selection
            st.rerun()

    with col6:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.filters = {
                'unengineered': False,
                'in_work': False,
                'can_ship': False,
                'esi': 'All',
                'customer': 'All',
                'date_range': None,
                'remaining': 'All'
            }
            st.rerun()

    st.markdown("---")


def render_status_badge(status):
    """Render a colored status badge"""
    color = get_status_color(status, st.session_state.theme)
    status_name = STATUS_NAMES.get(status, status.title())
    return f'<span style="background-color: {color}; padding: 4px 12px; border-radius: 12px; color: #000; font-weight: 500; font-size: 0.85em;">{status_name}</span>'


def show_notes_dialog(job, part, description):
    """Show notes dialog for a job"""
    st.session_state.selected_job = job

    with st.dialog(f"Notes for Job {job}", width="large"):
        st.markdown(f"**Part:** {part}")
        st.markdown(f"**Description:** {description}")
        st.markdown("---")

        # Display existing notes
        notes = get_notes(job)
        if notes:
            st.markdown("### Existing Notes")
            for note in notes:
                note_id, job_num, text, created_at, created_by = note
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
                    <strong>{created_by}</strong> - <em>{created_at}</em><br>
                    {text}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No notes yet for this job.")

        st.markdown("---")

        # Add new note
        st.markdown("### Add New Note")
        new_note = st.text_area("Note", key=f"note_input_{job}", height=100)
        author = st.text_input("Your Name", value="User", key=f"author_{job}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Note", type="primary", use_container_width=True):
                if new_note.strip():
                    try:
                        add_note(job, new_note, author)
                        st.success("Note added successfully!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding note: {str(e)}")
                else:
                    st.warning("Please enter a note before saving.")

        with col2:
            if st.button("Close", use_container_width=True):
                st.session_state.selected_job = None
                st.rerun()


def show_job_detail_dialog(row_data):
    """Show job detail modal dialog"""
    job = row_data.get('Job', 'N/A')
    order_lr = row_data.get('OrderLineRel', 'N/A')

    @st.dialog(f"Job Details - {order_lr}", width="large")
    def job_detail_modal():
        # Header with status
        status = row_data.get('Status', 'unknown')
        status_color = get_status_color(status, st.session_state.theme)
        status_name = STATUS_NAMES.get(status, status.title())

        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3 style="margin: 0;">Job: {job}</h3>
            <span style="background-color: {status_color}; padding: 8px 16px; border-radius: 12px; font-weight: 600;">{status_name}</span>
        </div>
        """, unsafe_allow_html=True)

        # Job Information
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Order Information")
            st.markdown(f"**Order-Line-Rel:** {order_lr}")
            part_num = row_data.get('Part', 'N/A')
            st.markdown(f"**Part:** {part_num}")
            # View Drawing button
            if part_num and part_num != 'N/A':
                if st.button("📄 View Drawing", key=f"view_drawing_{order_lr}", use_container_width=True):
                    st.session_state.show_drawing = part_num
            st.markdown(f"**Description:** {row_data.get('Description', 'N/A')}")
            st.markdown(f"**Customer:** {row_data.get('Name', 'N/A')}")

        with col2:
            st.markdown("#### Quantities & Dates")
            st.markdown(f"**Order Qty:** {row_data.get('Order Qty', 0)}")
            st.markdown(f"**Completed:** {row_data.get('Qty Completed', 0)}")
            st.markdown(f"**Remaining:** {row_data.get('Rem Qty', 0)}")
            st.markdown(f"**Ship By:** {row_data.get('Ship By_Display', 'N/A')}")
            st.markdown(f"**Need By:** {row_data.get('Need By_Display', 'N/A')}")

        # Drawing Display Section
        if st.session_state.get('show_drawing'):
            drawing_part = st.session_state.show_drawing
            is_esi = row_data.get('IsESI', False)
            customer = row_data.get('Name', 'Unknown')

            st.markdown("---")
            st.markdown(f"#### 📄 Drawings: {drawing_part}")

            # Get folder path
            folder_path = get_drawing_folder(drawing_part, customer, is_esi)

            col_draw1, col_draw2 = st.columns([4, 1])
            with col_draw2:
                if st.button("✕ Close", key="close_drawing"):
                    st.session_state.show_drawing = None
                    st.session_state.selected_drawing_file = None
                    st.rerun()

            with col_draw1:
                st.caption(f"Folder: {folder_path}")

            # List files in folder
            files = list_drawing_files(folder_path)

            if files:
                # File selector
                selected_file = st.selectbox(
                    "Select a drawing file:",
                    options=files,
                    key=f"drawing_file_select_{drawing_part}"
                )

                if selected_file:
                    file_path = os.path.join(folder_path, selected_file)
                    st.caption(f"File: {selected_file}")

                    # Display based on file type
                    if selected_file.lower().endswith('.pdf'):
                        if not display_pdf_in_modal(file_path):
                            st.warning("Could not display PDF in browser.")
                            st.info(f"Full path: {file_path}")
                    elif selected_file.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff')):
                        if not display_image_in_modal(file_path):
                            st.warning("Could not display image.")
                    else:
                        st.info(f"File type not supported for preview: {selected_file}")
                        st.code(file_path)
            else:
                st.warning(f"No drawing files found in folder.")
                st.info(f"Checked path: {folder_path}")
                st.caption("Supported formats: PDF, PNG, JPG, TIF")

        st.markdown("---")

        # Status Details
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("#### Status Details")
            eng = row_data.get('Engineered', False)
            rel = row_data.get('Released', False)
            st.markdown(f"**Engineered:** {'✅ Yes' if eng == True else '❌ No'}")
            st.markdown(f"**Released:** {'✅ Yes' if rel == True else '❌ No'}")
            labor_type = row_data.get('Labor Type', '')
            if labor_type:
                st.markdown(f"**Labor Type:** {labor_type}")

        with col4:
            st.markdown("#### Labor History")
            last_labor = row_data.get('LastLaborDate_Display', '')
            total_hours = row_data.get('TotalLaborHours', 0)
            st.markdown(f"**Last Labor Date:** {last_labor if last_labor else 'None'}")
            if total_hours:
                st.markdown(f"**Total Labor Hours:** {total_hours:.2f}")

        st.markdown("---")

        # Operations Section
        if job != 'No Job':
            st.markdown("#### Operations")
            operations_df = get_job_operations(job)
            if not operations_df.empty:
                # Rename columns for display
                display_ops = operations_df.copy()
                col_rename = {
                    'Opr': 'Op #',
                    'Operation Description': 'Description',
                    'Qty Completed': 'Completed',
                    'Run Qty': 'Run Qty',
                    'Est. Prod Hours': 'Est Hrs',
                    'Est. Setup Hours': 'Setup Hrs',
                    'Labor Type': 'Type',
                    'Labor Hrs': 'Labor Hrs'
                }
                display_ops = display_ops.rename(columns={k: v for k, v in col_rename.items() if k in display_ops.columns})

                st.dataframe(
                    display_ops,
                    use_container_width=True,
                    hide_index=True,
                    height=min(200, 35 * (len(display_ops) + 1))
                )
            else:
                st.info("No operations found for this job.")

            st.markdown("---")

        # Material Shortage Section
        if row_data.get('MaterialShort', False) and job != 'No Job':
            st.markdown("#### ⚠️ Material Shortage")
            shortage_details = get_material_shortage_details(job)
            if shortage_details:
                import pandas as pd
                shortage_df = pd.DataFrame(shortage_details)
                # Style the dataframe with red header
                st.markdown("""
                <style>
                .shortage-table { background-color: #FFE4E4; }
                </style>
                """, unsafe_allow_html=True)
                st.dataframe(
                    shortage_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Part": st.column_config.TextColumn("Part #"),
                        "Description": st.column_config.TextColumn("Description"),
                        "Required": st.column_config.NumberColumn("Required", format="%.1f"),
                        "Issued": st.column_config.NumberColumn("Issued", format="%.1f"),
                        "Short": st.column_config.NumberColumn("Short", format="%.1f"),
                    }
                )
            else:
                st.warning("Material shortage flagged but no details available.")
            st.markdown("---")

        # MB Comments Section (Purchasing and Operations comments from spreadsheet)
        purch_comments = row_data.get('PurchasingComments', '')
        ops_comments = row_data.get('OperationsComments', '')
        if purch_comments or ops_comments:
            st.markdown("#### 📝 Spreadsheet Comments")
            if purch_comments:
                st.markdown(f"""
                <div style="background-color: #E3F2FD; padding: 10px; margin-bottom: 10px; border-radius: 5px; border-left: 4px solid #2196F3;">
                    <strong>Purchasing Comments:</strong><br>
                    {purch_comments}
                </div>
                """, unsafe_allow_html=True)
            if ops_comments:
                st.markdown(f"""
                <div style="background-color: #FFF3E0; padding: 10px; margin-bottom: 10px; border-radius: 5px; border-left: 4px solid #FF9800;">
                    <strong>Operations Comments:</strong><br>
                    {ops_comments}
                </div>
                """, unsafe_allow_html=True)
            st.markdown("---")

        # Notes Section
        st.markdown("#### Notes")
        notes = get_notes(job) if job != 'No Job' else []
        if notes:
            for note in notes:
                note_id, job_num, text, created_at, created_by = note
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
                    <strong>{created_by}</strong> - <em>{created_at}</em><br>
                    {text}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No notes for this job.")

        # Add note form
        with st.expander("Add New Note"):
            new_note = st.text_area("Note", key=f"detail_note_{job}_{order_lr}", height=80)
            author = st.text_input("Your Name", value="User", key=f"detail_author_{job}_{order_lr}")
            if st.button("Save Note", type="primary", key=f"save_note_{job}_{order_lr}"):
                if new_note.strip() and job != 'No Job':
                    try:
                        add_note(job, new_note, author)
                        st.success("Note added!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    job_detail_modal()


def render_orders_table(df):
    """Render the main orders data table with clickable rows"""
    if df.empty:
        st.warning("No orders match the current filters.")
        return

    st.markdown(f"### Orders ({len(df)} jobs)")
    st.caption("Click on a row to view job details")

    # Format the dataframe for display
    display_df = df[[
        'Job', 'OrderLineRel', 'Part', 'Description', 'Status',
        'Order Qty', 'Rem Qty', 'MaterialShort', 'CanShip',
        'Ship By_Display', 'Need By_Display',
        'Name', 'LastLaborDate_Display', 'HasComments'
    ]].copy()

    # Add notes indicator column
    display_df['Notes'] = display_df['HasComments'].apply(lambda x: '📝' if x else '')

    display_df.columns = [
        'Job', 'Order-L-R', 'Part', 'Description', 'Status',
        'Order Qty', 'Remaining', 'MaterialShort', 'CanShip',
        'Ship By', 'Need By',
        'Customer', 'Last Labor', 'HasComments', 'Notes'
    ]

    # Apply color coding based on status and material shortage/can ship
    current_theme = st.session_state.theme

    def color_job_columns(row):
        """Apply text color to Job and Order-L-R based on status, and Remaining based on inventory"""
        status = row['Status']

        # Colors for light theme
        if current_theme == 'light':
            status_text_colors = {
                'unengineered': '#0066CC',  # Blue
                'in_work': '#228B22',       # Forest green
                'not_started': '#333333',   # Dark gray
                'no_job': '#CC6600',        # Orange
            }
            red_color = '#CC0000'    # Dark red
            green_color = '#228B22'  # Forest green
            default_color = '#333333'
            base_text_color = '#333333'
        else:
            # Colors for dark theme - lighter/brighter for visibility
            status_text_colors = {
                'unengineered': '#64B5F6',  # Light blue
                'in_work': '#81C784',       # Light green
                'not_started': '#E0E0E0',   # Light gray
                'no_job': '#FFB74D',        # Light orange
            }
            red_color = '#EF5350'    # Light red
            green_color = '#81C784'  # Light green
            default_color = '#E0E0E0'
            base_text_color = '#E0E0E0'  # Light text for dark background

        color = status_text_colors.get(status, default_color)

        # In dark mode, apply base text color to ALL cells for visibility
        if current_theme == 'dark':
            styles = [f'color: {base_text_color}'] * len(row)
        else:
            styles = [''] * len(row)

        job_idx = list(row.index).index('Job')
        olr_idx = list(row.index).index('Order-L-R')
        rem_idx = list(row.index).index('Remaining')
        styles[job_idx] = f'color: {color}; font-weight: bold'
        styles[olr_idx] = f'color: {color}; font-weight: bold'
        # Red text for Remaining if material shortage (takes precedence)
        if row.get('MaterialShort', False):
            styles[rem_idx] = f'color: {red_color}; font-weight: bold'
        # Green text for Remaining if can ship from inventory
        elif row.get('CanShip', False):
            styles[rem_idx] = f'color: {green_color}; font-weight: bold'
        return styles

    # Style the dataframe
    if current_theme == 'dark':
        # For dark mode, set background and default text color for entire dataframe
        styled_df = display_df.style\
            .set_properties(**{'background-color': '#2D2D2D', 'color': '#E0E0E0'})\
            .apply(color_job_columns, axis=1)
    else:
        styled_df = display_df.style.apply(color_job_columns, axis=1)

    # Display the table with row selection enabled
    # Key includes theme so selection clears when theme changes
    selection = st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        height=550,
        on_select="rerun",
        selection_mode="single-row",
        key=f"orders_table_{current_theme}",
        column_config={
            "Status": st.column_config.TextColumn("Status"),
            "Order Qty": st.column_config.NumberColumn("Order Qty", format="%d"),
            "Remaining": st.column_config.NumberColumn("Remaining", format="%d"),
            "MaterialShort": None,  # Hide this column
            "CanShip": None,  # Hide this column
            "HasComments": None,  # Hide this column
            "Notes": st.column_config.TextColumn("Notes", width="small"),
        }
    )

    # Handle row selection - show job detail modal
    if selection and selection.selection and selection.selection.rows:
        selected_idx = selection.selection.rows[0]
        selected_row = df.iloc[selected_idx].to_dict()
        show_job_detail_dialog(selected_row)


def render_color_legend():
    """Render a color legend at the bottom of the page"""
    st.markdown("---")
    st.markdown("#### Color Legend")

    # Use theme-appropriate colors
    if st.session_state.theme == 'light':
        in_work_color = '#228B22'
        uneng_color = '#0066CC'
        not_started_color = '#333333'
        no_job_color = '#CC6600'
        shortage_color = '#CC0000'
        can_ship_color = '#228B22'
    else:
        in_work_color = '#81C784'
        uneng_color = '#64B5F6'
        not_started_color = '#BDBDBD'
        no_job_color = '#FFB74D'
        shortage_color = '#EF5350'
        can_ship_color = '#81C784'

    legend_html = f"""
    <div style="display: flex; flex-wrap: wrap; gap: 20px; padding: 10px 0;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: {in_work_color}; font-weight: bold; font-size: 1.2em;">Job Text</span>
            <span>= In Work</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: {uneng_color}; font-weight: bold; font-size: 1.2em;">Job Text</span>
            <span>= Unengineered</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: {not_started_color}; font-weight: bold; font-size: 1.2em;">Job Text</span>
            <span>= Not Started</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: {no_job_color}; font-weight: bold; font-size: 1.2em;">Job Text</span>
            <span>= No Job</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: {shortage_color}; font-weight: bold; font-size: 1.2em;">Remaining</span>
            <span>= Material Shortage</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: {can_ship_color}; font-weight: bold; font-size: 1.2em;">Remaining</span>
            <span>= Can Ship from Inventory</span>
        </div>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)


def apply_theme_css():
    """Apply custom CSS based on selected theme"""
    if st.session_state.theme == 'dark':
        st.markdown("""
        <style>
        /* Dark theme overrides */
        .stApp {
            background-color: #1E1E1E;
            color: #E0E0E0;
        }

        /* Main content area */
        .main .block-container {
            background-color: #1E1E1E;
        }

        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #E0E0E0 !important;
        }

        /* Regular text and labels */
        p, span, label, .stMarkdown {
            color: #E0E0E0 !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #252526;
        }
        [data-testid="stSidebar"] * {
            color: #E0E0E0 !important;
        }

        /* Text inputs */
        .stTextInput input, .stTextArea textarea {
            background-color: #2D2D2D !important;
            color: #E0E0E0 !important;
            border-color: #404040 !important;
        }

        /* Select boxes */
        .stSelectbox > div > div {
            background-color: #2D2D2D !important;
            color: #E0E0E0 !important;
        }

        /* Buttons */
        .stButton > button {
            background-color: #404040;
            color: #E0E0E0;
            border-color: #505050;
        }
        .stButton > button:hover {
            background-color: #505050;
            border-color: #606060;
        }

        /* Primary buttons */
        .stButton > button[kind="primary"] {
            background-color: #0066CC;
            color: white;
        }

        /* Dataframe - comprehensive styling */
        .stDataFrame, [data-testid="stDataFrame"] {
            background-color: #2D2D2D !important;
        }

        /* Target the actual table elements inside the dataframe */
        [data-testid="stDataFrame"] table {
            background-color: #2D2D2D !important;
        }
        [data-testid="stDataFrame"] thead tr th {
            background-color: #383838 !important;
            color: #E0E0E0 !important;
        }
        [data-testid="stDataFrame"] tbody tr td {
            background-color: #2D2D2D !important;
            color: #E0E0E0 !important;
        }
        [data-testid="stDataFrame"] tbody tr:hover td {
            background-color: #404040 !important;
        }

        /* Glide data grid (used by newer Streamlit versions) */
        [data-testid="stDataFrame"] .dvn-scroller {
            background-color: #2D2D2D !important;
        }
        [data-testid="stDataFrame"] .dvn-underlay {
            background-color: #2D2D2D !important;
        }
        [data-testid="stDataFrame"] [class*="cell"] {
            background-color: #2D2D2D !important;
            color: #E0E0E0 !important;
        }
        [data-testid="stDataFrame"] [class*="header"] {
            background-color: #383838 !important;
            color: #E0E0E0 !important;
        }

        /* Data editor cells */
        .gdg-cell {
            background-color: #2D2D2D !important;
            color: #E0E0E0 !important;
        }
        .gdg-header-cell {
            background-color: #383838 !important;
            color: #E0E0E0 !important;
        }

        /* Canvas-based grid text */
        [data-testid="stDataFrame"] canvas {
            filter: none !important;
        }

        /* Metrics */
        [data-testid="stMetricValue"] {
            color: #E0E0E0 !important;
        }
        [data-testid="stMetricLabel"] {
            color: #B0B0B0 !important;
        }

        /* Expander */
        .streamlit-expanderHeader {
            background-color: #2D2D2D !important;
            color: #E0E0E0 !important;
        }
        .streamlit-expanderContent {
            background-color: #252526 !important;
        }

        /* Dialogs/Modals */
        [data-testid="stModal"] > div {
            background-color: #2D2D2D !important;
        }

        /* Captions */
        .stCaption {
            color: #A0A0A0 !important;
        }

        /* Success, Warning, Error, Info boxes */
        .stSuccess, .stWarning, .stError, .stInfo {
            color: #1E1E1E !important;
        }

        /* Radio buttons */
        .stRadio label {
            color: #E0E0E0 !important;
        }

        /* Dividers */
        hr {
            border-color: #404040 !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Light theme - reset to defaults (minimal CSS)
        st.markdown("""
        <style>
        /* Light theme - use Streamlit defaults */
        .stApp {
            background-color: #FFFFFF;
            color: #262730;
        }
        </style>
        """, unsafe_allow_html=True)


def main():
    """Main application function"""
    # Apply theme CSS first
    apply_theme_css()

    # Initialize database
    try:
        init_database()
    except Exception as e:
        st.warning("Database initialization skipped (expected in mounted folder).")

    # Load data if not loaded
    if st.session_state.data is None:
        load_data()

    # Render header
    render_header()

    # Get data
    df = st.session_state.data

    if df is None or df.empty:
        st.error("No data available. Please check data file paths in config/settings.py")
        return

    # Render filter bar
    render_filter_bar(df)

    # Apply filters
    filtered_df = apply_filters(df)

    # Render orders table
    render_orders_table(filtered_df)

    # Render color legend at bottom
    render_color_legend()

    # Sidebar for additional functions
    with st.sidebar:
        st.markdown("## Actions")

        # Job search for notes
        st.markdown("### Add Note to Job")
        job_search = st.text_input("Enter Job Number")
        if job_search and st.button("Open Notes"):
            # Find the job in the dataframe
            job_data = df[df['Job'] == job_search]
            if not job_data.empty:
                show_notes_dialog(
                    job_search,
                    job_data.iloc[0]['Part'],
                    job_data.iloc[0]['Description']
                )
            else:
                st.error(f"Job {job_search} not found.")

        st.markdown("---")

        # Theme toggle - using buttons for immediate feedback
        st.markdown("### Theme")
        col_light, col_dark = st.columns(2)
        with col_light:
            if st.button(
                "☀️ Light",
                type="primary" if st.session_state.theme == 'light' else "secondary",
                use_container_width=True
            ):
                if st.session_state.theme != 'light':
                    st.session_state.theme = 'light'
                    st.rerun()
        with col_dark:
            if st.button(
                "🌙 Dark",
                type="primary" if st.session_state.theme == 'dark' else "secondary",
                use_container_width=True
            ):
                if st.session_state.theme != 'dark':
                    st.session_state.theme = 'dark'
                    st.rerun()

        st.markdown("---")

        # Statistics
        st.markdown("### Statistics")
        st.metric("Total Jobs", len(df))
        st.metric("Unengineered", len(df[df['Status'] == 'unengineered']))
        st.metric("In Work", len(df[df['Status'] == 'in_work']))
        st.metric("Not Started", len(df[df['Status'] == 'not_started']))


if __name__ == "__main__":
    main()
