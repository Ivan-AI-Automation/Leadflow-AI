# LeadFlow AI Frontend

This is the Streamlit frontend for LeadFlow AI.

The frontend is built as a clean internal business tool. It is not a marketing site. The first
screen is the product workflow: login, dashboard, lead upload, lead workspace, email drafts, and
exports.

## Main Pages

- Login and registration
- Dashboard
- Upload Leads
- Imports
- Leads
- Lead Detail
- Email Drafts
- Export Center

## Frontend Structure

```text
frontend/
├── app/
│   ├── components/
│   │   ├── charts.py
│   │   ├── email_draft_card.py
│   │   ├── export_panel.py
│   │   ├── import_card.py
│   │   ├── kpi_cards.py
│   │   ├── lead_status_badge.py
│   │   ├── lead_table.py
│   │   ├── priority_score.py
│   │   └── sidebar.py
│   ├── pages/
│   │   ├── dashboard.py
│   │   ├── email_drafts.py
│   │   ├── export_center.py
│   │   ├── imports.py
│   │   ├── lead_detail.py
│   │   ├── leads.py
│   │   ├── login.py
│   │   └── upload_leads.py
│   ├── services/
│   │   ├── api_client.py
│   │   ├── auth_client.py
│   │   ├── dashboard_client.py
│   │   ├── email_draft_client.py
│   │   ├── export_client.py
│   │   ├── import_client.py
│   │   ├── lead_client.py
│   │   └── scoring_client.py
│   ├── utils/
│   │   └── session.py
│   ├── config.py
│   └── main.py
├── scripts/
├── Dockerfile
├── requirements.txt
└── README.md
```

## How It Talks to the Backend

All backend calls go through the shared API client:

```text
frontend/app/services/api_client.py
```

JWT tokens are stored in Streamlit session state. Page access is protected by session helpers so unauthenticated users are sent back to login.

The backend API URL comes from:

```env
BACKEND_API_URL=http://localhost:8000
```

When running inside Docker Compose, the compose file sets:

```env
BACKEND_API_URL=http://backend:8000
```

## Run Locally

From the project root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r frontend/requirements.txt
make frontend
```

Or from this directory:

```bash
pip install -r requirements.txt
BACKEND_API_URL=http://localhost:8000 streamlit run app/main.py --server.port 8501
```

Open:

```text
http://localhost:8501
```

The backend must also be running at:

```text
http://localhost:8000
```

## Run With Docker

From the project root:

```bash
cp .env.example .env
docker compose up --build frontend backend postgres
```

Open:

```text
http://localhost:8501
```

## Main User Workflow

1. Register or log in.
2. Upload a CSV or Excel lead file.
3. Process the import into leads.
4. Score leads.
5. Review dashboard metrics.
6. Filter leads by status, category, source, or missing contact data.
7. Open a lead detail page.
8. Generate an email draft.
9. Edit and approve the draft.
10. Export approved drafts from the Export Center.

## UI Notes

The frontend avoids heavy spreadsheet processing. File parsing, cleaning, scoring, and export generation happen in the backend.

The Streamlit app is intentionally business-focused:

- Compact navigation.
- Clear errors.
- Practical tables and filters.
- Drafts shown as editable review items.
- No email sending.

## Screenshot Placeholders

Screenshot guidance lives in:

[../docs/screenshots/README.md](../docs/screenshots/README.md)
