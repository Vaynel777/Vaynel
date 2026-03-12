#!/bin/bash
"""
Phase 4 Integration - Setup Cron Jobs
Configures cron job to run metric_collector_cron.py every 5 minutes on Master Dashboard VM
"""

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_SCRIPT="$SCRIPT_DIR/metric_collector_cron.py"
CRON_LOG="/var/log/admin_dashboard_cron.log"

echo "================================================================================
⏰ Setting up cron jobs (Phase 4)
================================================================================"
echo ""

# Check if script exists
if [ ! -f "$CRON_SCRIPT" ]; then
    echo "❌ Cron script not found: $CRON_SCRIPT"
    exit 1
fi

# Make script executable
chmod +x "$CRON_SCRIPT"
echo "✅ Made cron script executable: $CRON_SCRIPT"

# Create log file
if [ ! -f "$CRON_LOG" ]; then
    sudo touch "$CRON_LOG"
    sudo chmod 666 "$CRON_LOG"
    echo "✅ Created cron log file: $CRON_LOG"
fi

# Check if already in crontab
if crontab -l 2>/dev/null | grep -q "metric_collector_cron.py"; then
    echo "⚠️  Cron job already exists in crontab"
    echo "   To update, remove the old entry first:"
    echo "   crontab -e"
    exit 0
fi

# Add cron job (every 5 minutes)
CRON_ENTRY="*/5 * * * * $CRON_SCRIPT >> $CRON_LOG 2>&1"

echo "Adding cron job:"
echo "  $CRON_ENTRY"
echo ""

(crontab -l 2>/dev/null || echo "") | {
    cat
    echo "$CRON_ENTRY"
} | crontab -

echo "✅ Cron job installed successfully"
echo ""
echo "Verification:"
echo "  crontab -l | grep metric_collector"
echo ""
echo "View logs:"
echo "  tail -f $CRON_LOG"
echo ""
