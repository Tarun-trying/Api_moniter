# PulseMonitor

A simple, professional API and website monitoring dashboard. Add URLs, auto-monitor them, see uptime, response times, and incidents — all in a clean developer-focused UI.

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Frontend   | React + Vite + Tailwind CSS v4    |
| Charts     | Recharts                          |
| Routing    | React Router v6                   |
| Backend    | FastAPI (Python)                  |
| Database   | SQLite via SQLAlchemy             |
| HTTP checks| httpx (async)                     |
| Scheduler  | APScheduler                       |

---

## Project Structure

```
PulseMonitor/
├── backend/
│   ├── main.py              # FastAPI app entry
│   ├── database.py          # SQLAlchemy engine
│   ├── scheduler.py         # APScheduler background worker
│   ├── api/                 # Route handlers
│   ├── services/            # Business logic + monitoring engine
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── api/client.js    # Centralized API layer
    │   ├── components/      # Reusable UI components
    │   ├── pages/           # Route-level page components
    │   └── utils.js         # Shared formatting utilities
    └── vite.config.js       # Proxies /api → http://localhost:8000
```

---

## Quick Start

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Python < 3.12 on Windows without MSVC: install greenlet binary first
pip install greenlet --only-binary :all:

# Install dependencies
pip install -r requirements.txt

# Start the backend
uvicorn main:app --reload
```

The API will be available at **http://localhost:8000**  
Interactive docs: **http://localhost:8000/docs**

### 2. Frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The dashboard will open at **http://localhost:5173**

---

## How It Works

1. **Add a monitor** via the dashboard → a FastAPI endpoint creates a DB record and immediately schedules a background job.
2. **APScheduler** runs each monitor's HTTP check at its configured interval.
3. Each check result is saved to SQLite and the monitor's cached status is updated.
4. After **3 consecutive failures**, an incident is automatically created.
5. After **2 consecutive successes**, the incident is automatically resolved.
6. The frontend polls the API every 15 seconds and displays live status.

---

## API Endpoints

| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
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
| GET    | /api/health                       | Health check             |

---

## Security

- SSRF protection: all URLs are validated against private IP ranges before each check
- Private/loopback addresses, link-local (169.254.x.x), cloud metadata endpoints are blocked
- No shell commands are ever executed based on user input
- SQLAlchemy parameterized queries prevent SQL injection

---

## Feature Roadmap

- [ ] Email / Slack / webhook notifications
- [ ] Dark mode
- [ ] Response time alerts (threshold-based)
- [ ] Status page (public facing)
- [ ] Multi-user authentication
- [ ] Custom headers for authenticated endpoints
