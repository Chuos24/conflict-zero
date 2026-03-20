#!/bin/bash
# AWS EC2 User Data Script for Conflict Zero Backend
# Run on Amazon Linux 2023 or Ubuntu 22.04

set -e

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
DOCKER_COMPOSE_VERSION=v2.23.0
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install other tools
apt-get install -y git nginx certbot python3-certbot-nginx

# Create app directory
mkdir -p /opt/conflict-zero
cd /opt/conflict-zero

# Clone repository (replace with your repo)
# git clone https://github.com/yourusername/conflict-zero.git .

# Create environment file
cat > .env << EOF
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@localhost:5432/conflictzero
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=${SECRET_KEY}
DEBUG=false
DECOLECTA_API_KEY=${DECOLECTA_API_KEY}
EOF

# Start services with Docker Compose
docker-compose -f infrastructure/docker-compose.prod.yml up -d

# Configure Nginx
cat > /etc/nginx/sites-available/conflict-zero << 'NGINX'
server {
    listen 80;
    server_name api.czperu.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
NGINX

ln -s /etc/nginx/sites-available/conflict-zero /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

# Get SSL certificate (uncomment when DNS is ready)
# certbot --nginx -d api.czperu.com --non-interactive --agree-tos -m admin@czperu.com

echo "Setup complete!"
