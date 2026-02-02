"""
Purchasing Dashboard - Open PO tracking and supplier performance
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.settings import APP_TITLE, PAGE_ICON, COLORS
from app.utils.data_loader import (
    load_open_pos,
    get_supplier_metrics,
    get_po_job_linkage,
    load_shop_orders
)

# Page configuration
st.set_page_config(
    page_title=f"Purchasing - {APP_TITLE}",
    page_icon=PAGE_ICON,
    layout="wide"
)

# Initialize session state
if 'purchasing_filters' not in st.session_state:
    st.session_state.purchasing_filters = {
        'supplier': 'All',
        'overdue_only': False,
    }


def render_header(df):
    """Render header with summary metrics"""
    st.title("📦 Purchasing Dashboard")

    if df.empty:
        st.warning("No purchasing data available.")
        return

    # Calculate metrics
    total_pos = df['PO'].nunique()
    total_lines = len(df)
    overdue_lines = df['IsOverdue'].sum()
    unique_suppliers = df['Name'].nunique()
    total_qty = df['Supplier Qty'].sum()

    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Open POs", total_pos)

    with col2:
        st.metric("PO Lines", total_lines)

    with col3:
        # Overdue in red
        st.metric("Overdue Lines", int(overdue_lines),
                  delta=f"-{int(overdue_lines)}" if overdue_lines > 0 else None,
                  delta_color="inverse")

    with col4:
        st.metric("Suppliers", unique_suppliers)

    with col5:
        st.metric("Total Qty on Order", f"{total_qty:,.0f}")

    st.markdown("---")


def render_filters(df):
    """Render filter controls"""
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        suppliers = ['All'] + sorted(df['Name'].dropna().unique().tolist())
        supplier = st.selectbox(
            "Filter by Supplier",
            suppliers,
            index=suppliers.index(st.session_state.purchasing_filters['supplier'])
            if st.session_state.purchasing_filters['supplier'] in suppliers else 0
        )
        st.session_state.purchasing_filters['supplier'] = supplier

    with col2:
        overdue_only = st.checkbox(
            "Show Overdue Only",
            value=st.session_state.purchasing_filters['overdue_only']
        )
        st.session_state.purchasing_filters['overdue_only'] = overdue_only

    with col3:
        if st.button("Clear Filters"):
            st.session_state.purchasing_filters = {
                'supplier': 'All',
                'overdue_only': False,
            }
            st.rerun()


def apply_filters(df):
    """Apply filters to dataframe"""
    filtered = df.copy()

    if st.session_state.purchasing_filters['supplier'] != 'All':
        filtered = filtered[filtered['Name'] == st.session_state.purchasing_filters['supplier']]

    if st.session_state.purchasing_filters['overdue_only']:
        filtered = filtered[filtered['IsOverdue'] == True]

    return filtered


def color_po_rows(row):
    """Apply row coloring based on overdue status"""
    if row['IsOverdue']:
        return [f'background-color: {COLORS["po_overdue"]}'] * len(row)
    elif row.get('IsDueSoon', False):
        return [f'background-color: {COLORS["po_warning"]}'] * len(row)
    return [''] * len(row)


def render_po_table(df):
    """Render the main PO table"""
    st.markdown("### Open Purchase Orders")

    if df.empty:
        st.info("No purchase orders match the current filters.")
        return

    # Prepare display dataframe
    display_cols = ['PO', 'Name', 'Part Num', 'Description', 'Supplier Qty',
                    'Due Date_Display', 'DaysUntilDue', 'Job', 'Buyer ID']

    # Filter to existing columns
    display_cols = [c for c in display_cols if c in df.columns]
    display_df = df[display_cols].copy()

    # Rename columns for display
    display_df.columns = ['PO', 'Supplier', 'Part', 'Description', 'Qty',
                          'Due Date', 'Days Until Due', 'Job', 'Buyer'][:len(display_cols)]

    # Add status columns for styling
    display_df['IsOverdue'] = df['IsOverdue'].values
    display_df['IsDueSoon'] = df['IsDueSoon'].values

    # Style the dataframe
    styled_df = display_df.style.apply(color_po_rows, axis=1)

    # Display
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "IsOverdue": None,  # Hide
            "IsDueSoon": None,  # Hide
            "Days Until Due": st.column_config.NumberColumn(format="%d days"),
            "Qty": st.column_config.NumberColumn(format="%.0f"),
        }
    )

    st.caption(f"Showing {len(df)} PO lines")


def render_supplier_metrics(df):
    """Render supplier performance section"""
    with st.expander("📊 Supplier Performance", expanded=False):
        metrics_df = get_supplier_metrics(df)

        if metrics_df.empty:
            st.info("No supplier metrics available.")
            return

        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown("#### Supplier Summary")
            st.dataframe(
                metrics_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "OnTimeRate": st.column_config.ProgressColumn(
                        "On-Time %",
                        min_value=0,
                        max_value=100,
                        format="%.1f%%"
                    ),
                    "TotalQty": st.column_config.NumberColumn(format="%.0f"),
                }
            )

        with col2:
            st.markdown("#### PO Lines by Supplier")
            # Top 10 suppliers by line count
            top_suppliers = metrics_df.head(10)
            fig = px.bar(
                top_suppliers,
                x='TotalLines',
                y='Supplier',
                orientation='h',
                color='OverdueLines',
                color_continuous_scale=['green', 'red'],
                labels={'TotalLines': 'PO Lines', 'OverdueLines': 'Overdue'}
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


def render_po_job_linkage(df):
    """Render PO to Job linkage section"""
    with st.expander("🔗 PO to Job Linkage", expanded=False):
        linkage_df = get_po_job_linkage(df)

        if linkage_df.empty:
            st.info("No POs are currently linked to jobs. Most POs in the system are for stock replenishment.")
            return

        st.markdown("#### POs Linked to Jobs")
        st.caption("These POs are directly associated with specific jobs.")

        # Color rows based on overdue status
        def color_linkage_rows(row):
            if row['IsOverdue']:
                return [f'background-color: {COLORS["po_overdue"]}'] * len(row)
            return [''] * len(row)

        styled_df = linkage_df.style.apply(color_linkage_rows, axis=1)

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "IsOverdue": None,
                "Days Until Due": st.column_config.NumberColumn(format="%d days"),
                "Qty": st.column_config.NumberColumn(format="%.0f"),
            }
        )


def render_color_legend():
    """Render color legend"""
    st.markdown("---")
    st.markdown("#### Color Legend")
    legend_html = f"""
    <div style="display: flex; flex-wrap: wrap; gap: 20px; padding: 10px 0;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="background-color: {COLORS['po_overdue']}; padding: 4px 12px; border-radius: 4px;">■</span>
            <span>Overdue</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="background-color: {COLORS['po_warning']}; padding: 4px 12px; border-radius: 4px;">■</span>
            <span>Due Within 7 Days</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="background-color: #FFFFFF; border: 1px solid #ccc; padding: 4px 12px; border-radius: 4px;">■</span>
            <span>On Time</span>
        </div>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)


def main():
    """Main application function"""
    # Load data
    with st.spinner("Loading purchasing data..."):
        pos_df = load_open_pos()

    if pos_df.empty:
        st.error("Failed to load purchasing data. Please check data file paths.")
        return

    # Render components
    render_header(pos_df)
    render_filters(pos_df)

    # Apply filters
    filtered_df = apply_filters(pos_df)

    # Main content
    render_po_table(filtered_df)
    render_supplier_metrics(filtered_df)
    render_po_job_linkage(filtered_df)
    render_color_legend()


if __name__ == "__main__":
    main()
