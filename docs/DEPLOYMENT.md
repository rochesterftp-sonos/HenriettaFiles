# Deployment Guide - Henrietta Dispatch Application

This guide covers deploying the Henrietta Dispatch application to production.

## Quick Start (Local Development)

For local development and testing:

```bash
# Navigate to project directory
cd henrietta-dispatch

# Run the startup script (Linux/Mac)
./start.sh

# OR on Windows
start.bat
```

The application will be available at `http://localhost:8501`

---

## Production Deployment Options

### Option 1: Internal Server (Recommended for MVP)

Deploy to an internal Windows or Linux server that has access to the Epicor data export location.

#### Requirements:
- Python 3.9+ installed
- Access to network share `\\192.168.168.230\EpicorData\...` or local copy of CSV files
- Port 8501 accessible to users (or configure alternative port)

#### Steps:

1. **Copy project to server:**
```bash
# Copy entire henrietta-dispatch folder to server
# For example: C:\Applications\henrietta-dispatch\
```

2. **Update data paths in `config/settings.py`:**
```python
# Point to actual network share or local copy
DATA_DIR = Path("\\\\192.168.168.230\\EpicorData\\Companies\\FTTMFG\\Processes\\MMINOIA")
# OR
DATA_DIR = Path("C:\\EpicorData\\Export")
```

3. **Install Python dependencies:**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

4. **Test the application:**
```bash
streamlit run app/main.py
```

5. **Set up as Windows Service (optional but recommended):**

Use NSSM (Non-Sucking Service Manager):
```powershell
# Download NSSM from https://nssm.cc/download
nssm install HenriettaDispatch "C:\Applications\henrietta-dispatch\venv\Scripts\streamlit.exe" "run app/main.py"
nssm set HenriettaDispatch AppDirectory "C:\Applications\henrietta-dispatch"
nssm start HenriettaDispatch
```

6. **Configure firewall:**
Allow inbound connections on port 8501 (or your chosen port)

7. **Access the application:**
Users can access at: `http://[server-ip]:8501` or `http://servername:8501`

---

### Option 2: Docker Deployment

For containerized deployment:

#### Create Dockerfile:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Mount data volume
VOLUME /data

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### Build and run:

```bash
# Build image
docker build -t henrietta-dispatch:latest .

# Run container
docker run -d \
  --name henrietta-dispatch \
  -p 8501:8501 \
  -v /path/to/data:/data \
  -v /path/to/database:/app/database \
  henrietta-dispatch:latest
```

---

### Option 3: Cloud Deployment (Future)

For external/remote access (requires additional security considerations):

- **Streamlit Cloud** - Easy deployment but requires public GitHub repo
- **AWS EC2** - Full control, can be in private VPC
- **Azure App Service** - Integrated with Microsoft ecosystem
- **Heroku** - Simple deployment but limited data options

**Security Note:** For cloud deployment, ensure:
- Data files are securely transferred (not stored in public repos)
- Application is behind authentication
- Network access is restricted to authorized users

---

## Configuration for Production

### 1. Update Settings

Edit `config/settings.py`:

```python
# Production data location
DATA_DIR = Path("\\\\your-file-server\\epicor-exports")

# Production database location (use persistent storage)
DATABASE_DIR = Path("D:\\AppData\\henrietta-dispatch\\database")

# Configure refresh interval (in seconds)
REFRESH_INTERVAL = 300  # 5 minutes

# Set URL patterns for drawings and POs
DRAWING_URL_PATTERN = "\\\\henfiles\\drawings\\{part}.pdf"
PO_URL_PATTERN = "http://epicor-server/po/{po}"
```

### 2. Set Up Scheduled Data Refresh

Ensure Epicor BAQ exports run on schedule:
- Current setup: Daily exports to network share
- Recommended: Every 4-6 hours for more current data
- Application auto-refreshes from files every 5 minutes

### 3. Database Backup

Set up regular backups of the SQLite database:

```bash
# Linux/Mac
0 2 * * * cp /path/to/database/dispatch.db /path/to/backups/dispatch_$(date +\%Y\%m\%d).db

# Windows Task Scheduler
copy "D:\AppData\henrietta-dispatch\database\dispatch.db" "D:\Backups\dispatch_%date:~-4,4%%date:~-10,2%%date:~-7,2%.db"
```

### 4. User Access Management

#### Create user mapping (future enhancement):

Edit `config/settings.py`:

```python
# Map Windows usernames to roles
USER_ROLES = {
    "kyle.smith": "production_planner",
    "amy.jones": "purchasing",
    "richard.brown": "production_supervisor",
    # ... add more users
}
```

---

## Monitoring & Maintenance

### Log Files

Streamlit logs are output to console. Redirect to file:

```bash
streamlit run app/main.py > logs/app.log 2>&1
```

### Health Checks

Application health endpoint: `http://[server]:8501/_stcore/health`

Set up monitoring to check this endpoint regularly.

### Data Refresh Verification

Monitor the "Last updated" timestamp in the UI header. If it's stale:
1. Check that CSV files are being updated on the network share
2. Check application has read permissions to data files
3. Check application logs for errors

---

## Troubleshooting

### Application won't start

**Symptom:** Error on startup
**Solution:**
1. Check Python version: `python --version` (must be 3.9+)
2. Verify dependencies: `pip list | grep streamlit`
3. Check port availability: `netstat -an | grep 8501`

### No data showing

**Symptom:** "No data available" message
**Solution:**
1. Verify `DATA_DIR` path in `config/settings.py`
2. Check CSV files exist and have data: `ls -lh /path/to/data/*.csv`
3. Check file permissions: Application needs read access
4. Look for errors in console/logs

### Notes not saving

**Symptom:** Notes disappear or can't be added
**Solution:**
1. Check database folder permissions (needs write access)
2. Verify SQLite database exists: `ls database/dispatch.db`
3. Try manual database init: `python app/utils/database.py`
4. For network drives, consider moving database to local disk

### Performance issues

**Symptom:** Application is slow to load or filter
**Solution:**
1. Check data volume - app handles ~500-1000 jobs well
2. Reduce refresh interval if too frequent
3. Add indexes to database for faster note lookups
4. Consider pagination for very large datasets (>2000 jobs)

---

## Rollback Plan

If issues occur in production:

1. **Keep the old Excel workbook accessible** until MVP is proven stable
2. **Maintain backup of database:** Notes are critical data
3. **Document data export process:** Ensure you can recreate data files
4. **Version control:** Tag stable releases in git

---

## Future Enhancements

After successful MVP deployment, consider:

1. **Active Directory integration** - Auto-detect username
2. **Email notifications** - Alert on critical jobs
3. **Mobile responsive design** - Access from tablets on shop floor
4. **Additional views** - Jobs, Shipped, Shortages (Phase 2)
5. **Direct Epicor integration** - Real-time data via REST API
6. **Advanced analytics** - Trend analysis, predictive delays
7. **Export capabilities** - Download filtered data to Excel
8. **Multi-facility support** - Ontario integration

---

## Support Contacts

- **Application Issues:** [IT Department]
- **Data Issues:** [Epicor Administrator]
- **Feature Requests:** [Product Owner]
- **User Training:** [Kyle - Primary User]

---

## Acceptance Criteria Checklist

Before going live, verify:

- [ ] All data loads correctly from CSV files
- [ ] Status colors match specification
- [ ] All filters work (Unengineered, In-Work, ESI, Customer)
- [ ] Notes can be added and persist across refreshes
- [ ] Drawing/PO icons are configured (even if placeholder)
- [ ] Auto-refresh works
- [ ] Theme toggle works
- [ ] Kyle can complete his morning workflow in ≤30 minutes
- [ ] Application is accessible from all required workstations
- [ ] Database backup is scheduled
- [ ] Users are trained on new system
- [ ] Legacy Excel workbook is archived (not deleted!)
