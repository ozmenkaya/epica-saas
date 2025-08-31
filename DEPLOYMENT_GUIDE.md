# 🚀 Digital Ocean Production Deployment - Adım Adım

## ✅ Önkoşullar Tamamlandı:
- [x] SSH Key hazır
- [x] Git repository oluşturuldu
- [x] SaaS kodu commit edildi

## 📋 Deployment Checklist:

### 1. Digital Ocean Droplet (5 dakika)
- [ ] Digital Ocean hesabı açıldı
- [ ] SSH key eklendi
- [ ] Droplet oluşturuldu (Ubuntu 22.04, 4GB RAM, $24/ay)
- [ ] Droplet IP alındı

### 2. GitHub Repository (2 dakika)
```bash
# ✅ GitHub repository hazır:
# https://github.com/ozmenkaya/epica-saas.git
```

### 3. Domain DNS Ayarları (30 dakika - propagation)
```
Domain sağlayıcınızda aşağıdaki kayıtları ekleyin:

A     epica.com.tr        -> [DROPLET_IP]
A     *.epica.com.tr      -> [DROPLET_IP]
CNAME www.epica.com.tr    -> epica.com.tr
```

### 4. Sunucu Bağlantısı ve Deployment (10 dakika)
```bash
# Droplet'e SSH ile bağlan
ssh root@[DROPLET_IP]

# Repository'yi klonla
git clone https://github.com/ozmenkaya/epica-saas.git epica
cd epica

# Deploy script'ini çalıştır
chmod +x deploy.sh
./deploy.sh epica.com.tr
```

### 5. SSL Sertifikası (Otomatik - 2 dakika)
Script otomatik olarak Let's Encrypt SSL kuracak

### 6. Test ve Doğrulama (5 dakika)
```bash
# Servis durumları kontrol
systemctl status epica
systemctl status nginx
systemctl status postgresql

# Test URL'leri:
curl -I https://epica.com.tr
curl -I https://test.epica.com.tr
```

## 🎯 Deployment Sonrası Yapılacaklar:

### 1. Platform Admin Hesabı
```bash
# Sunucuda admin hesabı oluştur
cd /var/www/epica
sudo -u epica .venv/bin/python -c "
from app_saas import app, db
from models_saas import PlatformAdmin
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = PlatformAdmin(
        username='admin',
        password_hash=generate_password_hash('YourSecurePassword123!'),
        first_name='Platform',
        last_name='Admin',
        is_super_admin=True
    )
    db.session.add(admin)
    db.session.commit()
    print('Platform admin oluşturuldu: admin / YourSecurePassword123!')
"
```

### 2. İlk Tenant Test
```
1. https://epica.com.tr adresine git
2. "Kayıt Ol" ile ilk tenant'ı oluştur
3. Subdomain test: https://test.epica.com.tr
```

### 3. Monitoring Setup
```bash
# Log takibi
tail -f /var/log/nginx/access.log
tail -f /var/log/epica/app.log

# Database monitoring
sudo -u postgres psql epica_saas -c "SELECT name, created_at FROM tenants;"
```

## 🔧 Troubleshooting

### SSL Problemi:
```bash
sudo certbot renew --dry-run
sudo systemctl reload nginx
```

### Uygulama Restart:
```bash
sudo systemctl restart epica
sudo systemctl status epica
```

### Database Reset (Dikkat - Veri silinir):
```bash
sudo -u postgres dropdb epica_saas
sudo -u postgres createdb epica_saas
sudo systemctl restart epica
```

## 📊 Performans Monitoring

### Server Resources:
```bash
# CPU, Memory, Disk usage
htop
df -h
free -h
```

### Application Logs:
```bash
# Real-time log monitoring
journalctl -u epica -f
```

### Database Performance:
```bash
sudo -u postgres psql epica_saas -c "
SELECT schemaname,tablename,attname,n_distinct,correlation 
FROM pg_stats WHERE tablename='tenants';
"
```

## 🎉 Go-Live Checklist:

- [ ] HTTPS çalışıyor (epica.com.tr)
- [ ] Subdomain çalışıyor (*.epica.com.tr)  
- [ ] Ana sayfa yükleniyor
- [ ] Tenant kaydı çalışıyor
- [ ] Database bağlantısı OK
- [ ] Email gönderimi test edildi
- [ ] Backup çalışıyor
- [ ] Monitoring aktif

**Tahmini toplam süre: 1 saat**
**Maliyet: $24/ay (~₺800/ay)**
