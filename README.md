# StreetLens — Flask + Neon PostgreSQL + Vercel

This version keeps the existing StreetLens UI and adds:

- PostgreSQL database support through Neon
- SQLAlchemy ORM
- User registration/login stored in Neon
- Password hashing
- Flask sessions
- An `inspections` table for dashboard data
- Vercel Python deployment configuration

## 1. Local setup

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

If you want to test with Neon locally, create a `.env` file and load the variables through your shell or your preferred environment-variable tool.

For a quick local test without Neon, the app falls back to `streetlens.db` SQLite.

## 2. Create the Neon database

1. Create a project in Neon.
2. Open the project's **Connect** screen.
3. Copy the PostgreSQL connection string.
4. Keep SSL enabled (`sslmode=require` if it is not already present).

The value will look approximately like:

```text
postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Do not commit this connection string to GitHub.

## 3. Push the project to GitHub

From the `StreetLens-main` folder:

```powershell
git init
git add .
git commit -m "Add Neon database and Vercel deployment"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

## 4. Deploy on Vercel

1. Create/import a Vercel project from the GitHub repository.
2. Vercel will use `api/index.py` as the Python entry point.
3. In Vercel, open **Project Settings → Environment Variables**.
4. Add:

```text
DATABASE_URL = your Neon connection string
SECRET_KEY = a long random secret
```

5. Add them for the environment(s) you deploy to, usually **Production** and **Preview**.
6. Redeploy.

## 5. Database tables

The first request that needs the database calls `db.create_all()` and creates:

- `users`
  - id
  - username
  - email
  - password_hash
  - created_at
- `inspections`
  - id
  - route
  - mile_post
  - direction
  - distress_index
  - condition
  - captured_at

You can inspect these tables in the Neon SQL Editor.

### Important for future schema changes

`db.create_all()` is suitable for this initial project, but for a larger production application use Flask-Migrate/Alembic for controlled database migrations.

## 6. How the connection works

Browser
→ Vercel
→ Flask (`api/index.py`)
→ SQLAlchemy
→ Neon PostgreSQL

The browser never receives `DATABASE_URL`. It stays in Vercel's server-side environment variables.

## 7. Important security notes

- Never put `DATABASE_URL` in HTML or JavaScript.
- Never commit `.env` to GitHub.
- Never hard-code the Neon password in `app.py`.
- Use a strong `SECRET_KEY`.
- Passwords are stored as hashes, not plaintext.

## 8. Current limitation

The existing dashboard still contains mostly demo/static pavement-analysis values. The database is now ready for real inspection records, but your ML pipeline/API still needs to insert real detection results into the `inspections` table.

For example, later you can create a route such as:

```python
@app.route("/api/inspections", methods=["POST"])
@login_required
def create_inspection():
    ...
```

and save the ML result into Neon.
