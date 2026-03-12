#!/bin/bash
"""
Phase 4 Integration - Deploy Admin Dashboard Template
Deploys /admin_dashboard template to all 3 instances (neo-toshiba, mba2, agent3)
Sets up DEPLOYMENT_ID and MASTER_HOST environment variables
Starts the admin dashboard on port 8001 on each instance
"""

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
ADMIN_DASHBOARD_DIR="$PARENT_DIR/admin_dashboard"
MASTER_HOST="127.0.0.1"  # Set to the actual Master Dashboard IP if deploying to remote

# Deployments to deploy to
declare -A DEPLOYMENTS=(
    [neo-toshiba]="openclaw@192.168.1.33"
    [mba2]="sarah@192.168.1.56"
    [agent3]="openclaw@192.168.1.100"
)

DEPLOY_REMOTE_PATH="/opt/admin_dashboard"

echo "================================================================================
🚀 Admin Dashboard Deployment (Phase 4)
================================================================================"
echo ""
echo "Source: $ADMIN_DASHBOARD_DIR"
echo "Target remote path: $DEPLOY_REMOTE_PATH"
echo "Master: $MASTER_HOST:8000"
echo ""

# Validate source exists
if [ ! -d "$ADMIN_DASHBOARD_DIR" ]; then
    echo "❌ Admin dashboard directory not found: $ADMIN_DASHBOARD_DIR"
    exit 1
fi

echo "✅ Admin dashboard source found"
echo ""

# Deploy to each instance
for deployment_id in "${!DEPLOYMENTS[@]}"; do
    remote="${DEPLOYMENTS[$deployment_id]}"
    echo "================================================================================
📦 Deploying to: $deployment_id ($remote)
================================================================================"

    # Step 1: Create remote directory
    echo "📂 Creating remote directory..."
    ssh "$remote" "mkdir -p $DEPLOY_REMOTE_PATH" || {
        echo "❌ Failed to create remote directory"
        continue
    }

    # Step 2: SCP the admin_dashboard directory
    echo "📤 Copying admin_dashboard files..."
    scp -r "$ADMIN_DASHBOARD_DIR"/* "$remote:$DEPLOY_REMOTE_PATH/" || {
        echo "❌ Failed to copy files"
        continue
    }

    # Step 3: Create startup wrapper script on remote
    echo "🔧 Creating startup wrapper..."
    ssh "$remote" "cat > $DEPLOY_REMOTE_PATH/start_with_config.sh << 'EOFSTART'
#!/bin/bash
set -e

export DEPLOYMENT_ID=$deployment_id
export MASTER_HOST=$MASTER_HOST
export MASTER_PORT=8000

cd $DEPLOY_REMOTE_PATH
bash start.sh
EOFSTART
chmod +x $DEPLOY_REMOTE_PATH/start_with_config.sh" || {
        echo "❌ Failed to create startup wrapper"
        continue
    }

    # Step 4: Start the admin dashboard on the remote instance
    echo "🚀 Starting admin dashboard on $deployment_id..."
    ssh "$remote" "cd $DEPLOY_REMOTE_PATH && nohup bash start_with_config.sh > admin_dashboard.log 2>&1 &" || {
        echo "⚠️  Failed to start admin dashboard (may already be running)"
    }

    # Step 5: Verify it started
    echo "⏳ Waiting for startup..."
    sleep 3

    if ssh "$remote" "curl -s http://localhost:8001/health > /dev/null 2>&1"; then
        echo "✅ Admin dashboard running on $deployment_id"
        echo "   URL: http://${remote%@*}:8001"
        echo "   Health: http://${remote%@*}:8001/health"
    else
        echo "⚠️  Could not verify admin dashboard startup on $deployment_id"
        echo "   Check: ssh $remote 'tail -50 $DEPLOY_REMOTE_PATH/admin_dashboard.log'"
    fi

    echo ""
done

echo "================================================================================
✅ Deployment Complete
================================================================================"
echo ""
echo "Next steps:"
echo "1. Verify each instance is running:"
for deployment_id in "${!DEPLOYMENTS[@]}"; do
    remote="${DEPLOYMENTS[$deployment_id]}"
    echo "   curl http://${remote%@*}:8001/health"
done
echo ""
echo "2. Set up cron job on Master to poll metrics every 5 minutes:"
echo "   * * * * * /path/to/metric_collector_cron.py  (run every 5 min)"
echo ""
echo "3. View Master Dashboard:"
echo "   http://localhost:8000"
echo ""
