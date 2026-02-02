"""
Visual Scheduling Board - Work Center view showing jobs on machines
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.settings import APP_TITLE, PAGE_ICON, COLORS, STATUS_NAMES
from app.utils.data_loader import get_data_path

# Page configuration
st.set_page_config(
    page_title=f"Scheduling - {APP_TITLE}",
    page_icon=PAGE_ICON,
    layout="wide"
)

# Initialize session state
if 'scheduling_filters' not in st.session_state:
    st.session_state.scheduling_filters = {
        'work_centers': [],
        'date_range': 'next_2_weeks',
        'show_completed': False,
    }


def load_operations_data():
    """
    Load operations from Shop Orders for work center scheduling view.
    Each row represents one unique operation on a work center.
    Deduplicates by Job + Operation number, aggregating labor data.
    """
    try:
        df = pd.read_csv(get_data_path("shop_orders"))

        # Parse dates
        for col in ['Due Date', 'Ship By', 'Need By', 'Req. By']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Convert numeric columns
        df['Est. Prod Hours'] = pd.to_numeric(df['Est. Prod Hours'], errors='coerce').fillna(0)
        df['Est. Setup Hours'] = pd.to_numeric(df['Est. Setup Hours'], errors='coerce').fillna(0)
        df['Qty Completed'] = pd.to_numeric(df['Qty Completed'], errors='coerce').fillna(0)
        df['Run Qty'] = pd.to_numeric(df['Run Qty'], errors='coerce').fillna(0)
        df['Labor Hrs'] = pd.to_numeric(df['Labor Hrs'], errors='coerce').fillna(0)

        # Work Center is the Operation Description - filter out invalid ones
        df['Work Center'] = df['Operation Description'].fillna('')

        # Filter to only valid work centers (not empty, not numbers, not long comments)
        valid_work_centers = [
            'Horizontal Mill', 'Vertical Mill', 'Mill-Turn', 'Assembly',
            'INSPECTION', 'Final Inspection', 'Packing', 'Programming',
            'Saw Cutting', 'Subcontract Plating', 'Clean', 'Inspection',
            'Grinding', 'Deburr', 'Shipping', 'Lathe', 'EDM', 'Welding',
            'Heat Treat', 'Anodize', 'Paint', 'Laser', 'Waterjet'
        ]

        # Keep rows where Work Center is in valid list OR looks like a real work center
        # (starts with capital letter, reasonable length, not a number)
        def is_valid_work_center(wc):
            if not wc or len(wc) < 3 or len(wc) > 30:
                return False
            # Check if it's just a number
            try:
                float(wc)
                return False
            except ValueError:
                pass
            # Check if it starts with a letter
            if not wc[0].isalpha():
                return False
            return True

        df = df[df['Work Center'].apply(is_valid_work_center)]

        # Check if any labor entry has 'P' (production) type - means in work
        df['HasProduction'] = df['Labor Type'] == 'P'

        # Deduplicate: one row per Job + Operation
        # Aggregate: take max Qty Completed, sum Labor Hrs, check if any has Production labor
        agg_df = df.groupby(['Job', 'Opr']).agg({
            'Order': 'first',
            'Line': 'first',
            'Release': 'first',
            'Part': 'first',
            'Description': 'first',
            'Engineered': 'first',
            'Released': 'first',
            'Run Qty': 'first',
            'Qty Completed': 'max',  # Take the max completed qty
            'Work Center': 'first',
            'Operation Description': 'first',
            'Est. Prod Hours': 'first',
            'Est. Setup Hours': 'first',
            'Due Date': 'first',
            'Ship By': 'first',
            'Need By': 'first',
            'Req. By': 'first',
            'Labor Hrs': 'sum',  # Sum all labor hours
            'HasProduction': 'any',  # True if any row has production labor
        }).reset_index()

        df = agg_df

        # Calculate total hours per operation
        df['Total Hours'] = df['Est. Prod Hours'] + df['Est. Setup Hours']

        # Calculate progress
        df['Progress'] = (df['Qty Completed'] / df['Run Qty'] * 100).fillna(0).clip(0, 100)

        # Determine operation status
        def get_op_status(row):
            if row['Qty Completed'] >= row['Run Qty'] and row['Run Qty'] > 0:
                return 'completed'
            elif row['HasProduction']:
                return 'in_work'
            elif row['Engineered'] == False:
                return 'unengineered'
            else:
                return 'not_started'

        df['Status'] = df.apply(get_op_status, axis=1)

        # Check if past due
        today = pd.Timestamp.now().normalize()
        df['IsPastDue'] = df['Ship By'] < today

        # Create a display label for each operation
        df['Label'] = df['Job'] + ' - Op ' + df['Opr'].astype(str)

        return df

    except Exception as e:
        print(f"Error loading operations data: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def get_work_centers(df):
    """Get unique work centers from data"""
    if df.empty:
        return []
    return sorted(df['Work Center'].dropna().unique().tolist())


def render_header():
    """Render page header"""
    st.title("📅 Work Center Scheduling Board")
    st.caption("Visual schedule showing operations on each work center/machine")


def render_controls(df):
    """Render control panel"""
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        work_centers = get_work_centers(df)
        # Default to all work centers if none selected
        default_wcs = st.session_state.scheduling_filters['work_centers'] or work_centers
        selected_wcs = st.multiselect(
            "Filter Work Centers",
            options=work_centers,
            default=default_wcs,
            help="Select which work centers to display"
        )
        st.session_state.scheduling_filters['work_centers'] = selected_wcs

    with col2:
        date_range = st.selectbox(
            "Date Range",
            options=['this_week', 'next_2_weeks', 'this_month', 'next_3_months', 'all'],
            format_func=lambda x: {
                'this_week': 'This Week',
                'next_2_weeks': 'Next 2 Weeks',
                'this_month': 'This Month',
                'next_3_months': 'Next 3 Months',
                'all': 'All Operations'
            }[x],
            index=['this_week', 'next_2_weeks', 'this_month', 'next_3_months', 'all'].index(
                st.session_state.scheduling_filters['date_range']
            )
        )
        st.session_state.scheduling_filters['date_range'] = date_range

    with col3:
        show_completed = st.checkbox(
            "Show Completed",
            value=st.session_state.scheduling_filters['show_completed']
        )
        st.session_state.scheduling_filters['show_completed'] = show_completed

    st.markdown("---")


def filter_by_date_range(df, date_range):
    """Filter dataframe by date range based on Ship By"""
    today = pd.Timestamp.now().normalize()

    if date_range == 'this_week':
        end_date = today + timedelta(days=(6 - today.weekday()))
        return df[(df['Ship By'] >= today - timedelta(days=7)) & (df['Ship By'] <= end_date)]
    elif date_range == 'next_2_weeks':
        end_date = today + timedelta(days=14)
        return df[(df['Ship By'] >= today - timedelta(days=7)) & (df['Ship By'] <= end_date)]
    elif date_range == 'this_month':
        end_date = (today + pd.offsets.MonthEnd(0))
        return df[(df['Ship By'] >= today - timedelta(days=7)) & (df['Ship By'] <= end_date)]
    elif date_range == 'next_3_months':
        end_date = today + timedelta(days=90)
        return df[(df['Ship By'] >= today - timedelta(days=7)) & (df['Ship By'] <= end_date)]
    else:
        return df


def apply_filters(df):
    """Apply all filters to dataframe"""
    filtered = df.copy()

    # Work center filter
    if st.session_state.scheduling_filters['work_centers']:
        filtered = filtered[filtered['Work Center'].isin(
            st.session_state.scheduling_filters['work_centers']
        )]

    # Date range filter
    filtered = filter_by_date_range(filtered, st.session_state.scheduling_filters['date_range'])

    # Completed filter
    if not st.session_state.scheduling_filters['show_completed']:
        filtered = filtered[filtered['Status'] != 'completed']

    return filtered


def create_gantt_chart(df):
    """Create Plotly Gantt chart for work center view"""
    if df.empty:
        return None

    # Prepare data for Gantt
    gantt_df = df.copy()

    # Use Ship By as the end date, calculate start based on hours
    # For simplicity, use Ship By - estimated hours as start
    gantt_df['End'] = gantt_df['Ship By']
    gantt_df['Start'] = gantt_df['End'] - pd.to_timedelta(gantt_df['Total Hours'], unit='h')

    # Fill missing dates
    today = pd.Timestamp.now().normalize()
    gantt_df['End'] = gantt_df['End'].fillna(today + timedelta(days=7))
    gantt_df['Start'] = gantt_df['Start'].fillna(today)

    # Ensure Start is before End
    gantt_df.loc[gantt_df['Start'] >= gantt_df['End'], 'Start'] = \
        gantt_df.loc[gantt_df['Start'] >= gantt_df['End'], 'End'] - timedelta(hours=1)

    # Color mapping
    color_map = {
        'in_work': COLORS['in_work'],
        'unengineered': COLORS['unengineered'],
        'not_started': '#E0E0E0',
        'completed': '#4CAF50',
    }

    # Create the timeline chart
    fig = px.timeline(
        gantt_df,
        x_start='Start',
        x_end='End',
        y='Work Center',
        color='Status',
        hover_data={
            'Job': True,
            'Part': True,
            'Opr': True,
            'Operation Description': True,
            'Total Hours': ':.1f',
            'Progress': ':.0f',
            'Status': True,
            'Start': False,
            'End': False,
            'Work Center': False,
        },
        color_discrete_map=color_map,
        labels={
            'Total Hours': 'Est. Hours',
            'Progress': 'Progress %',
            'Opr': 'Op #'
        }
    )

    # Add today line
    today = datetime.now()
    fig.add_shape(
        type="line",
        x0=today,
        x1=today,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="red", width=2, dash="dash"),
    )
    fig.add_annotation(
        x=today,
        y=1.02,
        yref="paper",
        text="Today",
        showarrow=False,
        font=dict(color="red", size=12),
    )

    # Update layout
    num_work_centers = len(gantt_df['Work Center'].unique())
    fig.update_layout(
        height=max(400, num_work_centers * 50),
        xaxis_title="Date",
        yaxis_title="Work Center",
        showlegend=True,
        legend_title="Status",
        xaxis=dict(
            type='date',
            tickformat='%m/%d',
        ),
        yaxis=dict(
            categoryorder='category ascending'
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
        )
    )

    return fig


def render_gantt_chart(df):
    """Render the Gantt chart section"""
    st.markdown("### Work Center Schedule")

    if df.empty:
        st.info("No operations match the current filters.")
        return

    fig = create_gantt_chart(df)

    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Unable to create Gantt chart with current data.")


def render_work_center_summary(df):
    """Render work center load summary"""
    st.markdown("### Work Center Load")

    if df.empty:
        return

    # Aggregate by work center
    summary = df.groupby('Work Center').agg({
        'Job': 'nunique',
        'Opr': 'count',
        'Total Hours': 'sum',
        'Status': lambda x: (x == 'in_work').sum()
    }).reset_index()

    summary.columns = ['Work Center', 'Jobs', 'Operations', 'Total Hours', 'In Work']
    summary = summary.sort_values('Total Hours', ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Total Hours": st.column_config.NumberColumn(format="%.1f hrs"),
            }
        )

    with col2:
        # Bar chart of hours by work center
        fig = px.bar(
            summary.head(10),
            x='Total Hours',
            y='Work Center',
            orientation='h',
            color='In Work',
            color_continuous_scale=['lightgray', 'green'],
            labels={'Total Hours': 'Hours', 'In Work': 'Active'}
        )
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def render_operations_list(df):
    """Render expandable operations list"""
    with st.expander("📋 Operations List", expanded=False):
        if df.empty:
            st.info("No operations to display.")
            return

        # Prepare display columns
        display_cols = ['Job', 'Part', 'Work Center', 'Opr', 'Status',
                        'Total Hours', 'Progress', 'Ship By']
        display_cols = [c for c in display_cols if c in df.columns]

        display_df = df[display_cols].copy()

        # Format Ship By for display
        if 'Ship By' in display_df.columns:
            display_df['Ship By'] = pd.to_datetime(display_df['Ship By']).dt.strftime('%m/%d/%Y')

        # Rename columns
        display_df = display_df.rename(columns={
            'Opr': 'Op #',
            'Total Hours': 'Est. Hours'
        })

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Progress": st.column_config.ProgressColumn(
                    "Progress",
                    min_value=0,
                    max_value=100,
                    format="%.0f%%"
                ),
                "Est. Hours": st.column_config.NumberColumn(format="%.1f"),
            }
        )


def render_summary_metrics(df):
    """Render summary metrics"""
    if df.empty:
        return

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Operations", len(df))

    with col2:
        st.metric("Unique Jobs", df['Job'].nunique())

    with col3:
        st.metric("Work Centers", df['Work Center'].nunique())

    with col4:
        total_hours = df['Total Hours'].sum()
        st.metric("Total Hours", f"{total_hours:,.1f}")

    with col5:
        in_work = (df['Status'] == 'in_work').sum()
        st.metric("In Work", in_work)

    st.markdown("---")


def render_color_legend():
    """Render color legend"""
    st.markdown("---")
    st.markdown("#### Color Legend")
    legend_html = f"""
    <div style="display: flex; flex-wrap: wrap; gap: 20px; padding: 10px 0;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="background-color: {COLORS['in_work']}; padding: 4px 12px; border-radius: 4px;">■</span>
            <span>In Work</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="background-color: {COLORS['unengineered']}; padding: 4px 12px; border-radius: 4px;">■</span>
            <span>Unengineered</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="background-color: #E0E0E0; padding: 4px 12px; border-radius: 4px;">■</span>
            <span>Not Started</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="background-color: #4CAF50; padding: 4px 12px; border-radius: 4px;">■</span>
            <span>Completed</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: red; font-weight: bold;">|</span>
            <span>Today</span>
        </div>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)


def main():
    """Main application function"""
    render_header()

    # Load data
    with st.spinner("Loading operations data..."):
        df = load_operations_data()

    if df.empty:
        st.error("Failed to load operations data. Please check data file paths.")
        return

    # Render controls
    render_controls(df)

    # Apply filters
    filtered_df = apply_filters(df)

    # Render main content
    render_summary_metrics(filtered_df)
    render_gantt_chart(filtered_df)
    render_work_center_summary(filtered_df)
    render_operations_list(filtered_df)
    render_color_legend()


if __name__ == "__main__":
    main()
