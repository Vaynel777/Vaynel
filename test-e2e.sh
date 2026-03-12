#!/bin/bash

# End-to-End Test Script for Phase 4 Integration
# Tests: Master Dashboard + Admin Dashboard + Event Pusher + Metric Sync
# Usage: bash test-e2e.sh

set -e

MASTER_HOST="127.0.0.1"
MASTER_PORT=8000
ADMIN_HOST="127.0.0.1"
ADMIN_PORT=8001
DEPLOYMENT_ID="test-instance"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Phase 4 End-to-End Test Suite"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

PASSED=0
FAILED=0

# Test helper
test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local expected_code="$4"
    local data="$5"

    echo -n "Testing: $name... "

    if [ "$method" == "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null)
    else
        response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" == "$expected_code" ]; then
        echo "✅ PASS"
        ((PASSED++))
        return 0
    else
        echo "❌ FAIL (got $http_code, expected $expected_code)"
        ((FAILED++))
        return 1
    fi
}

# Test helper for JSON response
test_json_field() {
    local name="$1"
    local url="$2"
    local field="$3"
    local expected_value="$4"

    echo -n "Testing: $name... "

    response=$(curl -s "$url" 2>/dev/null)
    value=$(echo "$response" | jq -r "$field" 2>/dev/null || echo "null")

    if [ "$value" == "$expected_value" ] || [ "$expected_value" == "*" ]; then
        echo "✅ PASS"
        ((PASSED++))
        return 0
    else
        echo "❌ FAIL (got '$value', expected '$expected_value')"
        ((FAILED++))
        return 1
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Checking if services are running..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Master health
echo -n "Checking Master Dashboard (port $MASTER_PORT)... "
if curl -s "http://$MASTER_HOST:$MASTER_PORT/health" > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Not running"
    echo ""
    echo "ERROR: Master Dashboard not running!"
    echo "Start it with: cd ~/mission_control_master && bash start.sh"
    exit 1
fi

# Admin health
echo -n "Checking Admin Dashboard (port $ADMIN_PORT)... "
if curl -s "http://$ADMIN_HOST:$ADMIN_PORT/health" > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Not running"
    echo ""
    echo "ERROR: Admin Dashboard not running!"
    echo "Start it with: cd ~/mission_control_master/admin_dashboard && DEPLOYMENT_ID=test-instance MASTER_HOST=127.0.0.1 MASTER_PORT=8000 bash start.sh"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Testing Master Dashboard API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_endpoint "Master health check" "GET" "http://$MASTER_HOST:$MASTER_PORT/health" "200"
test_json_field "Master status is 'ok'" "http://$MASTER_HOST:$MASTER_PORT/health" ".status" "ok"
test_endpoint "Master status endpoint" "GET" "http://$MASTER_HOST:$MASTER_PORT/status" "200"
test_endpoint "Master deployments list" "GET" "http://$MASTER_HOST:$MASTER_PORT/api/deployments" "200"
test_endpoint "Master dashboard data" "GET" "http://$MASTER_HOST:$MASTER_PORT/api/dashboard" "200"
test_endpoint "Master events list" "GET" "http://$MASTER_HOST:$MASTER_PORT/api/events" "200"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Testing Admin Dashboard API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_endpoint "Admin health check" "GET" "http://$ADMIN_HOST:$ADMIN_PORT/health" "200"
test_json_field "Admin deployment_id" "http://$ADMIN_HOST:$ADMIN_PORT/health" ".deployment_id" "*"
test_endpoint "Admin status endpoint" "GET" "http://$ADMIN_HOST:$ADMIN_PORT/status" "200"
test_endpoint "Admin metrics (for Master)" "GET" "http://$ADMIN_HOST:$ADMIN_PORT/metrics" "200"
test_json_field "Admin metrics has deployment_id" "http://$ADMIN_HOST:$ADMIN_PORT/metrics" ".deployment_id" "*"
test_json_field "Admin metrics has guardrails" "http://$ADMIN_HOST:$ADMIN_PORT/metrics" ".guardrails | keys | length > 0" "true"
test_endpoint "Admin dashboard data" "GET" "http://$ADMIN_HOST:$ADMIN_PORT/api/dashboard" "200"
test_endpoint "Admin events list" "GET" "http://$ADMIN_HOST:$ADMIN_PORT/events" "200"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  Testing Event Pushing"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get initial event count on Master
initial_count=$(curl -s "http://$MASTER_HOST:$MASTER_PORT/api/events?limit=1" | jq '.critical_events | length' 2>/dev/null || echo "0")

# Push a critical event from Admin
echo "Pushing critical event from Admin to Master..."
test_endpoint "Rate limit alert" "POST" "http://$ADMIN_HOST:$ADMIN_PORT/notify/rate_limit_exceeded" "200" \
    '{"model_id":"deepseek-tier1","current":1050,"limit":1000}'

# Wait for event to propagate
sleep 2

# Check if event arrived on Master
final_count=$(curl -s "http://$MASTER_HOST:$MASTER_PORT/api/events?limit=50" | jq '.critical_events | length' 2>/dev/null || echo "0")

echo -n "Testing: Event pushed to Master... "
if [ "$final_count" -gt "$initial_count" ]; then
    echo "✅ PASS"
    ((PASSED++))
    # Verify event details
    latest_event=$(curl -s "http://$MASTER_HOST:$MASTER_PORT/api/events?limit=1" | jq '.critical_events[0]' 2>/dev/null)
    echo "  Latest event:"
    echo "    Type: $(echo "$latest_event" | jq -r '.event_type // "N/A"')"
    echo "    Severity: $(echo "$latest_event" | jq -r '.severity // "N/A"')"
    echo "    Message: $(echo "$latest_event" | jq -r '.message // "N/A"')"
else
    echo "❌ FAIL (event not received on Master)"
    ((FAILED++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  Testing Metric Sync"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get metrics from Admin
echo "Getting metrics from Admin..."
admin_metrics=$(curl -s "http://$ADMIN_HOST:$ADMIN_PORT/metrics")
deployment_id=$(echo "$admin_metrics" | jq -r '.deployment_id // "unknown"')

echo "  Deployment ID: $deployment_id"
echo "  Has uptime: $(echo "$admin_metrics" | jq 'has("uptime_percent")')"
echo "  Has guardrails: $(echo "$admin_metrics" | jq '.guardrails | length')"

# Simulate Master pulling metrics (what cron would do)
echo ""
echo "Simulating Master metric pull (like cron would do)..."
test_endpoint "Master receives metrics from Admin" "POST" \
    "http://$MASTER_HOST:$MASTER_PORT/api/metrics/$deployment_id" "200" "$admin_metrics"

# Verify metrics were stored on Master
echo "Checking if metrics stored on Master..."
test_endpoint "Get stored metrics from Master" "GET" \
    "http://$MASTER_HOST:$MASTER_PORT/api/metrics/$deployment_id" "200"

stored_metrics=$(curl -s "http://$MASTER_HOST:$MASTER_PORT/api/metrics/$deployment_id")
echo -n "Testing: Metrics match on Master... "
if echo "$stored_metrics" | jq '.deployment_id' | grep -q "$deployment_id"; then
    echo "✅ PASS"
    ((PASSED++))
else
    echo "❌ FAIL"
    ((FAILED++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  Testing Frontend Loading"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_endpoint "Master Dashboard frontend" "GET" "http://$MASTER_HOST:$MASTER_PORT/" "200"
test_endpoint "Admin Dashboard frontend" "GET" "http://$ADMIN_HOST:$ADMIN_PORT/" "200"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Test Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 All tests passed! Phase 4 integration is ready."
    echo ""
    echo "Next steps:"
    echo "  1. Deploy to instances: bash admin_dashboard/deploy.sh neo-toshiba 192.168.1.33 127.0.0.1 8000"
    echo "  2. Check Master dashboard: http://localhost:8000"
    echo "  3. Monitor metric sync logs: tail -f /tmp/mc_sync.log"
    echo ""
    exit 0
else
    echo "⚠️  Some tests failed. See details above."
    echo ""
    echo "Common issues:"
    echo "  - Master Dashboard not running: cd ~/mission_control_master && bash start.sh"
    echo "  - Admin Dashboard not running: cd ~/mission_control_master/admin_dashboard && DEPLOYMENT_ID=test-instance MASTER_HOST=127.0.0.1 MASTER_PORT=8000 bash start.sh"
    echo "  - Network connectivity: check firewall and localhost routing"
    echo ""
    exit 1
fi
