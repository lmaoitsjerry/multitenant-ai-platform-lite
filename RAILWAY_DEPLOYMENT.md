# Railway Deployment - Quick Start Guide

## Why Railway?
- ✅ Deploy in 5 minutes
- ✅ Free tier (no credit card needed)
- ✅ Automatic HTTPS
- ✅ GitHub integration
- ✅ Perfect for demos

---

## Step 1: Push to GitHub

Make sure your code is on GitHub (you've already done this):
```powershell
cd c:\Users\jerry\ZAFS1_REVERSE\zorah_afs_platform1\multitenant
git push -u origin main
```

---

## Step 2: Deploy to Railway

### Option A: One-Click Deploy (Easiest)

1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub
5. Select: `lmaoitsjerry/multitenant-ai-platform`
6. Railway will auto-detect the Dockerfile and deploy!

### Option B: Railway CLI

```powershell
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize
railway init

# Deploy
railway up
```

---

## Step 3: Configure Environment Variables

After deployment starts, add these in Railway dashboard:

1. Go to your project → Variables tab
2. Add:
   ```
   CLIENT_ID=example
   PORT=8080
   ```

3. Optional (add when ready):
   ```
   OPENAI_API_KEY=your_key
   SUPABASE_URL=your_url
   SUPABASE_KEY=your_key
   ```

---

## Step 4: Get Your URL

Railway will give you a URL like:
```
https://multitenant-ai-platform-production.up.railway.app
```

Test it:
```powershell
curl https://your-railway-url/health
curl https://your-railway-url/api/v1/client/info
```

---

## Step 5: Connect to Lovable

In your Lovable frontend:

1. Add environment variable:
   ```
   VITE_API_URL=https://your-railway-url
   ```

2. Deploy your frontend

3. Test the connection!

---

## Deployment Time: ~5 minutes ⚡

1. Push to GitHub: 1 min
2. Connect Railway: 1 min  
3. Auto-deploy: 2-3 min
4. Configure env vars: 1 min

**Total: 5 minutes!**

---

## Troubleshooting

### Build fails
- Check Railway logs in dashboard
- Ensure Dockerfile is in root directory
- Verify all dependencies in requirements.txt

### Service not starting
- Check environment variables are set
- Look at deployment logs
- Ensure PORT=8080 is set

### CORS errors
- Railway URL is automatically added to CORS in main.py
- Check your Lovable domain is in the allowlist

---

## Cost

**Free Tier Includes:**
- 500 hours/month
- 512MB RAM
- 1GB storage
- Perfect for demos and testing!

**No credit card required for free tier!**

---

## Next Steps

1. ✅ Deploy to Railway (5 min)
2. ✅ Get Railway URL
3. ✅ Add URL to Lovable
4. ✅ Test end-to-end
5. 🎉 Demo ready!
