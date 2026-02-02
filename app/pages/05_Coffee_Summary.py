"""
Coffee Summary Page - Daily Production Overview
A quick morning snapshot for the production scheduler
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import io

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.settings import APP_TITLE, PAGE_ICON, COLORS
from app.utils.data_loader import load_all_data, load_open_pos, get_cache_status

# Page configuration
st.set_page_config(
    page_title=f"Coffee Summary - {APP_TITLE}",
    page_icon="☕",
    layout="wide"
)


def get_summary_metrics(df):
    """Calculate key metrics for the summary"""
    today = pd.Timestamp.now().normalize()

    metrics = {
        "total_orders": len(df),
        "total_jobs": len(df[df['Job'] != 'No Job']),
        "no_job": len(df[df['Job'] == 'No Job']),
        "unengineered": len(df[df['Status'] == 'unengineered']),
        "in_work": len(df[df['Status'] == 'in_work']),
        "not_started": len(df[df['Status'] == 'not_started']),
        "past_due": len(df[df['IsPastDue'] == True]),
        "material_shortage": len(df[df['MaterialShort'] == True]),
        "can_ship": len(df[df['CanShip'] == True]),
        "esi_orders": len(df[df['IsESI'] == True]),
    }

    # Due this week
    week_end = today + timedelta(days=7)
    df['Ship By'] = pd.to_datetime(df['Ship By'], errors='coerce')
    metrics["due_this_week"] = len(df[(df['Ship By'] >= today) & (df['Ship By'] <= week_end)])

    # Due today
    metrics["due_today"] = len(df[df['Ship By'] == today])

    return metrics


def create_status_pie_chart(df):
    """Create a pie chart of job statuses"""
    status_counts = df['Status'].value_counts()

    color_map = {
        'in_work': '#90EE90',
        'unengineered': '#ADD8E6',
        'not_started': '#FFFFFF',
        'no_job': '#FFA500',
    }

    fig = px.pie(
        values=status_counts.values,
        names=status_counts.index.map({
            'in_work': 'In Work',
            'unengineered': 'Unengineered',
            'not_started': 'Not Started',
            'no_job': 'No Job'
        }),
        title="Jobs by Status",
        color=status_counts.index,
        color_discrete_map=color_map
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(showlegend=False, height=300)
    return fig


def create_due_date_chart(df):
    """Create a bar chart of items due by week"""
    df = df.copy()
    df['Ship By'] = pd.to_datetime(df['Ship By'], errors='coerce')
    df = df.dropna(subset=['Ship By'])

    # Group by week
    df['Week'] = df['Ship By'].dt.to_period('W').apply(lambda x: x.start_time)
    weekly_counts = df.groupby('Week').size().reset_index(name='Count')
    weekly_counts['Week'] = weekly_counts['Week'].dt.strftime('%m/%d')

    # Limit to next 8 weeks
    weekly_counts = weekly_counts.head(8)

    fig = px.bar(
        weekly_counts,
        x='Week',
        y='Count',
        title="Orders Due by Week",
        color_discrete_sequence=['#4CAF50']
    )
    fig.update_layout(height=300, xaxis_title="Week Starting", yaxis_title="Orders")
    return fig


def create_alerts_list(df, metrics):
    """Generate list of alerts and concerns"""
    alerts = []

    # Critical alerts (red)
    if metrics['past_due'] > 0:
        alerts.append({
            "level": "critical",
            "icon": "🔴",
            "message": f"{metrics['past_due']} orders are PAST DUE",
            "action": "Review and expedite immediately"
        })

    if metrics['material_shortage'] > 0:
        alerts.append({
            "level": "critical",
            "icon": "🔴",
            "message": f"{metrics['material_shortage']} jobs have MATERIAL SHORTAGES",
            "action": "Contact purchasing for status"
        })

    # Warning alerts (yellow)
    if metrics['no_job'] > 0:
        alerts.append({
            "level": "warning",
            "icon": "🟡",
            "message": f"{metrics['no_job']} order lines have NO JOB assigned",
            "action": "Create jobs or assign stock jobs"
        })

    if metrics['unengineered'] > 0:
        alerts.append({
            "level": "warning",
            "icon": "🟡",
            "message": f"{metrics['unengineered']} jobs are UNENGINEERED",
            "action": "Follow up with engineering"
        })

    if metrics['due_today'] > 0:
        alerts.append({
            "level": "warning",
            "icon": "🟡",
            "message": f"{metrics['due_today']} orders due TODAY",
            "action": "Verify shipping readiness"
        })

    # Info alerts (blue)
    if metrics['can_ship'] > 0:
        alerts.append({
            "level": "info",
            "icon": "🟢",
            "message": f"{metrics['can_ship']} orders CAN SHIP from inventory",
            "action": "Coordinate with shipping"
        })

    if metrics['due_this_week'] > 0:
        alerts.append({
            "level": "info",
            "icon": "🔵",
            "message": f"{metrics['due_this_week']} orders due this week",
            "action": "Plan accordingly"
        })

    return alerts


def get_past_due_details(df):
    """Get details of past due orders"""
    past_due = df[df['IsPastDue'] == True].copy()
    if past_due.empty:
        return None

    past_due = past_due.sort_values('Ship By')
    return past_due[['Job', 'OrderLineRel', 'Part', 'Name', 'Ship By_Display', 'Status', 'Rem Qty']].head(10)


def get_material_shortage_jobs(df):
    """Get jobs with material shortages"""
    shortage = df[df['MaterialShort'] == True].copy()
    if shortage.empty:
        return None

    return shortage[['Job', 'Part', 'Name', 'Ship By_Display', 'Rem Qty']].head(10)


def generate_email_body(metrics, alerts, df):
    """Generate HTML email body"""
    today = datetime.now().strftime("%A, %B %d, %Y")

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h1 {{ color: #333; }}
            .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #f5f5f5; border-radius: 8px; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
            .metric-label {{ font-size: 12px; color: #666; }}
            .alert-critical {{ background: #FFEBEE; border-left: 4px solid #F44336; padding: 10px; margin: 5px 0; }}
            .alert-warning {{ background: #FFF3E0; border-left: 4px solid #FF9800; padding: 10px; margin: 5px 0; }}
            .alert-info {{ background: #E3F2FD; border-left: 4px solid #2196F3; padding: 10px; margin: 5px 0; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
        </style>
    </head>
    <body>
        <h1>☕ Henrietta Dispatch - Daily Summary</h1>
        <p><strong>Date:</strong> {today}</p>

        <h2>Key Metrics</h2>
        <div>
            <div class="metric">
                <div class="metric-value">{metrics['total_orders']}</div>
                <div class="metric-label">Total Orders</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics['in_work']}</div>
                <div class="metric-label">In Work</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics['past_due']}</div>
                <div class="metric-label">Past Due</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics['due_this_week']}</div>
                <div class="metric-label">Due This Week</div>
            </div>
        </div>

        <h2>Alerts & Action Items</h2>
    """

    for alert in alerts:
        level_class = f"alert-{alert['level']}"
        html += f"""
        <div class="{level_class}">
            <strong>{alert['icon']} {alert['message']}</strong><br>
            <em>Action: {alert['action']}</em>
        </div>
        """

    # Add past due table if any
    if metrics['past_due'] > 0:
        past_due = get_past_due_details(df)
        if past_due is not None:
            html += """
            <h2>Past Due Orders (Top 10)</h2>
            <table>
                <tr><th>Job</th><th>Order</th><th>Part</th><th>Customer</th><th>Ship By</th><th>Remaining</th></tr>
            """
            for _, row in past_due.iterrows():
                html += f"""
                <tr>
                    <td>{row['Job']}</td>
                    <td>{row['OrderLineRel']}</td>
                    <td>{row['Part']}</td>
                    <td>{row['Name']}</td>
                    <td>{row['Ship By_Display']}</td>
                    <td>{row['Rem Qty']}</td>
                </tr>
                """
            html += "</table>"

    html += """
        <hr>
        <p><em>Generated by Henrietta Dispatch</em></p>
    </body>
    </html>
    """

    return html


def send_email(to_email, subject, html_body, smtp_server="", smtp_port=587, username="", password=""):
    """Send email with the summary"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = username
        msg['To'] = to_email

        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)

        return True, "Email sent successfully!"
    except Exception as e:
        return False, f"Error sending email: {str(e)}"


def main():
    # Header
    st.title("☕ Coffee Summary")
    st.caption(f"Daily Production Overview - {datetime.now().strftime('%A, %B %d, %Y')}")

    # Initialize session state for coffee summary data
    if 'coffee_data' not in st.session_state:
        st.session_state.coffee_data = None
    if 'coffee_data_loaded_at' not in st.session_state:
        st.session_state.coffee_data_loaded_at = None

    # Check if we need to load data
    need_load = False
    today = datetime.now().date()

    if st.session_state.coffee_data is None:
        need_load = True
    elif st.session_state.coffee_data_loaded_at:
        # Check if data was loaded today
        loaded_date = st.session_state.coffee_data_loaded_at.date()
        if loaded_date != today:
            need_load = True  # New day, reload

    # Refresh controls
    col_header1, col_header2, col_header3 = st.columns([2, 1, 1])

    with col_header1:
        if st.session_state.coffee_data_loaded_at:
            loaded_time = st.session_state.coffee_data_loaded_at.strftime("%I:%M %p")
            st.info(f"📊 Data loaded at **{loaded_time}** today")
        else:
            st.info("📊 Data not yet loaded")

    with col_header2:
        if st.button("🔄 Refresh Data", type="primary", use_container_width=True):
            need_load = True
            st.session_state.coffee_data = None

    with col_header3:
        auto_refresh = st.checkbox("Auto-refresh on new day", value=True)

    # Load data if needed
    if need_load or (auto_refresh and st.session_state.coffee_data is None):
        with st.spinner("Loading fresh data..."):
            df = load_all_data()
            if df is not None and not df.empty:
                st.session_state.coffee_data = df
                st.session_state.coffee_data_loaded_at = datetime.now()
                st.rerun()
            else:
                st.error("No data available. Please check data file configuration in Settings.")
                return

    # Use cached data
    df = st.session_state.coffee_data

    if df is None or df.empty:
        st.error("No data available. Click 'Refresh Data' to load.")
        return

    # Calculate metrics
    metrics = get_summary_metrics(df)
    alerts = create_alerts_list(df, metrics)

    # Top metrics row
    st.markdown("---")
    st.markdown("### 📊 Today's Numbers")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("Total Orders", metrics['total_orders'])
    with col2:
        st.metric("In Work", metrics['in_work'],
                  delta=None if metrics['in_work'] == 0 else f"{round(metrics['in_work']/metrics['total_orders']*100)}%")
    with col3:
        delta_color = "inverse" if metrics['past_due'] > 0 else "normal"
        st.metric("Past Due", metrics['past_due'], delta_color=delta_color)
    with col4:
        st.metric("Due This Week", metrics['due_this_week'])
    with col5:
        st.metric("Material Short", metrics['material_shortage'])
    with col6:
        st.metric("Can Ship", metrics['can_ship'])

    # Alerts section
    st.markdown("---")
    st.markdown("### ⚠️ Alerts & Action Items")

    if not alerts:
        st.success("✅ No critical alerts today!")
    else:
        for alert in alerts:
            if alert['level'] == 'critical':
                st.error(f"{alert['icon']} **{alert['message']}** - {alert['action']}")
            elif alert['level'] == 'warning':
                st.warning(f"{alert['icon']} **{alert['message']}** - {alert['action']}")
            else:
                st.info(f"{alert['icon']} **{alert['message']}** - {alert['action']}")

    # Charts row
    st.markdown("---")
    st.markdown("### 📈 Visual Overview")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        fig_status = create_status_pie_chart(df)
        st.plotly_chart(fig_status, use_container_width=True)

    with col_chart2:
        fig_due = create_due_date_chart(df)
        st.plotly_chart(fig_due, use_container_width=True)

    # Details sections
    st.markdown("---")
    col_detail1, col_detail2 = st.columns(2)

    with col_detail1:
        st.markdown("### 🔴 Past Due Orders")
        past_due = get_past_due_details(df)
        if past_due is not None and not past_due.empty:
            st.dataframe(past_due, use_container_width=True, hide_index=True)
        else:
            st.success("No past due orders!")

    with col_detail2:
        st.markdown("### 🟡 Material Shortages")
        shortages = get_material_shortage_jobs(df)
        if shortages is not None and not shortages.empty:
            st.dataframe(shortages, use_container_width=True, hide_index=True)
        else:
            st.success("No material shortages!")

    # ESI vs Non-ESI breakdown
    st.markdown("---")
    st.markdown("### 🏥 ESI vs Standard Orders")

    col_esi1, col_esi2, col_esi3 = st.columns(3)

    esi_count = metrics['esi_orders']
    non_esi_count = metrics['total_orders'] - esi_count

    with col_esi1:
        st.metric("ESI (Medical) Orders", esi_count)
    with col_esi2:
        st.metric("Standard Orders", non_esi_count)
    with col_esi3:
        esi_pct = round(esi_count / metrics['total_orders'] * 100) if metrics['total_orders'] > 0 else 0
        st.metric("ESI Percentage", f"{esi_pct}%")

    # Email section
    st.markdown("---")
    st.markdown("### 📧 Email Summary to Supervisor")

    with st.expander("Configure & Send Email", expanded=False):
        st.caption("Send this summary to your supervisor")

        col_email1, col_email2 = st.columns(2)

        with col_email1:
            to_email = st.text_input("Supervisor's Email", placeholder="supervisor@company.com")
            smtp_server = st.text_input("SMTP Server", placeholder="smtp.office365.com")
            smtp_port = st.number_input("SMTP Port", value=587, min_value=1, max_value=65535)

        with col_email2:
            from_email = st.text_input("Your Email", placeholder="you@company.com")
            email_password = st.text_input("Email Password", type="password")

        if st.button("📤 Send Email Summary", type="primary"):
            if not all([to_email, smtp_server, from_email, email_password]):
                st.error("Please fill in all email fields")
            else:
                subject = f"☕ Henrietta Dispatch Summary - {datetime.now().strftime('%m/%d/%Y')}"
                html_body = generate_email_body(metrics, alerts, df)

                with st.spinner("Sending email..."):
                    success, message = send_email(
                        to_email, subject, html_body,
                        smtp_server, smtp_port, from_email, email_password
                    )

                if success:
                    st.success(message)
                else:
                    st.error(message)

        # Preview option
        if st.checkbox("Preview Email Content"):
            html_body = generate_email_body(metrics, alerts, df)
            st.markdown(html_body, unsafe_allow_html=True)

    # Data freshness
    st.markdown("---")
    st.caption("Data Status")
    try:
        cache_status = get_cache_status()
        last_check = cache_status.get("_last_check_str", "Unknown")
        st.caption(f"Last data check: {last_check}")
    except:
        pass


if __name__ == "__main__":
    main()
