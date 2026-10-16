#!/usr/bin/env bash
# ==============================================================================
# Oracle Cloud Infrastructure (OCI) Deployment Script for Budget Tracker
# Supported OS: Ubuntu 22.04 / 24.04 LTS & Oracle Linux 8 / 9
# ==============================================================================

set -e

echo "=========================================================="
echo " Starting Budget Tracker Deployment on Oracle Cloud"
echo "=========================================================="

# 1. Open Host Firewall Ports for HTTP (80) and HTTPS (443)
echo "[1/5] Configuring Host Firewall for ports 80 & 443..."
if command -v iptables &> /dev/null; then
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
    if command -v netfilter-persistent &> /dev/null; then
        sudo netfilter-persistent save
    fi
fi

if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp || true
    sudo ufw allow 443/tcp || true
fi

if command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --zone=public --permanent --add-service=http || true
    sudo firewall-cmd --zone=public --permanent --add-service=https || true
    sudo firewall-cmd --reload || true
fi

# 2. Check and Install Docker & Docker Compose if missing
echo "[2/5] Checking Docker & Docker Compose installation..."
if ! command -v docker &> /dev/null; then
    echo "Installing Docker Engine..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker "$USER" || true
    rm -f get-docker.sh
    echo "Docker installed successfully."
fi

# 3. Environment configuration check
echo "[3/5] Verifying .env configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.production.example" ]; then
        echo "No .env found. Copying .env.production.example to .env..."
        cp .env.production.example .env
        RANDOM_KEY=$(openssl rand -hex 32)
        sed -i.bak "s/replace-with-a-long-random-secret-key-in-production/$RANDOM_KEY/" .env && rm -f .env.bak
        echo "Generated random SECRET_KEY in .env."
        echo "IMPORTANT: Please review and update ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS in .env with your public IP / domain!"
    else
        echo "Error: Neither .env nor .env.production.example found!"
        exit 1
    fi
fi

# 4. Build and start containers
echo "[4/5] Building and launching containers with Docker Compose..."
sudo docker compose down --remove-orphans || true
sudo docker compose build --pull
sudo docker compose up -d

# 5. Check container health
echo "[5/5] Checking container status..."
sleep 5
sudo docker compose ps

echo "=========================================================="
echo " Budget Tracker is now up and running on Oracle Cloud!"
echo " Web app is listening on HTTP port 80."
echo ""
echo " To create an initial admin account, run:"
echo "   sudo docker compose exec web python manage.py createsuperuser"
echo ""
echo " To view live container logs:"
echo "   sudo docker compose logs -f"
echo "=========================================================="
