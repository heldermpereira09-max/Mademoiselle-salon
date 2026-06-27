# Bella Salon

A Flask web application for a beauty salon booking system with Portuguese/English language support.

## Run & Operate

- `python run.py` — start the Flask app on port 5000
- Required: Python 3.11 (installed via Replit module)
- SQLite database at `salon.db` (auto-created on first run)

## Stack

- Python 3.11 + Flask
- Flask-SQLAlchemy (SQLite in dev, PostgreSQL-ready for prod)
- Flask-Babel (i18n: Portuguese + English)
- Jinja2 templates + vanilla CSS/JS (no frontend build step)

## Where things live

- `salon/` — Flask application package
- `salon/app.py` — app factory, DB setup, Babel config
- `salon/routes.py` — all URL routes (Blueprint `main`)
- `salon/models/models.py` — SQLAlchemy models + seed data
- `salon/templates/` — Jinja2 HTML templates
- `salon/static/css/style.css` — all styles
- `salon/static/js/main.js` — client-side JS
- `run.py` — entry point

## Architecture decisions

- App factory pattern (`create_app()`) for testability and future extensibility.
- SQLite by default in dev; falls back if `DATABASE_URL` is missing or points to Postgres without driver.
- Language stored in Flask session (`session['lang']`); falls back to `Accept-Language` header.
- Outlook Calendar integration is architecturally ready: `Booking.outlook_event_id` column is on the model, and the contact page shows the integration status. Wire up via Microsoft Graph API when ready.
- Services are seeded automatically on first run if the DB is empty.

## Product

- Homepage with hero, service category overview, and features
- Services page grouped by category (Hair, Nails, Skin, Makeup, Massage)
- Online booking form with real-time available slot calculation
- Booking confirmation page with full summary
- Contact page with Outlook Calendar integration placeholder
- Full PT/EN language switching via navbar

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- DB auto-creates on app start (`db.create_all()` + `seed_data()` called in app factory).
- Never import `psycopg2` unless Postgres is explicitly configured — the app defaults to SQLite.
- To add Outlook Calendar: install `msal` + `requests`, add `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` secrets, and call Microsoft Graph API `/me/events` after booking is saved.

## Pointers

- See the `pnpm-workspace` skill for workspace structure (Node.js side)
