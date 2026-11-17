# Deploying Frontend to Cloudflare Pages / Vercel

If you prefer decoupling the React frontend from the FastAPI backend (e.g., hosting the frontend on Cloudflare Pages or Vercel edge CDN, and pointing to a Cloud Run or Render backend), follow these steps.

---

## 1. Cloudflare Pages Deployment
1. Connect your GitHub repository to Cloudflare Pages.
2. In **Build Settings**:
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build` (or `npm run build:demo` for standalone demo)
   - **Build Output Directory**: `frontend/dist`
   - **Root Directory**: `frontend`
3. In **Environment Variables**:
   - `VITE_API_URL`: `https://your-backend-service.onrender.com/api` (leave unset if using built-in demo mode)

---

## 2. Vercel Deployment
1. Import repository on Vercel.
2. Select **Root Directory**: `frontend`
3. Set **Framework Preset**: `Vite`
4. In **Environment Variables**:
   - `VITE_API_URL`: `https://your-backend-service.onrender.com/api`
5. Click **Deploy**.
