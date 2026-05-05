# 🏗️ BBS Automation — Bar Bending Schedule Generator

Production-ready web app to automate Bar Bending Schedules per **IS 456:2000** & **IS 2502:1963**.

> Input structural details → validate → calculate → preview BBS → download Excel & PDF.

---

## ✨ Features

- 🔁 Beam / Column / Slab toggle
- ✅ Strict input validation (missing fields, mm-unit sanity check, geometric sanity)
- 📐 Calculation engine: cover deduction · hook length (90°/135°) · bend allowance · stirrup formula · `W = d²/162 × L`
- 📋 Auto-generated structured BBS table (Bar mark · Dia · Shape · Cutting len · Qty · Total len · Weight)
- 🚚 Final order engine — groups by diameter, applies 5% wastage, converts to 12 m rods
- 📊 Excel export (2 sheets: `BBS_Data` + `Final_Order`)
- 📄 Professional PDF report (ReportLab)
- 🪵 Rotating log files in `backend/logs/app.log`
- 🎨 Clean Tailwind dashboard UI

---

## 📁 Project Structure

```
bbs_app/
├── backend/
│   ├── app.py                       # Flask entry-point
│   ├── requirements.txt
│   ├── services/
│   │   ├── calculator.py            # IS 456/2502 calculation engine
│   │   ├── validator.py             # Input validation
│   │   ├── excel_generator.py       # OpenPyXL report
│   │   └── pdf_generator.py         # ReportLab report
│   ├── utils/
│   │   └── logger.py                # Rotating logger
│   ├── routes/                      # (reserved for future blueprints)
│   ├── logs/                        # app.log lives here
│   └── generated/                   # generated .xlsx and .pdf files
└── frontend/
    ├── index.html                   # Tailwind dashboard
    └── app.js                       # Form, validation, fetch calls
```

---

## 🚀 Run Locally

### Prerequisites
- Python **3.9+**
- pip

### 1. Install dependencies

```bash
cd bbs_app/backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start the server

```bash
python app.py
```

Server will start on **http://localhost:5000**.

### 3. Open the app

Open a browser and visit **http://localhost:5000**.
Flask serves both the API and the frontend from the same origin — no CORS issues.

---

## 🔌 API Reference

| Method | Endpoint           | Description                                        |
|--------|--------------------|----------------------------------------------------|
| GET    | `/`                | Serves frontend (`index.html`)                     |
| GET    | `/health`          | Health check `{"status": "ok"}`                    |
| POST   | `/calculate`       | Validate + compute BBS, returns JSON               |
| POST   | `/download-excel`  | Returns `.xlsx` BBS report                         |
| POST   | `/download-pdf`    | Returns `.pdf` BBS report                          |

### Sample request body

```json
{
  "element_type": "beam",
  "width": 300,
  "depth": 450,
  "length": 6000,
  "cover": 25,
  "main_bar_dia": 16,
  "main_bar_qty": 4,
  "stirrup_dia": 8,
  "stirrup_spacing": 150,
  "hook_type": 135,
  "lap_length": 0
}
```

### Sample successful `/calculate` response

```json
{
  "success": true,
  "data": {
    "bbs": [
      {"bar_mark":"M1","dia_mm":16,"cutting_length_mm":6270,"quantity":4,"total_weight_kg":39.63, "...": "..."},
      {"bar_mark":"S1","dia_mm":8,"cutting_length_mm":1332,"quantity":40,"total_weight_kg":21.05, "...": "..."}
    ],
    "final_order": [
      {"dia_mm":8,"order_length_m":55.94,"rods_12m_required":5},
      {"dia_mm":16,"order_length_m":26.33,"rods_12m_required":3}
    ],
    "summary": {
      "total_bars":44,"total_length_m":78.36,
      "total_weight_kg_net":60.68,"total_weight_kg_with_wastage":63.71
    }
  }
}
```

### Validation error response (`400`)

```json
{
  "success": false,
  "errors": [
    "'width' = 30.0 is outside valid mm range [50, 5000]. Did you submit in cm/m instead of mm?"
  ]
}
```

---

## 🧮 Formulas Used (IS 456 / IS 2502)

| Quantity              | Formula                                                |
|-----------------------|--------------------------------------------------------|
| Hook length (90°)     | `9 × d`                                                |
| Hook length (135°)    | `10 × d`                                               |
| Bend deduction (90°)  | `2 × d` per bend                                       |
| Bend deduction (135°) | `3 × d` per bend                                       |
| Main bar length       | `L − 2·cover + 2·hook + lap`                           |
| Stirrup cutting len   | `2(a + b) + 2·hook − n_bend × deduction`               |
| Unit weight           | `d² / 162`  (kg/m for d in mm)                         |
| Order qty             | `net_length × 1.05` → `ceil( order_len / 12 m )` rods  |

---

## 🌐 Deployment

### Option 1 — Single-server (Gunicorn)

```bash
cd bbs_app/backend
pip install -r requirements.txt
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Place behind nginx if you want HTTPS. Sample nginx config:

```
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Option 2 — Docker

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/  ./backend/
COPY frontend/ ./frontend/
WORKDIR /app/backend
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t bbs-app .
docker run -p 5000:5000 bbs-app
```

### Option 3 — Render / Railway / Fly.io

- **Build command:** `pip install -r backend/requirements.txt`
- **Start command:** `cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT app:app`
- Frontend is served by Flask, no separate hosting needed.

### Option 4 — Vercel (full-stack, recommended free option)

Deploys frontend + Python backend together as serverless functions.
**Zero config changes needed** — the project already includes `vercel.json`,
`/api/index.py`, and `/requirements.txt` at the root.

#### A. Deploy via GitHub (easiest)

1. Push your project to a GitHub repo.
2. Go to <https://vercel.com> → "Add New Project" → import the repo.
3. Vercel auto-detects:
   - Framework: **Other**
   - Build command: *(leave blank)*
   - Output directory: *(leave blank)*
   - Install command: *(leave blank — Vercel reads `requirements.txt` itself)*
4. Click **Deploy**. ~60 seconds later, you get a `*.vercel.app` URL.

#### B. Deploy via CLI

```bash
npm i -g vercel              # one-time
cd bbs_app
vercel                       # follow the prompts
vercel --prod                # promote to production URL
```

#### How it works on Vercel

- `frontend/index.html` and `frontend/app.js` → served as static files
- `/calculate`, `/download-excel`, `/download-pdf`, `/health` → routed to
  `api/index.py`, which imports the Flask `app` object and runs it as a
  serverless function (cold start ~1 s, warm <100 ms).
- `app.py` auto-detects the `VERCEL` env-var and writes generated PDFs/Excel
  to `/tmp` (the only writable path on Vercel) instead of `backend/generated`.
- Logging stays in stdout (visible in the Vercel dashboard's Functions tab).

#### Vercel-specific notes

- **Free tier execution limit:** 10 s per request — our generators take ~200 ms, so plenty of headroom.
- **Function size:** ~10 MB (well under the 50 MB limit). `pandas` was dropped from `requirements.txt` since it wasn't actually used.
- **No database / no persistence:** generated PDFs live in `/tmp` only for the duration of one request — they're streamed back to the user immediately. Nothing is stored long-term.
- **Custom domain:** add it in the Vercel dashboard under Settings → Domains.

---

## 🧪 Quick Test (no UI)

```bash
curl -X POST http://localhost:5000/calculate \
  -H "Content-Type: application/json" \
  -d '{"element_type":"beam","width":300,"depth":450,"length":6000,"cover":25,
       "main_bar_dia":16,"main_bar_qty":4,"stirrup_dia":8,"stirrup_spacing":150,
       "hook_type":135,"lap_length":0}'
```

---

## ⚠️ Disclaimer

This tool follows standard IS code practice but the generated BBS must always be **verified against site drawings and reviewed by a licensed structural engineer** before steel fabrication.
