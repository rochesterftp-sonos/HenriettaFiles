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

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import (
    APP_TITLE, PAGE_ICON, COLORS, STATUS_NAMES,
    REFRESH_INTERVAL, DRAWING_URL_PATTERN, PO_URL_PATTERN
)
from app.utils.data_loader import load_all_data
from app.utils.database import init_database, add_note, get_notes, get_notes_count

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
        'date_range': None
    }
if 'selected_job' not in st.session_state:
    st.session_state.selected_job = None


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

    # with col3:
    #     canship_count = len(df[df['Status'] == 'can_ship'])
    #     if st.button(
    #         f"📦 Can Ship ({canship_count})",
    #         type="primary" if st.session_state.filters['can_ship'] else "secondary",
    #         use_container_width=True
    #     ):
    #         st.session_state.filters['can_ship'] = not st.session_state.filters['can_ship']
    #         st.rerun()

    with col4:
        esi_options = ['All', 'ESI Only', 'Non-ESI Only']
        current_esi = st.session_state.filters['esi']
        esi_selection = st.selectbox(
            "ESI Filter",
            esi_options,
            index=esi_options.index(current_esi),
            label_visibility="collapsed"
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
            "Customer Filter",
            customers,
            index=customers.index(current_customer),
            label_visibility="collapsed"
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
                'date_range': None
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


def render_orders_table(df):
    """Render the main orders data table"""
    if df.empty:
        st.warning("No orders match the current filters.")
        return

    st.markdown(f"### Orders ({len(df)} jobs)")

    # Format the dataframe for display
    display_df = df[[
        'Job', 'Part', 'Description', 'Status',
        'Selling Requested Qty', 'Qty Completed',
        'Due Date_Display', 'Need By_Display',
        'Name', 'LastLaborDate_Display'
    ]].copy()

    display_df.columns = [
        'Job', 'Part', 'Description', 'Status',
        'Order Qty', 'Completed',
        'Due Date', 'Need By',
        'Customer', 'Last Labor'
    ]

    # Add clickable indicators
    display_df['📋'] = '📋'  # Notes indicator
    display_df['📄'] = '📄'  # Drawing indicator

    # Reorder columns
    display_df = display_df[[
        '📋', 'Job', 'Part', 'Description', 'Status',
        'Order Qty', 'Completed', 'Due Date', 'Need By',
        'Customer', 'Last Labor', '📄'
    ]]

    # Display the table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Status": st.column_config.TextColumn("Status"),
            "📋": st.column_config.TextColumn("Notes", width="small"),
            "📄": st.column_config.TextColumn("Doc", width="small"),
        }
    )

    # Note: In a full implementation, we'd make rows clickable to show notes dialog
    # For now, users can use the sidebar to add notes


def main():
    """Main application function"""
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

        # Theme toggle
        st.markdown("### Theme")
        theme_option = st.radio("Color Scheme", ["Light", "Dark"], index=0 if st.session_state.theme == 'light' else 1)
        new_theme = 'light' if theme_option == 'Light' else 'dark'
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme
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
