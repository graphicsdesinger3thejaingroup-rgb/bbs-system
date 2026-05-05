# 🚀 Deploying to Vercel

Bhai, ekta step-by-step guide. **5 minute lagbe.**

---

## Method 1 — GitHub + Vercel Dashboard (easiest, recommended)

### Step 1: Push to GitHub

```bash
cd bbs_app
git init
git add .
git commit -m "Initial commit"
```

GitHub e ekta notun **empty repo** banao (https://github.com/new). Tarpor:

```bash
git remote add origin https://github.com/YOUR-USERNAME/bbs-app.git
git branch -M main
git push -u origin main
```

### Step 2: Import to Vercel

1. https://vercel.com e jao → Sign up / login (use GitHub account for easiest)
2. Click **"Add New..."** → **"Project"**
3. **"Import"** the GitHub repo you just made
4. Configuration screen e dekhbe — **kichu change korte hobe na**:
   - Framework Preset: `Other`
   - Root Directory: `./`
   - Build Command: *(leave blank)*
   - Output Directory: *(leave blank)*
   - Install Command: *(leave blank)*
5. Click **"Deploy"**

~60 second wait koro. Tarpor tomar app live!

URL hobe rokom: `https://bbs-app-yourname.vercel.app`

### Step 3: Custom domain (optional)

Vercel dashboard → Settings → Domains → Add domain. Free `*.vercel.app` works as-is.

---

## Method 2 — Vercel CLI (faster for repeat deploys)

### Step 1: Install Vercel CLI (one time only)

```bash
npm install -g vercel
```

(Need Node.js installed — https://nodejs.org)

### Step 2: Login

```bash
vercel login
```

Email diye OTP ashbe, click korle login hoye jabe.

### Step 3: Deploy

```bash
cd bbs_app
vercel
```

Eirokom prompts ashbe — sob default chap (Enter):
```
? Set up and deploy "~/bbs_app"? [Y/n]  y
? Which scope?                          (your account)
? Link to existing project?             n
? What's your project's name?           bbs-app
? In which directory is your code?      ./
? Want to modify settings?              n
```

~30 second build hobe. Then preview URL ashbe.

### Step 4: Promote to production

```bash
vercel --prod
```

**Production URL** taile pacche — eta tumi clients ke share korte parba.

---

## ✅ Verify deployment

URL e jao, ar ekta beam calculation try koro:

1. Open the URL → **BBS Automation** dashboard load hoye gele ✓
2. Click **📄 Project Info** → fill in 3 fields
3. Default beam values keep koro → click **Calculate**
4. Verify ✓ Engineering Verified banner ashche
5. Click **PDF** button — 5-page professional report download hobe

---

## 🔧 Troubleshooting

### Build fails with "Module not found: services.calculator"

Make sure `backend/` folder is in your repo. Check `.vercelignore` doesn't accidentally exclude it (it shouldn't — only excludes tests/logs/cache).

### "Function exceeded maximum execution time of 10s"

Free tier e 10-second limit. Tomar BBS gen 200ms te kaaj kore — eta hocche na. Jodi hoy, check Vercel function logs (dashboard → Functions tab → click on the function).

### PDF download e "404" or empty file

Browser network tab e dekho — `/download-pdf` endpoint hit hocche kina. Jodi `/api/download-pdf` jay (wrong path), tomar `vercel.json` ek-bar reverify koro — should be exactly as shipped.

### Cold start slow first time

First request ~1-2 seconds (Vercel spinning up the Python runtime). Subsequent requests <100ms. Eta normal serverless behavior. Free tier e koto kichu cold-warm cycle hoy.

---

## 💰 Cost

**Free tier covers:**
- 100 GB bandwidth / month
- 100 hours of function execution / month (~360,000 calls @ 1s each)
- Unlimited static page views

For a typical BBS app used by a small engineering firm — **free tier ekdom enough**.

---

## 🔄 Updating after deploy

Code change kore push korle Vercel automatically redeploy korbe (if you used GitHub method).

```bash
git add .
git commit -m "Update X"
git push
```

Vercel dashboard e "Deployments" tab khulo — within 1 minute notun version live hoye jabe.

For CLI method: just run `vercel --prod` again.
