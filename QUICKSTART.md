# 🚀 Quick Start Guide

Get the Smart Traffic Control System running in under 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Verify Setup (Optional)

```bash
python setup_check.py
```

This will check that all required packages are installed correctly.

## Step 3: Run the System

```bash
python main.py
```

You should see:

```
============================================================
🚦 SMART TRAFFIC CONTROL SYSTEM
   King Khalid University - Graduation Project
============================================================

📊 Initializing database...
✓ Database initialized (sqlite mode)
🚥 Setting up intersection configuration...
✓ Created default intersection (ID: 1)
🎮 Starting simulation (DEMO mode)...
✓ Demo simulation initialized
✓ Demo simulation started

============================================================
✅ System initialization complete!
============================================================

🔄 Starting traffic control loop...

🌐 Dashboard running at:
   • http://localhost:8000
   • http://127.0.0.1:8000

💡 Press Ctrl+C to stop
```

## Step 4: Open Dashboard

Open your web browser and go to:

```
http://localhost:8000
```

You should see the dark-themed dashboard with:
- 4 lane camera feeds (showing demo traffic)
- Live intersection overview in the center
- Real-time metrics and charts
- Signal countdowns

## Features to Try

### 1. Watch Real-Time Updates
- Vehicle counts update every second
- Signal lights change automatically
- Chart shows traffic density trends

### 2. Toggle AI Mode
- Click the "AI Mode" button in the top-right
- Switch between AI-optimized and fixed timer modes
- Compare performance

### 3. Trigger Emergency Override
- Click the red "🚨 Emergency Override" button
- Select a lane (N, S, E, or W)
- Watch that lane get immediate green light
- All other lanes go red

## Troubleshooting

### Port 8000 Already in Use?

Edit `.env` and change:
```bash
API_PORT=8080
```

Then restart.

### Dashboard Not Loading?

1. Check that main.py is running
2. Look for the "Dashboard running at" message
3. Try `http://127.0.0.1:8000` instead of localhost

### WebSocket Not Connecting?

Check the connection status (top-right corner):
- Green dot = Connected
- Red dot = Disconnected

If disconnected, refresh the page.

## What's Next?

### Run Performance Evaluation

Compare AI vs fixed timer:

```bash
# Run baseline (30 minutes)
python evaluation/run_baseline.py

# Run AI-optimized (30 minutes)
python evaluation/run_ai.py

# Compare results
python evaluation/compare_results.py
```

### Enable Real YOLO Detection

By default, the system generates synthetic demo feeds. To use real YOLO detection:

1. The YOLOv8 model will download automatically on first use
2. Add real camera feeds or video files to the `video/` directory
3. Update the feed manager configuration

### Connect to MySQL

Edit `.env`:
```bash
DB_MODE=mysql
MYSQL_HOST=localhost
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=smart_traffic
```

Create the database first:
```sql
CREATE DATABASE smart_traffic;
```

## Need Help?

Check the full [README.md](README.md) for:
- Complete documentation
- Architecture details
- API reference
- Advanced configuration

---

**Ready to go? Run `python main.py` and visit http://localhost:8000** 🎉
