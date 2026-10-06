# PulseMonitor

A professional API and website monitoring dashboard. Add URLs, auto-monitor them, see uptime, response times, and incidents — all in a clean developer-focused UI.

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Frontend   | React + Vite + Tailwind CSS v4    |
| Charts     | Recharts                          |
| Routing    | React Router v7                   |
| Backend    | FastAPI (Python)                  |
| Database   | MongoDB Atlas (motor async driver)|
| HTTP checks| httpx (async)                     |
| Scheduler  | asyncio tasks                     |

---

## Project Structure

```
PulseMonitor/
├── backend/
│   ├── main.py              # FastAPI app entry
│   ├── database.py          # MongoDB Atlas connection
│   ├── store.py             # Data access layer (MongoDB)
│   ├── scheduler.py         # Async background monitor workers
│   ├── api/                 # Route handlers
│   ├── services/            # Business logic + monitoring engine
│   ├── schemas/             # Pydantic request/response schemas
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example         # Copy to .env and fill in secrets
│   └── .env                 # ⚠️ Never commit — gitignored
│
├── frontend/
│   ├── src/
│   │   ├── api/client.js    # Centralized API layer
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route-level page components
│   │   └── utils.js         # Shared formatting utilities
│   ├── Dockerfile
│   ├── nginx.conf           # SPA routing + gzip
│   ├── vite.config.js
│   └── .env.example
│
├── docker-compose.yml       # Full-stack local/VPS deploy
└── render.yaml              # One-click Render.com deploy
```

---

## Local Development

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — add your MONGODB_URI

# Start the backend
uvicorn main:app --reload
```

API: **http://localhost:8000** | Docs: **http://localhost:8000/docs**

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: **http://localhost:5173**

---

## Deployment

### Option A — Render.com (Free, Recommended)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your repo — Render will detect `render.yaml` automatically
4. In the Render dashboard, set these environment variables:
   - **Backend service**: `MONGODB_URI`, `ALLOWED_ORIGINS` (your frontend URL)
   - **Frontend service**: `VITE_API_URL` (your backend URL)
5. Click **Deploy**

### Option B — Docker Compose (VPS / Self-hosted)

```bash
# Clone the repo on your server
git clone <your-repo-url>
cd APIMonitor

# Set up backend secrets
cp backend/.env.example backend/.env
# Edit backend/.env with your real MONGODB_URI

# Build and start everything
docker-compose up -d --build
```

Frontend at **http://your-server-ip** | Backend at **http://your-server-ip:8000**

### Option C — Railway.app

1. Push to GitHub
2. New Railway project → Deploy from GitHub
3. Add two services: point one to `backend/`, one to `frontend/`
4. Set env vars in Railway dashboard (same as Render above)

---

## Environment Variables

### Backend (`backend/.env`)

| Variable          | Required | Description                              |
|-------------------|----------|------------------------------------------|
| `MONGODB_URI`     | ✅ Yes   | MongoDB Atlas connection string          |
| `MONGODB_DB`      | No       | Database name (default: `pulsemonitor`)  |
| `ALLOWED_ORIGINS` | No       | Comma-separated CORS origins             |
| `PORT`            | No       | Server port (default: `8000`)            |

### Frontend (`frontend/.env`)

| Variable       | Required | Description                              |
|----------------|----------|------------------------------------------|
| `VITE_API_URL` | Prod only| Backend URL (e.g. `https://api.myapp.com`). Leave empty for local dev. |

---

## How It Works

1. **Add a monitor** via the dashboard → stored in MongoDB, immediately scheduled
2. **Async workers** run each monitor's HTTP check at its configured interval
3. Each result is saved to MongoDB and the monitor's cached status is updated
4. After **3 consecutive failures**, an incident is automatically created
5. After **2 consecutive successes**, the incident is resolved
6. The frontend polls the API every 15 seconds and shows live status

---

## API Endpoints

| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| GET    | /api/health                       | Health check + uptime    |
| GET    | /api/monitors                     | List all monitors        |
| POST   | /api/monitors                     | Create a monitor         |
| GET    | /api/monitors/{id}                | Get a monitor            |
| PUT    | /api/monitors/{id}                | Update a monitor         |
| DELETE | /api/monitors/{id}                | Delete a monitor         |
| POST   | /api/monitors/{id}/check          | Trigger immediate check  |
| GET    | /api/monitors/{id}/checks         | Check history            |
| GET    | /api/monitors/{id}/uptime         | Uptime percentages       |
| GET    | /api/monitors/{id}/chart          | Chart data               |
| GET    | /api/monitors/{id}/incidents      | Monitor incidents        |
| GET    | /api/incidents                    | All incidents            |
| GET    | /api/analytics                    | Aggregate analytics      |

---

## Security

- SSRF protection: all URLs validated against private IP ranges before each check
- Private/loopback addresses, link-local (169.254.x.x), cloud metadata endpoints are blocked
- No shell commands executed based on user input
- MongoDB parameterized queries prevent injection attacks
- `.env` is gitignored — secrets never committed

---

## Feature Roadmap

- [ ] Email / Slack / webhook notifications
- [ ] Response time threshold alerts
- [ ] Status page (public facing)
- [ ] Multi-user authentication
- [ ] Custom headers for authenticated endpoints
