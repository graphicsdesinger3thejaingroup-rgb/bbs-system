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

### Option 4 — Vercel / Netlify (frontend only) + Backend on a Python host
- Deploy `frontend/` to Vercel or Netlify
- Update the `API_BASE` constant in `app.js` to point to the deployed Flask URL
- Enable CORS (already enabled in `app.py` via `flask_cors`)

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
