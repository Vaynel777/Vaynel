# Deployment Guide - OpenClaw Mission Control

**Status:** Ready for Deployment
**Version:** 4.1.0
**Target:** Vercel / Self-hosted

---

## Option 1: Vercel Deployment (Recommended)

### Prerequisites
- Vercel account (free tier available)
- Git repository (already set up)
- Vercel CLI or GitHub integration

### Steps

#### 1. Connect GitHub Repository
```bash
# Push to GitHub first
git remote add origin https://github.com/YOUR_USERNAME/openclaw-mission-control.git
git branch -M main
git push -u origin main
```

#### 2. Deploy via Vercel Dashboard
1. Go to https://vercel.com/new
2. Import the GitHub repository
3. Select "Other" for Framework
4. Deploy!

#### 3. Or Deploy via CLI
```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy to production
vercel --prod
```

### Expected URL
```
https://openclaw-mission-control.vercel.app
```

---

## Option 2: Self-Hosted Deployment

### Prerequisites
- Python 3.9+
- uvicorn installed
- Port 8000 available

### Quick Start
```bash
cd /Users/alexren/.openclaw/workspace/mission_control_master

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn api.index:app --host 0.0.0.0 --port 8000 --reload
```

Access at: `http://localhost:8000`

### With Gunicorn (Production)
```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:8000 api.index:app
```

---

## Option 3: Docker Deployment

### Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run
```bash
docker build -t openclaw-mission-control .
docker run -p 8000:8000 openclaw-mission-control
```

### Deploy to Docker Hub
```bash
docker tag openclaw-mission-control YOUR_USERNAME/openclaw-mission-control:latest
docker push YOUR_USERNAME/openclaw-mission-control:latest
```

---

## Option 4: Railway / Fly.io Deployment

### Railway
```bash
# Install Railway CLI
brew install railway

# Login
railway login

# Deploy
railway up
```

### Fly.io
```bash
# Install Fly CLI
brew install flyctl

# Deploy
fly deploy
```

---

## Integration with Admin Dashboards

Once deployed, configure each instance to report to the Master Dashboard:

```bash
# On each instance (neo-toshiba, mba2, agent3)
export DEPLOYMENT_ID="neo-toshiba"
export MASTER_HOST="openclaw-mission-control.vercel.app"  # Or your domain
export MASTER_PORT="443"  # Or 80 for HTTP

cd admin_dashboard
bash start.sh
```

### Metric Sync
Add to Master Dashboard crontab:
```bash
# Every 5 minutes, sync metrics from each instance
*/5 * * * * curl -s http://192.168.1.33:8001/metrics | \
  curl -X POST -d @- -H "Content-Type: application/json" \
  "https://openclaw-mission-control.vercel.app/api/metrics/neo-toshiba"
```

---

## Testing

### Local Test
```bash
# Start server
python -m uvicorn api.index:app --host 0.0.0.0 --port 8000

# In another terminal
curl http://localhost:8000/health
curl http://localhost:8000/api/dashboard | jq .
```

### Remote Test
```bash
# Replace with your Vercel URL
curl https://openclaw-mission-control.vercel.app/health
curl https://openclaw-mission-control.vercel.app/api/dashboard | jq .
```

---

## Environment Variables

For production deployments, set these if needed:

```bash
DEPLOYMENT_ID=neo-toshiba
MASTER_HOST=openclaw-mission-control.vercel.app
MASTER_PORT=443
PYTHONUNBUFFERED=1
```

---

## Monitoring

### Health Checks
- **Local:** `curl http://localhost:8000/health`
- **Remote:** `curl https://your-domain.vercel.app/health`

### View Logs
- **Vercel:** Dashboard → Deployments → Logs
- **Self-hosted:** Check stdout or `tail -f logs/app.log`

### Check Metrics
```bash
curl https://your-domain.vercel.app/api/dashboard | jq .stats
```

---

## Troubleshooting

### "Port 8000 already in use"
```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>
```

### "Cannot find module 'fastapi'"
```bash
# Make sure dependencies are installed
pip install -r requirements.txt
```

### "HTML file not found"
```bash
# Ensure index.html is in the root directory
ls -la index.html
```

### Vercel Deploy Failed
1. Check that `vercel.json` is valid JSON
2. Ensure all Python files are present
3. Check build output for errors
4. Verify Python version compatibility (3.9+)

---

## Performance Tips

1. **Enable caching** (Vercel automatically does this)
2. **Use CDN** for static files
3. **Minimize database queries** (currently using in-memory)
4. **Scale horizontally** with load balancer if needed

---

## Next Steps

1. ✅ Deploy Master Dashboard to Vercel/self-hosted
2. ✅ Deploy Admin Dashboard to each instance
3. ✅ Set up metric sync cron jobs
4. ✅ Configure alert notifications
5. ⏳ Monitor and iterate

---

## Support

For issues or questions:
- Check logs: `tail -f logs/app.log`
- Review API docs: `/docs` (Swagger UI)
- Read README: `README.md`

---

**Deploy with confidence! 🚀**
