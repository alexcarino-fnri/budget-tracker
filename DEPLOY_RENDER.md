# Deploying Budget Tracker on Render

This guide provides everything you need to deploy the **Budget Tracker** Django application on **[Render](https://render.com)** with **PostgreSQL**, **Gunicorn**, **WhiteNoise**, and automatic **HTTPS/SSL**.

---

## 🏛️ Architecture Overview

On Render, the application is deployed using:
- **Web Service**: Runs Django with **Gunicorn** WSGI on Python 3.12 (Native Python or Docker container).
- **PostgreSQL Database**: Managed Render PostgreSQL instance, connected via private internal network (`DATABASE_URL`).
- **Static Asset Serving**: **WhiteNoise** with compression and cache headers directly from the web process (no Nginx container required).
- **Media Uploads (Receipts)**: Served directly with Django's media route fallback or persisted to a Render Persistent Disk.
- **SSL / HTTPS**: Automatically provisioned by Render with free Let's Encrypt certificates.

---

## ⚡ Method 1: 1-Click Blueprint Deploy (Recommended)

This repository includes a [`render.yaml`](render.yaml) Blueprint file. Render reads this file and automatically configures the PostgreSQL database, links database credentials, sets environment variables, and launches the web service with zero manual copy-pasting.

### Step 1: Push your Code to GitHub or GitLab
Ensure your project repository is pushed to your GitHub or GitLab account:
```bash
git add .
git commit -m "Configure project for Render deployment"
git push origin main
```

### Step 2: Create Blueprint Instance on Render
1. Log in to your **[Render Dashboard](https://dashboard.render.com/)**.
2. Click **New +** in the top-right corner and select **Blueprint**.
3. Connect your repository (`budget-tracker`).
4. Enter a name for the Blueprint instance (e.g. `budget-tracker`).
5. Click **Apply**.

Render will automatically:
- Provision a **PostgreSQL Database** (`budget-tracker-db`).
- Provision a **Python Web Service** (`budget-tracker-web`).
- Inject the private `DATABASE_URL` from the database directly into the web service.
- Generate a secure, unique `SECRET_KEY`.
- Run [`build.sh`](build.sh) (installs packages, runs database migrations, and collects static files).
- Start the web service using Gunicorn.

Once deployment finishes, click the service URL (e.g. `https://budget-tracker-web.onrender.com`) to view your live app!

---

## 🛠️ Method 2: Manual Dashboard Deploy (Step-by-Step)

If you prefer to configure the services manually through the Render web UI, follow these steps:

### Step 1: Create a Managed PostgreSQL Database
1. In the Render Dashboard, click **New +** &rarr; **PostgreSQL**.
2. Fill in the database details:
   - **Name**: `budget-tracker-db`
   - **Database**: `budget_tracker`
   - **User**: `budget_user`
   - **Region**: Choose the region closest to you (e.g. *Oregon, US West* or *Frankfurt, EU*)
   - **PostgreSQL Version**: Default (16)
   - **Instance Type**: **Free**
3. Click **Create Database**.
4. Once created, look for the **Connections** panel and copy the **Internal Database URL** (e.g., `postgres://budget_user:...@dpg-xxxx-a/budget_tracker`).
   > [!IMPORTANT]
   > Always use the **Internal Database URL** for services running on Render. Internal connections are faster, encrypted, and do not incur external bandwidth quotas.

---

### Step 2: Create the Django Web Service
1. In the Render Dashboard, click **New +** &rarr; **Web Service**.
2. Select your Git repository.
3. Configure the service settings:
   - **Name**: `budget-tracker`
   - **Region**: Select the **same region** as your database!
   - **Branch**: `main`
   - **Runtime**: **Python 3**
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn config.wsgi:application`
     > [!WARNING]
     > Render often auto-fills the Start Command with `gunicorn Budget_Tracker.wsgi:application` based on your GitHub repository name. Change it to `gunicorn config.wsgi:application` (we also provide a `Budget_Tracker` fallback alias in the codebase).
   - **Instance Type**: **Free**

---

### Step 3: Add Environment Variables
Scroll down to the **Environment Variables** section and add the following keys:

| Key | Value | Description |
|---|---|---|
| `DATABASE_URL` | *(Paste Internal Database URL from Step 1)* | Private PostgreSQL connection string |
| `SECRET_KEY` | *(Click "Generate" or paste a random string)* | Django production secret key |
| `DEBUG` | `False` | Disables debug mode in production |
| `PYTHON_VERSION` | `3.12.8` | Ensures Python 3.12 runtime parity |
| `WEB_CONCURRENCY` | `2` | Number of Gunicorn worker processes |
| `ALLOWED_HOSTS` | `.onrender.com,localhost,127.0.0.1` | Allowed hostnames |
| `CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com` | Allowed CSRF origins |

> [!TIP]
> The application code in `config/settings.py` includes automatic detection for Render (`RENDER_EXTERNAL_HOSTNAME` and `RENDER=true`), so your `.onrender.com` domain is automatically trusted even if you forget to add it to `ALLOWED_HOSTS`.

4. Click **Create Web Service**.
5. Render will run `./build.sh`, run migrations, collect static files, and boot Gunicorn.

---

## 👤 Step 4: Create a Superuser / Admin Account

Once the web service is live, you can create your Django administrator account using Render's built-in web terminal:

1. In the Render Dashboard, navigate to your **Web Service** (`budget-tracker`).
2. In the left navigation menu, click **Shell**.
3. Click **Connect** to open a secure web terminal session into the running container.
4. Run:
   ```bash
   python manage.py createsuperuser
   ```
5. Follow the interactive prompts to enter a username, email, and password.
6. Now you can visit `https://your-app.onrender.com/admin/` or `https://your-app.onrender.com/accounts/login/` and log in with your credentials.

---

## 📁 Step 5: Handling Media Files (Receipt Uploads)

### Free Tier (Ephemeral Storage)
Render's Free Web Services use an ephemeral filesystem. If the service restarts or redeploys, files saved to the local container disk will be reset. Receipts uploaded during a session remain accessible while the container is active.

### Persistent Storage (Recommended for Long-Term Receipts)
If you require receipts to persist permanently across redeployments:
1. Upgrade the web service to the **Starter** tier ($7/month).
2. Go to **Disks** in your Web Service settings &rarr; **Add Disk**.
3. Configure the disk:
   - **Name**: `media-storage`
   - **Mount Path**: `/var/data`
   - **Size**: `1 GB` (or more)
4. In your Web Service **Environment Variables**, add:
   ```env
   MEDIA_ROOT=/var/data/media
   ```
5. The application will automatically save and serve all receipts from the persistent disk.

*(Alternatively, for cloud storage at zero compute cost, configure `django-storages` with AWS S3, Cloudflare R2, or Supabase Storage).*

---

## 🌐 Step 6: Custom Domain & Free SSL (Optional)

1. In your Web Service dashboard, go to **Settings** &rarr; **Custom Domains**.
2. Click **Add Custom Domain** and enter your domain (e.g. `budget.yourdomain.com`).
3. Add the DNS records shown by Render in your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.):
   - **CNAME** pointing `budget` to `budget-tracker.onrender.com` (for subdomains)
   - Or **A Record** pointing `@` to Render's IP (for root domains)
4. Render automatically provisions and renews a free Let's Encrypt SSL/TLS certificate.
5. If using a custom domain, add it to your environment variables:
   - `ALLOWED_HOSTS`: `budget.yourdomain.com,.onrender.com`
   - `CSRF_TRUSTED_ORIGINS`: `https://budget.yourdomain.com,https://*.onrender.com`

---

## 🔧 Maintenance & Management Commands

To run periodic tasks or management commands, use the **Shell** tab in the Render Dashboard:

### Process Recurring Transactions
```bash
python manage.py generate_recurring
```

### Run Custom SQL / Django Shell
```bash
python manage.py shell
```

### Inspect Database Status
```bash
python manage.py showmigrations
```

---

## ❓ Frequently Asked Questions & Troubleshooting

### 1. App takes 50 seconds to load after being idle (Cold Start)
- **Cause**: On Render's Free tier, Web Services automatically spin down after 15 minutes of inactivity to conserve resources.
- **Solution**: The first request spins the container back up (takes ~30-50 seconds). Subsequent requests respond instantly. To keep the service awake 24/7 without upgrading, you can ping your app every 10 minutes using a free uptime monitor (e.g. UptimeRobot or Cron-Job.org), or upgrade to the Starter plan ($7/mo).

### 2. `Invalid HTTP_HOST header` or `400 Bad Request`
- Check that your Render hostname or custom domain is included in `ALLOWED_HOSTS`.
- Because our `config/settings.py` includes auto-detection for `RENDER_EXTERNAL_HOSTNAME`, this is handled automatically if `RENDER_EXTERNAL_HOSTNAME` is present.

### 3. `Forbidden (403): CSRF verification failed`
- Ensure `CSRF_TRUSTED_ORIGINS` contains `https://your-app.onrender.com` (and `https://*.onrender.com`).
- The application automatically adds `https://*.onrender.com` when running on Render.

### 4. Database Connection Errors (`OperationalError: could not connect to server`)
- Verify that your Web Service and PostgreSQL database are in the **same region**.
- Ensure `DATABASE_URL` is set to the **Internal Database URL** (e.g. `postgres://...dpg-xxxx-a...`), not the External URL.
- On Render's Free tier, PostgreSQL databases expire after 30 days unless upgraded to a paid instance or recreated.

### 5. `ModuleNotFoundError: No module named 'Budget_Tracker'`
- **Cause**: Render automatically generated the Start Command based on your repository name (`Budget_Tracker`).
- **Solution**: In your Web Service &rarr; **Settings** &rarr; change **Start Command** to `gunicorn config.wsgi:application`. (The codebase also includes a compatibility alias `Budget_Tracker/wsgi.py` that forwards directly to `config.wsgi`).
