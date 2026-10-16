# Deploying Budget Tracker on Oracle Cloud Infrastructure (OCI)

This guide walks you through deploying the **Budget Tracker** Django application on an **Oracle Cloud Infrastructure (OCI) Compute Instance** using **Docker Compose**, **PostgreSQL 16**, **Gunicorn**, and **Nginx**.

---

## 🏛️ Architecture Overview

The production deployment consists of 3 isolated containers orchestrated with Docker Compose:
- **`nginx`**: Front-facing reverse proxy (ports 80 & 443). Directly serves static files (`/static/`) and media uploads (`/media/` for receipts) with aggressive caching and 25MB upload limits.
- **`web`**: Django application executed via **Gunicorn WSGI** (3 worker processes) with WhiteNoise fallback.
- **`db`**: **PostgreSQL 16** with persistent volume storage (`postgres_data`).

> [!TIP]
> This setup is 100% compatible with the **Oracle Cloud Always Free Tier** (e.g., Ampere A1 ARM64 instance with up to 4 OCPUs and 24 GB RAM, or AMD Micro).

---

## 📋 Step 1: Create an OCI Compute Instance

1. Log into your **[Oracle Cloud Console](https://cloud.oracle.com)**.
2. In the navigation menu (top-left), go to **Compute** &rarr; **Instances** &rarr; **Create instance**.
3. Configure the instance:
   - **Name**: `budget-tracker-server` (or any name you prefer)
   - **Placement**: Keep default Availability Domain
   - **Image and shape**:
     - **Image**: **Ubuntu 24.04** or **Ubuntu 22.04 LTS** (recommended)
     - **Shape**: Select **Ampere (VM.Standard.A1.Flex)** for Always Free (e.g. 2–4 OCPU, 12–24 GB RAM) or **AMD (VM.Standard.E2.1.Micro)**
   - **Networking**:
     - Select **Create new virtual cloud network** or use existing
     - Under **Public IPv4 address**, ensure **Assign a public IPv4 address** is selected.
   - **Add SSH keys**:
     - Upload your public SSH key (`~/.ssh/id_rsa.pub` or `~/.ssh/id_ed25519.pub`) or choose **Generate a key pair** and download the private key.
4. Click **Create** and wait for the instance status to become **Running** (green).
5. Note your instance's **Public IP Address** (e.g., `129.146.xxx.xxx`).

---

## 🔓 Step 2: Open Ports in OCI Virtual Cloud Network (VCN)

By default, OCI security lists block HTTP (port 80) and HTTPS (port 443) from the public internet.

1. In the OCI Console, navigate to **Networking** &rarr; **Virtual Cloud Networks**.
2. Click on the VCN associated with your instance.
3. Under **Resources** (left side), click **Security Lists**, then click **Default Security List for [your-vcn]**.
4. Click **Add Ingress Rules**:
   - **Source Type**: CIDR
   - **Source CIDR**: `0.0.0.0/0`
   - **IP Protocol**: TCP
   - **Source Port Range**: All (leave empty)
   - **Destination Port Range**: `80,443`
   - **Description**: `Allow HTTP and HTTPS traffic`
5. Click **Add Ingress Rules**.

---

## 💻 Step 3: Connect to your VM via SSH

Open your local terminal and connect to your instance:

```bash
# If using Ubuntu:
ssh -i /path/to/your/private_key ubuntu@<YOUR_OCI_PUBLIC_IP>

# If using Oracle Linux:
ssh -i /path/to/your/private_key opc@<YOUR_OCI_PUBLIC_IP>
```

---

## 🚀 Step 4: Clone the Repository & Configure Environment

1. Clone your Budget Tracker repository on the VM:
   ```bash
   git clone <YOUR_GIT_REPOSITORY_URL> budget-tracker
   cd budget-tracker
   ```

2. Create your `.env` configuration file:
   ```bash
   cp .env.production.example .env
   ```

3. Edit `.env` using nano or vim:
   ```bash
   nano .env
   ```

   Update the following values:
   - `SECRET_KEY`: Set to a strong random key (generate one with: `openssl rand -base64 48`)
   - `ALLOWED_HOSTS`: Add your server's Public IP and domain name (e.g., `129.146.xxx.xxx,yourdomain.com`)
   - `CSRF_TRUSTED_ORIGINS`: Set your origins (e.g., `http://129.146.xxx.xxx,https://yourdomain.com`)
   - `POSTGRES_PASSWORD`: Choose a secure password for PostgreSQL

---

## ⚡ Step 5: Run the Automated Deployment Script

Make sure `deploy_oci.sh` is executable and run it:

```bash
chmod +x deploy_oci.sh entrypoint.sh
./deploy_oci.sh
```

### What this script automatically does:
1. **Host-Level Firewall**: OCI Linux images have a built-in `iptables`/`ufw` firewall rule that drops non-SSH inbound traffic. The script opens ports **80** and **443** at the OS level so your app is reachable.
2. **Docker Engine**: Installs Docker and the Docker Compose plugin if not already installed.
3. **Container Launch**: Builds the Docker container, executes PostgreSQL readiness checks, runs database migrations (`python manage.py migrate`), and collects all static assets (`python manage.py collectstatic`).
4. **Starts Services**: Runs Nginx, Django/Gunicorn, and PostgreSQL in the background.

---

## 👤 Step 6: Create an Admin Account

Once the containers are running, create your Django superuser:

```bash
sudo docker compose exec web python manage.py createsuperuser
```

Enter your desired username, email, and password.

---

## 🌐 Step 7: Access Your App

Open your web browser and navigate to:
```
http://<YOUR_OCI_PUBLIC_IP>
```
You can now log in, configure wallets, create budgets, log transactions, and upload receipts!

---

## 🔒 Step 8 (Recommended): Adding a Custom Domain & Free SSL (HTTPS)

### Option A: Cloudflare (Fastest & Easiest)
1. Add an `A` record in Cloudflare pointing your domain/subdomain (e.g., `budget.yourdomain.com`) to `<YOUR_OCI_PUBLIC_IP>`.
2. Enable the **Cloudflare Proxy (Orange Cloud)**.
3. Set SSL/TLS encryption mode to **Flexible** (or **Full** with a Cloudflare Origin Certificate).
4. Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in your `.env`:
   ```env
   ALLOWED_HOSTS=budget.yourdomain.com,127.0.0.1
   CSRF_TRUSTED_ORIGINS=https://budget.yourdomain.com
   ```
5. Reload containers: `sudo docker compose up -d`

### Option B: Let's Encrypt / Certbot
1. Point your domain `A` record directly to `<YOUR_OCI_PUBLIC_IP>`.
2. Obtain a certificate using certbot:
   ```bash
   sudo docker compose run --rm --entrypoint "\
     certbot certonly --webroot -w /var/www/certbot \
     --email your-email@example.com \
     -d yourdomain.com -d www.yourdomain.com \
     --agree-tos --no-eff-email" nginx
   ```
3. Update `nginx/conf.d/default.conf` to enable SSL listening on port 443 with your generated certificates in `/etc/letsencrypt/live/yourdomain.com/`.

---

## 🛠️ Management & Maintenance Cheatsheet

| Task | Command |
|---|---|
| **View live logs** | `sudo docker compose logs -f` |
| **Check container health** | `sudo docker compose ps` |
| **Restart services** | `sudo docker compose restart` |
| **Stop all services** | `sudo docker compose down` |
| **Deploy code updates** | `git pull && sudo docker compose build && sudo docker compose up -d` |
| **Backup PostgreSQL database** | `sudo docker compose exec db pg_dump -U budget_user budget_tracker > backup_$(date +%F).sql` |
| **Restore PostgreSQL database** | `cat backup.sql \| sudo docker compose exec -T db psql -U budget_user budget_tracker` |
| **Open Django shell** | `sudo docker compose exec web python manage.py shell` |
