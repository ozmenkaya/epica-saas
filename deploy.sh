#!/bin/bash

# Epica SaaS - Production Deployment Script
# Ubuntu 22.04 LTS için optimize edilmiştir

set -e

echo "🚀 Epica SaaS Production Deployment başlıyor..."

# Variables
APP_NAME="epica"
APP_USER="epica"
APP_DIR="/var/www/epica"
DOMAIN="epica.com.tr"
DB_NAME="epica_saas"
DB_USER="epica_user"
DB_PASSWORD=$(openssl rand -base64 32)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo_error "Bu script root olarak çalıştırılmalıdır"
   exit 1
fi

echo_info "System güncelleniyor..."
apt update && apt upgrade -y

echo_info "Gerekli paketler yükleniyor..."
apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    wget \
    htop \
    unzip \
    supervisor \
    fail2ban \
    ufw

echo_info "PostgreSQL veritabanı konfigürasyonu..."
sudo -u postgres createuser --interactive --pwprompt $DB_USER
sudo -u postgres createdb --owner=$DB_USER $DB_NAME

echo_info "Application user oluşturuluyor..."
useradd --system --shell /bin/bash --home $APP_DIR --create-home $APP_USER

echo_info "Application dizini hazırlanıyor..."
mkdir -p $APP_DIR
mkdir -p /var/log/$APP_NAME
mkdir -p /var/run/$APP_NAME
chown -R $APP_USER:$APP_USER $APP_DIR
chown -R $APP_USER:$APP_USER /var/log/$APP_NAME
chown -R $APP_USER:$APP_USER /var/run/$APP_NAME

echo_info "Python virtual environment oluşturuluyor..."
sudo -u $APP_USER python3.11 -m venv $APP_DIR/venv

echo_info "Kaynak kodu klonlanıyor..."
cd $APP_DIR
sudo -u $APP_USER git clone https://github.com/yourusername/epica-saas.git .

echo_info "Python dependencies yükleniyor..."
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements_saas.txt

echo_info "Environment dosyası oluşturuluyor..."
sudo -u $APP_USER cp .env.example .env
sudo -u $APP_USER sed -i "s/your_secure_password/$DB_PASSWORD/g" .env
sudo -u $APP_USER sed -i "s/your-super-secret-key-change-this-in-production/$(openssl rand -base64 32)/g" .env
sudo -u $APP_USER sed -i "s/your-password-salt-change-this/$(openssl rand -base64 32)/g" .env

echo_info "Database migration..."
sudo -u $APP_USER $APP_DIR/venv/bin/python -c "
from app_saas import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"

echo_info "Firewall konfigürasyonu..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 'Nginx Full'

echo_info "SSL Certificate alınıyor..."
certbot --nginx -d $DOMAIN -d "*.$DOMAIN" --non-interactive --agree-tos --email admin@$DOMAIN

echo_info "Nginx konfigürasyonu..."
cp nginx.conf /etc/nginx/sites-available/$APP_NAME
ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo_info "Systemd service konfigürasyonu..."
cp $APP_NAME.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable $APP_NAME
systemctl start $APP_NAME

echo_info "Fail2ban konfigürasyonu..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true

[nginx-noscript]
enabled = true

[nginx-badbots]
enabled = true

[nginx-noproxy]
enabled = true
EOF

systemctl restart fail2ban

echo_info "Redis konfigürasyonu..."
systemctl enable redis-server
systemctl start redis-server

echo_info "Log rotation konfigürasyonu..."
cat > /etc/logrotate.d/$APP_NAME << EOF
/var/log/$APP_NAME/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    postrotate
        systemctl reload $APP_NAME
    endscript
}
EOF

echo_info "Monitoring script oluşturuluyor..."
cat > /usr/local/bin/epica-monitor.sh << 'EOF'
#!/bin/bash
# Epica Health Check Script

# Check if application is running
if ! systemctl is-active --quiet epica; then
    echo "$(date): Epica service is not running, attempting restart..."
    systemctl restart epica
fi

# Check database connection
if ! sudo -u epica /var/www/epica/venv/bin/python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    conn.close()
    print('DB OK')
except:
    print('DB ERROR')
    exit(1)
" > /dev/null 2>&1; then
    echo "$(date): Database connection failed!"
fi

# Check disk space
DISK_USAGE=$(df /var/www/epica | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "$(date): Warning: Disk usage is at ${DISK_USAGE}%"
fi
EOF

chmod +x /usr/local/bin/epica-monitor.sh

# Add monitoring to crontab
echo "*/5 * * * * /usr/local/bin/epica-monitor.sh >> /var/log/epica/monitor.log 2>&1" | crontab -

echo_info "Backup script oluşturuluyor..."
cat > /usr/local/bin/epica-backup.sh << 'EOF'
#!/bin/bash
# Epica Backup Script

BACKUP_DIR="/var/backups/epica"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="epica_saas"

mkdir -p $BACKUP_DIR

# Database backup
sudo -u postgres pg_dump $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Application files backup
tar -czf $BACKUP_DIR/app_$DATE.tar.gz -C /var/www epica

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "$(date): Backup completed - db_$DATE.sql.gz, app_$DATE.tar.gz"
EOF

chmod +x /usr/local/bin/epica-backup.sh

# Add backup to crontab
echo "0 2 * * * /usr/local/bin/epica-backup.sh >> /var/log/epica/backup.log 2>&1" | crontab -

echo_info "Services başlatılıyor..."
systemctl restart postgresql
systemctl restart redis-server
systemctl restart nginx
systemctl restart $APP_NAME

echo_info "Service durumları kontrol ediliyor..."
systemctl is-active postgresql
systemctl is-active redis-server
systemctl is-active nginx
systemctl is-active $APP_NAME

echo_info "Final security ayarları..."
# Remove unnecessary packages
apt autoremove -y

# Update file permissions
chmod -R 750 $APP_DIR
chmod -R 640 $APP_DIR/.env
chown -R $APP_USER:$APP_USER $APP_DIR

echo ""
echo_info "🎉 Epica SaaS deployment tamamlandı!"
echo ""
echo_info "✅ Application URL: https://$DOMAIN"
echo_info "✅ Database: PostgreSQL ($DB_NAME)"
echo_info "✅ Redis: Çalışıyor"
echo_info "✅ SSL: Let's Encrypt ile aktif"
echo_info "✅ Firewall: UFW aktif"
echo_info "✅ Monitoring: 5 dakika aralıklarla çalışıyor"
echo_info "✅ Backup: Günlük 02:00'da çalışıyor"
echo ""
echo_warning "⚠️  Database şifresi: $DB_PASSWORD"
echo_warning "⚠️  Bu şifreyi güvenli bir yerde saklayın!"
echo ""
echo_info "🔧 Log dosyaları:"
echo_info "   Application: /var/log/$APP_NAME/"
echo_info "   Nginx: /var/log/nginx/"
echo_info "   System: journalctl -u $APP_NAME"
echo ""
echo_info "🚀 Deployment başarıyla tamamlandı!"
