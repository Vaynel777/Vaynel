#!/bin/bash

# Admin Dashboard Deployment Script
# Usage: ./deploy.sh [deployment_id] [target_host] [master_host] [master_port]
# Example: ./deploy.sh neo-toshiba 192.168.1.33 192.168.1.1 8000

set -e

DEPLOYMENT_ID="${1:-neo-toshiba}"
TARGET_HOST="${2:-192.168.1.33}"
MASTER_HOST="${3:-127.0.0.1}"
MASTER_PORT="${4:-8000}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying Admin Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 Deployment ID: $DEPLOYMENT_ID"
echo "🌐 Target Host: $TARGET_HOST"
echo "🔗 Master: $MASTER_HOST:$MASTER_PORT"
echo ""

# Detect deployment type
if [ "$DEPLOYMENT_ID" == "neo-toshiba" ]; then
    echo "📦 Deploying to neo-toshiba (Docker/Linux)..."
    REMOTE_PATH="/opt/openclaw/admin_dashboard"
    REMOTE_USER="openclaw"
    INIT_SYSTEM="systemd"
elif [ "$DEPLOYMENT_ID" == "mba2" ]; then
    echo "🍎 Deploying to mba2 (macOS)..."
    REMOTE_PATH="~/openclaw/admin_dashboard"
    REMOTE_USER="sarah"
    INIT_SYSTEM="launchctl"
else
    echo "🤖 Deploying to agent3 or custom target..."
    REMOTE_PATH="~/openclaw/admin_dashboard"
    REMOTE_USER="openclaw"
    INIT_SYSTEM="systemd"
fi

echo ""
echo "1️⃣  Copying files..."
ssh "$REMOTE_USER@$TARGET_HOST" "mkdir -p $REMOTE_PATH && echo '✅ Directory created'"

# Copy admin_dashboard files
scp -r "$SCRIPT_DIR"/* "$REMOTE_USER@$TARGET_HOST:$REMOTE_PATH/" > /dev/null 2>&1
echo "✅ Files copied to $REMOTE_PATH"

echo ""
echo "2️⃣  Installing dependencies..."
ssh "$REMOTE_USER@$TARGET_HOST" "cd $REMOTE_PATH && bash start.sh &" &
STARTUP_PID=$!
sleep 3
kill $STARTUP_PID 2>/dev/null || true
echo "✅ Dependencies installed"

echo ""
echo "3️⃣  Setting up initialization..."

if [ "$INIT_SYSTEM" == "systemd" ]; then
    # For Linux/Docker (neo-toshiba, agent3)
    SERVICE_FILE="$REMOTE_PATH/admin-dashboard.service"

    cat > "/tmp/admin-dashboard.service" << EOF
[Unit]
Description=OpenClaw Admin Dashboard ($DEPLOYMENT_ID)
After=network.target

[Service]
Type=simple
User=$REMOTE_USER
WorkingDirectory=$REMOTE_PATH
Environment="DEPLOYMENT_ID=$DEPLOYMENT_ID"
Environment="MASTER_HOST=$MASTER_HOST"
Environment="MASTER_PORT=$MASTER_PORT"
ExecStart=$REMOTE_PATH/venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    scp "/tmp/admin-dashboard.service" "$REMOTE_USER@$TARGET_HOST:$REMOTE_PATH/" > /dev/null 2>&1

    ssh "$REMOTE_USER@$TARGET_HOST" "sudo systemctl enable $REMOTE_PATH/admin-dashboard.service" || true
    echo "✅ Systemd service configured"

elif [ "$INIT_SYSTEM" == "launchctl" ]; then
    # For macOS (mba2)
    PLIST_PATH="$HOME/Library/LaunchAgents/com.openclaw.admin-dashboard.plist"

    cat > "/tmp/admin-dashboard.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.admin-dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>$REMOTE_PATH/venv/bin/python</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>app:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8001</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REMOTE_PATH</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>DEPLOYMENT_ID</key>
        <string>$DEPLOYMENT_ID</string>
        <key>MASTER_HOST</key>
        <string>$MASTER_HOST</string>
        <key>MASTER_PORT</key>
        <string>$MASTER_PORT</string>
    </dict>
    <key>StandardOutPath</key>
    <string>$REMOTE_PATH/logs/admin.log</string>
    <key>StandardErrorPath</key>
    <string>$REMOTE_PATH/logs/admin.log</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

    scp "/tmp/admin-dashboard.plist" "$REMOTE_USER@$TARGET_HOST:$PLIST_PATH" > /dev/null 2>&1

    ssh "$REMOTE_USER@$TARGET_HOST" "launchctl unload $PLIST_PATH; launchctl load $PLIST_PATH" || true
    echo "✅ LaunchAgent configured"
fi

echo ""
echo "4️⃣  Setting up cron job for Master sync..."

# Create cron script on remote
CRON_SCRIPT="$REMOTE_PATH/sync-metrics.sh"

cat > "/tmp/sync-metrics.sh" << 'EOF'
#!/bin/bash
DEPLOYMENT_ID="$DEPLOYMENT_ID"
LOCAL_PORT=8001
MASTER_HOST="$MASTER_HOST"
MASTER_PORT="$MASTER_PORT"

curl -s "http://localhost:$LOCAL_PORT/metrics" | \
  curl -X POST -d @- \
  -H "Content-Type: application/json" \
  "http://$MASTER_HOST:$MASTER_PORT/api/metrics/$DEPLOYMENT_ID" 2>&1 >> "$REMOTE_PATH/logs/sync.log"
EOF

sed "s|\$DEPLOYMENT_ID|$DEPLOYMENT_ID|g; s|\$MASTER_HOST|$MASTER_HOST|g; s|\$MASTER_PORT|$MASTER_PORT|g; s|\$REMOTE_PATH|$REMOTE_PATH|g" "/tmp/sync-metrics.sh" > "/tmp/sync-metrics.sh.tmp"
mv "/tmp/sync-metrics.sh.tmp" "/tmp/sync-metrics.sh"

scp "/tmp/sync-metrics.sh" "$REMOTE_USER@$TARGET_HOST:$CRON_SCRIPT" > /dev/null 2>&1
ssh "$REMOTE_USER@$TARGET_HOST" "chmod +x $CRON_SCRIPT" > /dev/null 2>&1

# Add cron job (runs every 5 minutes)
ssh "$REMOTE_USER@$TARGET_HOST" "
  (crontab -l 2>/dev/null | grep -v 'sync-metrics.sh'; echo '*/5 * * * * $CRON_SCRIPT') | crontab -
" || true

echo "✅ Cron job configured (every 5 minutes)"

echo ""
echo "5️⃣  Creating log directory..."
ssh "$REMOTE_USER@$TARGET_HOST" "mkdir -p $REMOTE_PATH/logs" > /dev/null 2>&1
echo "✅ Log directory created"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Deployment complete!"
echo ""
echo "Admin Dashboard is now running on:"
echo "  🌐 http://$TARGET_HOST:8001"
echo ""
echo "Next steps:"
echo "  1. Verify health: curl http://$TARGET_HOST:8001/health"
echo "  2. Check metrics: curl http://$TARGET_HOST:8001/metrics"
echo "  3. View logs: ssh $REMOTE_USER@$TARGET_HOST tail -f $REMOTE_PATH/logs/admin.log"
echo ""
