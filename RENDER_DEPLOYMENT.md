# Render.com Deployment - Quick Start Guide

## Why Render?
- ✅ Deploy in 3 minutes
- ✅ Free tier (750 hours/month)
- ✅ Automatic HTTPS
- ✅ GitHub auto-deploy
- ✅ Very reliable for demos

---

## Step 1: Push to GitHub (Already Done ✅)

Your code is already on GitHub at:
`https://github.com/lmaoitsjerry/multitenant-ai-platform`

---

## Step 2: Deploy to Render (2 minutes)

### Go to Render Dashboard

1. **Sign up/Login**: https://render.com
   - Use your GitHub account (easiest)

2. **Create New Web Service**:
   - Click "New +" → "Web Service"
   
3. **Connect Repository**:
   - Select: `lmaoitsjerry/multitenant-ai-platform`
   - Click "Connect"

4. **Configure Service** (Render auto-detects most settings):
   - **Name**: `multitenant-ai-platform`
   - **Region**: Oregon (US West) or closest to you
   - **Branch**: `main`
   - **Runtime**: Docker ✅ (auto-detected from Dockerfile)
   - **Plan**: Free

5. **Environment Variables** - Add these:
   ```
   CLIENT_ID=example
   PORT=8080
   ```

6. **Click "Create Web Service"**

---

## Step 3: Wait for Deployment (2-3 minutes)

Render will:
1. Clone your repo
2. Build Docker image
3. Deploy container
4. Give you a URL like: `https://multitenant-ai-platform.onrender.com`

Watch the logs in real-time!

---

## Step 4: Test Your Deployment

Once deployed, test these endpoints:

```bash
# Health check
curl https://multitenant-ai-platform.onrender.com/health

# Client info
curl https://multitenant-ai-platform.onrender.com/api/v1/client/info

# Destinations
curl https://multitenant-ai-platform.onrender.com/api/v1/destinations
```

Expected response for health:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-06T18:57:04.000Z"
}
```

---

## Step 5: Connect to Lovable

In your Lovable project:

1. **Add Environment Variable**:
   ```
   VITE_API_URL=https://multitenant-ai-platform.onrender.com
   ```

2. **Deploy your frontend**

3. **Test the connection!**

---

## Important Notes

### Free Tier Limitations
- ⚠️ **Spins down after 15 min of inactivity**
- ⚠️ **First request after spin-down takes 30-60 seconds**
- ✅ Perfect for demos - just wake it up before presenting!

### Keep Service Awake
If you want it always on, you can:
1. Upgrade to paid plan ($7/month)
2. Use a service like UptimeRobot to ping it every 5 minutes

---

## Troubleshooting

### Build Fails
- Check Render logs in dashboard
- Ensure Dockerfile is correct
- Verify requirements.txt has all dependencies

### Service Won't Start
- Check environment variables in Render dashboard
- Look at deployment logs
- Ensure PORT is set to 8080

### CORS Errors
- Already configured in main.py: `https://*.onrender.com`
- Check your Lovable domain is accessible

---

## Cost: 100% FREE 🎉

**Free Tier Includes:**
- 750 hours/month
- 512MB RAM
- Automatic SSL
- GitHub integration
- Build minutes included

**Perfect for demos and testing!**

---

## Auto-Deploy Setup

Render automatically deploys when you push to GitHub:

```bash
# Make changes
git add .
git commit -m "Update feature"
git push

# Render auto-deploys in ~2 minutes!
```

---

## Deployment Checklist

- [ ] Sign up at render.com
- [ ] Connect GitHub repository
- [ ] Configure service (Docker)
- [ ] Add environment variables (CLIENT_ID, PORT)
- [ ] Deploy service
- [ ] Get service URL
- [ ] Test endpoints
- [ ] Add URL to Lovable
- [ ] Test end-to-end
- [ ] 🎉 Demo ready!

**Total Time: ~5 minutes**
