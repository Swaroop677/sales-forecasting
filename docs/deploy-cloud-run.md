# Google Cloud Run Deployment Guide

This guide walks you through deploying **Forecastly** to Google Cloud Run under the **Free Tier / Low-Cost** profile.

---

## 1. Prerequisites
- Google Cloud Project with billing enabled (Cloud Run has a generous free tier of 2M requests/month).
- Google Cloud CLI (`gcloud`) installed and authenticated:
  ```bash
  gcloud auth login
  gcloud config set project YOUR_PROJECT_ID
  ```

---

## 2. Recommended Cloud Run Architecture (Free-Tier Safe)
- **Region**: `us-central1` (eligible for Google Cloud Free Tier)
- **Memory**: `2Gi` (strictly adheres to the <= 2 GB RAM constraint)
- **CPU**: `1` (CPU allocated only during request processing)
- **Max Instances**: `1` (prevents unexpected burst cost spikes)
- **Min Instances**: `0` (scales to zero when idle, incurring zero cost)
- **Concurrency**: `40`

---

## 3. Deployment Commands

### Step A: Build & Deploy via Cloud Build
```bash
gcloud run deploy forecastly \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --max-instances 1 \
  --min-instances 0 \
  --port 8080 \
  --set-env-vars "OMP_NUM_THREADS=1,OPENBLAS_NUM_THREADS=1,MAX_UPLOAD_SIZE_MB=10,MAX_UPLOAD_ROWS=200000"
```

### Step B: (Optional) Adding Gemini API Key
To securely attach your Google AI Studio API key via Cloud Secret Manager:
```bash
# 1. Store secret
echo -n "AIzaSy..." | gcloud secrets create gemini-api-key --data-file=-

# 2. Grant Cloud Run access and update service
gcloud run services update forecastly \
  --region us-central1 \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest"
```

---

## 4. Setting Up Budget Alerts
To avoid billing surprises, set a $5 or $10 monthly budget alert:
```bash
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="Forecastly Safety Budget" \
  --budget-amount=10.00USD \
  --threshold-rule=percent=0.8 \
  --threshold-rule=percent=1.0
```

---

## 5. Verification
Once deployed, Cloud Run will print the live HTTPS service URL:
```bash
curl https://forecastly-xxxxx-uc.a.run.app/health
# Response: {"status":"healthy","app_name":"Forecastly","version":"1.0.0"}
```
Open the URL in any browser to experience the full application.
