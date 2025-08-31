# Epica SaaS - Multi-Tenant Teklif Yönetim Sistemi

## 🏗️ Mimari Özellikleri

### Multi-Tenant (Çok Kiracılı) Yapı
- **Tenant Model**: Her firma için izole veri yapısı
- **Subdomain Yapısı**: `firma.epica.com.tr` formatında özel erişim
- **Veri İzolasyonu**: Her tenant'ın verileri tamamen ayrık
- **Kaynak Limitleri**: Plan bazlı kullanıcı/müşteri/tedarikçi limitleri

### Güvenlik Önlemleri
- **SSL/TLS**: Let's Encrypt ile otomatik SSL sertifikaları
- **Rate Limiting**: API ve auth endpoint'leri için sınırlama
- **Firewall**: UFW ile network güvenliği
- **Fail2ban**: Brute force saldırı koruması
- **Input Validation**: SQLAlchemy ORM ile SQL injection koruması
- **CSRF Protection**: Form güvenliği
- **Security Headers**: HSTS, XSS, Content Security Policy

### Performans ve Ölçeklenebilirlik
- **Load Balancing**: Nginx ile multiple Gunicorn worker'ları
- **Caching**: Redis ile session ve data caching
- **Database**: PostgreSQL (production), SQLite (development)
- **CDN Ready**: Static dosyalar için CDN desteği
- **Async Tasks**: Celery ile background işlemler

## 📋 SaaS Özellikleri

### Abonelik Planları
1. **Deneme (15 gün ücretsiz)**
   - 2 kullanıcı, 10 müşteri, 5 tedarikçi
   - 50 ürün, 20 aylık teklif

2. **Temel (₺299/ay)**
   - 5 kullanıcı, 100 müşteri, 50 tedarikçi
   - 1000 ürün, 500 aylık teklif

3. **Profesyonel (₺599/ay)**
   - 15 kullanıcı, 500 müşteri, 200 tedarikçi
   - 5000 ürün, 2000 aylık teklif

4. **Kurumsal (₺1299/ay)**
   - 50 kullanıcı, 2000 müşteri, 1000 tedarikçi
   - 20000 ürün, 10000 aylık teklif

### Platform Yönetimi
- **Super Admin Panel**: Tüm tenant'ları yönetme
- **Tenant Admin**: Her firma için admin hesabı
- **Kullanım İstatistikleri**: Real-time kullanım takibi
- **Audit Logging**: Tüm işlemlerin kaydı

## 🛠️ Deployment

### Production Requirements
- **Server**: Ubuntu 22.04 LTS (minimum 2 CPU, 4GB RAM)
- **Database**: PostgreSQL 14+
- **Cache**: Redis 6+
- **Web Server**: Nginx
- **SSL**: Let's Encrypt
- **Domain**: epica.com.tr + wildcard subdomain

### Kurulum
```bash
# Repository klonla
git clone https://github.com/yourusername/epica-saas.git
cd epica-saas

# Deploy script'i çalıştır (root olarak)
chmod +x deploy.sh
sudo ./deploy.sh
```

### Domain Ayarları
DNS kayıtlarında şu ayarları yapın:
```
A     epica.com.tr        → SERVER_IP
CNAME *.epica.com.tr      → epica.com.tr
MX    epica.com.tr        → mail.epica.com.tr (email için)
```

## 🔧 Development

### Local Development
```bash
# Sanal ortam oluştur
python3 -m venv venv
source venv/bin/activate

# Dependencies yükle
pip install -r requirements_saas.txt

# Environment ayarla
cp .env.example .env
# .env dosyasını düzenle

# Database oluştur
python app_saas.py

# Development server başlat
flask --app app_saas run --debug --host=0.0.0.0 --port=5000
```

### Test Tenants
Development için test tenant'ları:
- `demo.epica.com.tr` (demo / demo123)
- `test.epica.com.tr` (admin / admin123)

## 📊 Monitoring ve Backup

### Monitoring
- **Health Check**: `/health` endpoint
- **System Monitor**: 5 dakikada bir otomatik kontrol
- **Log Files**: 
  - Application: `/var/log/epica/`
  - Nginx: `/var/log/nginx/`
  - System: `journalctl -u epica`

### Backup
- **Otomatik Backup**: Her gece 02:00'da
- **Database**: PostgreSQL dump
- **Files**: Application dosyaları
- **Retention**: 7 gün tutma süresi

### Analytics
- **Usage Stats**: Her tenant için kullanım istatistikleri
- **Performance**: Response time ve error tracking
- **Business Metrics**: Churn rate, usage growth

## 🔄 Migration

### Mevcut Sistemden Geçiş
1. **Veri Export**: CSV/JSON formatında
2. **Tenant Oluşturma**: Platform admin'den
3. **Data Import**: API veya bulk import
4. **User Training**: Yeni sistem eğitimi

### API Integration
```python
# API Example
import requests

# Tenant API key ile auth
headers = {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
}

# Müşteri oluştur
response = requests.post(
    'https://yourcompany.epica.com.tr/api/customers',
    headers=headers,
    json={
        'company_name': 'ABC Ltd.',
        'contact_email': 'info@abc.com'
    }
)
```

## 💰 Pricing Model

### Revenue Sharing
- Platform sahibi: Ana gelir
- Referans sistemi: %10 komisyon
- Enterprise deals: Özel fiyatlandırma

### Payment Processing
- Stripe entegrasyonu
- Otomatik faturalandırma
- Türk Lirası ve döviz desteği
- KDV hesaplama

## 🚀 Growth Strategy

### Marketing
- SEO optimizasyonu
- Content marketing
- Webinar ve demo'lar
- Partner program

### Enterprise Sales
- Custom branding
- On-premise deployment
- Dedicated support
- SLA agreements

## 📞 Support

### Customer Support
- 7/24 Türkçe destek
- Canlı chat (Intercom)
- Telefon desteği
- Email support
- Dokümantasyon sitesi

### Technical Support
- API dokümantasyonu
- Integration assistance
- Custom development
- Training programs

Bu SaaS sistemi ile:
✅ Çok kiracılı güvenli mimari
✅ Ölçeklenebilir altyapı
✅ Abonelik tabanlı gelir modeli
✅ Enterprise ready özellikler
✅ Otomatik deployment ve monitoring
✅ Tam güvenlik önlemleri
