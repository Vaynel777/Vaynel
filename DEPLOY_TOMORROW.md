# 🚀 Deploy to Vercel Tomorrow - Step-by-Step

**Estimated Time:** 10 minutes
**Cost:** Free
**Result:** Live shareable dashboard URL

---

## Prerequisites (Do Tonight)

✅ Already done:
- [ ] Code is in `/Users/alexren/.openclaw/workspace/mission_control_master`
- [ ] Git repository initialized (`git init` ✅)
- [ ] All files committed (`git commit` ✅)
- [ ] `vercel.json` configured ✅
- [ ] `package.json` created ✅
- [ ] `serve_test.py` ready ✅

---

## Step 1: Create GitHub Repository (5 min)

### 1.1 Create repo on GitHub.com
1. Go to https://github.com/new
2. Name: `openclaw-mission-control`
3. Description: "OpenClaw AaaS Master & Admin Dashboards"
4. Make it **Public** (required for free deployment)
5. Click **Create Repository**

### 1.2 Push code to GitHub
```bash
cd /Users/alexren/.openclaw/workspace/mission_control_master

# Add origin
git remote add origin https://github.com/YOUR_USERNAME/openclaw-mission-control.git

# Rename branch (if needed)
git branch -M main

# Push
git push -u origin main

# Verify
git log --oneline | head -5
```

---

## Step 2: Deploy to Vercel (3 min)

### Option A: Via GitHub (Easiest)
1. Go to https://vercel.com/new
2. Click **"Import Git Repository"**
3. Paste: `https://github.com/YOUR_USERNAME/openclaw-mission-control`
4. Click **Import**
5. Click **Deploy**
6. Wait for build (1-2 min)
7. Copy your live URL

### Option B: Via CLI
```bash
# Install Vercel CLI (if not already installed)
npm install -g vercel

# Login
vercel login

# Deploy
cd /Users/alexren/.openclaw/workspace/mission_control_master
vercel --prod

# Copy URL from output
```

---

## Step 3: Test Live Dashboard (2 min)

```bash
# Replace with your actual URL
LIVE_URL="https://openclaw-mission-control.vercel.app"

# Test health
curl "$LIVE_URL/health"

# Test API
curl "$LIVE_URL/api/dashboard" | jq .stats

# View in browser
open "$LIVE_URL"
```

**Expected:** Same dashboard as localhost:8000

---

## Step 4: Update Admin Dashboards (Optional)

If deploying admin dashboards to instances:

```bash
# Update MASTER_HOST in admin_dashboard config
export MASTER_HOST="your-vercel-url.vercel.app"
export MASTER_PORT="443"

# Deploy to neo-toshiba
bash admin_dashboard/deploy.sh neo-toshiba 192.168.1.33 "$MASTER_HOST" "$MASTER_PORT"

# Deploy to mba2
bash admin_dashboard/deploy.sh mba2 192.168.1.56 "$MASTER_HOST" "$MASTER_PORT"
```

---

## Step 5: Share Link

**Copy this URL and send:**
```
https://openclaw-mission-control.vercel.app
```

**Access from anywhere:**
- Desktop: Click link
- Mobile: Works on iPhone/Android
- Public: Anyone with link can view (no auth)

---

## Troubleshooting

### "Build failed"
Check Vercel dashboard → Deployments → Build logs
Common issues:
- Missing Python dependencies (check requirements.txt)
- Wrong file paths
- Syntax errors in Python files

**Solution:** Fix and re-push to GitHub
```bash
git add .
git commit -m "Fix build issue"
git push
# Vercel auto-redeploys
```

### "Homepage shows 404"
- Make sure `index.html` is in root directory
- Check Vercel is serving static files correctly
- Clear browser cache (Cmd+Shift+Delete)

### "API endpoints not working"
- Check `api/index.py` syntax
- Verify function names match routes
- Check Vercel logs for Python errors

---

## What to Expect

**Build Time:** 1-2 minutes
**Live URL Format:** `https://openclaw-mission-control-<random>.vercel.app`
**Dashboard:** Identical to localhost:8000
**Demo Data:** 3 deployments, 2 critical events

---

## Commands Cheat Sheet

```bash
# Check git status
git status

# Add all changes
git add .

# Commit
git commit -m "Ready for production"

# Push to GitHub
git push

# Check Vercel status
vercel status

# View recent deployments
vercel deployments

# Open Vercel dashboard
vercel dashboard
```

---

## Next: After Live URL

Once you have the live URL:

1. **Update Memory**
   - Add to `memory/aaas.md`
   - Note: "Phase 4 Master Dashboard live at: <url>"

2. **Test Endpoints**
   ```bash
   curl https://your-url/health
   curl https://your-url/api/dashboard | jq .
   ```

3. **Configure Admin Dashboards**
   - Update `MASTER_HOST` to live URL
   - Deploy to each instance

4. **Set Up Metric Sync**
   - Add cron job to sync every 5 minutes

---

## Reference

- **Vercel Docs:** https://vercel.com/docs
- **FastAPI:** https://fastapi.tiangolo.com/
- **Git Guide:** https://git-scm.com/docs

---

**⏱️ Total time: ~10 minutes**
**Result: Live, shareable dashboard URL**
**Cost: $0 (free tier)**

Let's go! 🚀

