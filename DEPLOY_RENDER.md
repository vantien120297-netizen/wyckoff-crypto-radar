# Deploy Wyckoff Crypto Radar to Render (free trial)

1. Push the project folder to a GitHub repository. Keep `app.py`, `templates/`, `static/`, `requirements.txt`, `Procfile`, and `render.yaml` at the repository root.
2. In Render, choose **New + → Web Service** and connect the GitHub repository.
3. Choose the **Free** instance plan.
4. Set Build Command to `pip install -r requirements.txt`.
5. Set Start Command to `gunicorn app:app --workers 2 --threads 4 --timeout 120`.
6. Optional health check path: `/api/health`.
7. Deploy. When successful, open the assigned `https://<service-name>.onrender.com` URL.
8. Verify the home page loads and `/api/health` returns JSON with `ok: true`.
9. On iPhone, open the HTTPS URL in Safari → Share → Add to Home Screen.

Free Render services sleep after 15 minutes without inbound traffic and can take about a minute to wake up. They use ephemeral storage. This app does not store user data, so persistent disk is not required. Free services are for testing, not production.
