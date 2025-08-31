# Digital Ocean SaaS Deployment Guide

## 1. Digital Ocean Droplet Oluşturma

### Droplet Özellikleri (Başlangıç için):
- **OS**: Ubuntu 22.04 LTS
- **Plan**: Basic Droplet
- **CPU**: 2 vCPUs
- **Memory**: 4 GB RAM
- **Storage**: 80 GB SSD
- **Fiyat**: $24/ay (~₺800/ay)
- **Bandwidth**: 4 TB transfer

### Droplet Oluşturma Adımları:
1. Digital Ocean hesabı açın: https://digitalocean.com
2. "Create" > "Droplets" tıklayın
3. Ubuntu 22.04 LTS seçin
4. $24/ay plan seçin (4GB RAM)
5. SSH Key ekleyin (güvenlik için)
6. Droplet adı: `epica-saas-prod`
7. "Create Droplet" tıklayın

## 2. Domain Konfigürasyonu

### DNS Ayarları:
```
A Record: epica.com.tr -> [DROPLET_IP]
A Record: *.epica.com.tr -> [DROPLET_IP]  (Wildcard için subdomain)
```

## 3. Sunucu Kurulumu

SSH ile bağlanın:
```bash
ssh root@[DROPLET_IP]
```

Deployment scriptini çalıştırın:
```bash
# Projeyi klonla
git clone https://github.com/kullanici/epica.git
cd epica

# Deploy scriptini çalıştır
chmod +x deploy.sh
./deploy.sh epica.com.tr
```

## 4. SSL Sertifikası (Otomatik)

Script otomatik olarak Let's Encrypt SSL kuracak:
- https://epica.com.tr
- https://*.epica.com.tr (wildcard)

## 5. Database Yedekleme

PostgreSQL otomatik yedekleme:
```bash
# Günlük yedek cron job
0 2 * * * pg_dump epica_saas > /backups/epica_$(date +%Y%m%d).sql
```

## 6. Monitoring ve Logging

### Digital Ocean Monitoring:
- CPU, Memory, Disk kullanımı
- Uptime monitoring
- Email alerts

### Log Files:
- Nginx: `/var/log/nginx/`
- Gunicorn: `/var/log/gunicorn/`
- PostgreSQL: `/var/log/postgresql/`

## 7. Ölçekleme Seçenekleri

### Droplet Yükseltme:
- 4GB RAM → 8GB RAM ($48/ay)
- 8GB RAM → 16GB RAM ($96/ay)

### Managed Database:
- PostgreSQL Managed Database ($15/ay)
- Otomatik yedekleme ve failover

### Load Balancer:
- Birden fazla droplet için ($12/ay)

## 8. Güvenlik

### Firewall (Otomatik kurulur):
```bash
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### Fail2Ban (DDoS koruması):
```bash
# Otomatik olarak kurulur
systemctl status fail2ban
```

## 9. Toplam Maliyet (Aylık)

### Minimum Setup:
- Droplet (4GB): $24/ay (~₺800)
- Domain: ~₺50/ay
- **Toplam**: ~₺850/ay

### Production Setup:
- Droplet (8GB): $48/ay (~₺1600)
- Managed Database: $15/ay (~₺500)
- Load Balancer: $12/ay (~₺400)
- **Toplam**: ~₺2500/ay

## 10. Backup Stratejisi

### Droplet Snapshots:
- Haftalık otomatik snapshot: $2.40/ay
- Manuel snapshot oluşturma

### Database Backup:
- Daily PostgreSQL dump
- S3 compatible storage

## Avantajları:
✅ Kolay kurulum ve yönetim
✅ Otomatik yedekleme
✅ 99.99% uptime SLA
✅ 24/7 destek
✅ Monitoring ve alerting
✅ Kolay ölçekleme
✅ SSD storage
✅ Global CDN entegrasyonu
