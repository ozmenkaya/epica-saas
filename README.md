# Teklif Arayüzü

Modern, kullanıcı dostu bir teklif yönetim sistemi. Flask framework'ü ile geliştirilmiş, Bootstrap 5 frontend'i ve SQLite veritabanı kullanılmaktadır.

## Özellikler

- **Kullanıcı Kimlik Doğrulama**: Flask-Login ile güvenli giriş/çıkış sistemi
- **Teklif Yönetimi**: Teklif oluşturma, düzenleme, görüntüleme ve silme
- **Kalem Yönetimi**: Tekliflere kalem ekleme/çıkarma, otomatik toplam hesaplama
- **Dashboard**: Görsel grafik ve istatistiklerle genel bakış (Chart.js)
- **Responsive Tasarım**: Bootstrap 5 ile mobil uyumlu arayüz
- **Durum Takibi**: Taslak, Gönderildi, Onaylandı, Reddedildi durumları

## Teknoloji Stack'i

### Backend
- **Python Flask**: Web framework
- **SQLAlchemy**: ORM (Object-Relational Mapping)
- **Flask-Login**: Kimlik doğrulama
- **SQLite**: Veritabanı

### Frontend
- **Bootstrap 5**: CSS framework
- **Chart.js**: Grafik kütüphanesi
- **Bootstrap Icons**: İkon seti
- **JavaScript**: İnteraktif özellikler

## Kurulum

### Gereksinimler
- Python 3.8+
- pip (Python package manager)

### Adımlar

1. **Projeyi klonlayın:**
```bash
git clone <repository-url>
cd epica
```

2. **Virtual environment oluşturun:**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# veya
.venv\Scripts\activate  # Windows
```

3. **Gerekli paketleri yükleyin:**
```bash
pip install -r requirements.txt
```

4. **Uygulamayı çalıştırın:**
```bash
python app.py
```

5. **Tarayıcınızda açın:**
```
http://localhost:5000
```

## Varsayılan Kullanıcı

Uygulama ilk çalıştırıldığında otomatik olarak bir admin kullanıcısı oluşturulur:

- **Email**: admin@admin.com
- **Şifre**: admin123

## Proje Yapısı

```
epica/
├── app.py                 # Ana uygulama dosyası
├── models.py              # Veritabanı modelleri (kullanılmıyor - app.py içinde)
├── routes.py              # URL routes (kullanılmıyor - app.py içinde)
├── requirements.txt       # Python dependencies
├── README.md             # Proje dokümantasyonu
├── templates/            # Jinja2 templates
│   ├── base.html         # Ana template
│   ├── index.html        # Ana sayfa
│   ├── dashboard.html    # Dashboard
│   ├── auth/             # Kimlik doğrulama sayfaları
│   │   ├── login.html
│   │   └── register.html
│   └── proposals/        # Teklif sayfaları
│       ├── list.html     # Teklif listesi
│       ├── new.html      # Yeni teklif
│       ├── view.html     # Teklif görüntüleme
│       └── edit.html     # Teklif düzenleme
├── static/               # CSS, JS, resim dosyaları
└── teklif_arayuzu.db     # SQLite veritabanı (otomatik oluşur)
```

## Veritabanı Modelleri

### User (Kullanıcı)
- id, username, email, password_hash, role, created_at
- İlişkiler: proposals (bir kullanıcının birden fazla teklifi olabilir)

### Proposal (Teklif)
- id, title, description, client_name, client_email, client_phone
- status, total_amount, created_at, updated_at, user_id
- İlişkiler: creator (User), items (ProposalItem)

### ProposalItem (Teklif Kalemi)
- id, name, description, quantity, unit_price, total_price, proposal_id
- İlişkiler: proposal (Proposal)

## API Endpoints

### Kimlik Doğrulama
- `GET /` - Ana sayfa
- `GET|POST /login` - Giriş yapma
- `GET|POST /register` - Kayıt olma
- `GET /logout` - Çıkış yapma

### Dashboard & Teklifler
- `GET /dashboard` - Dashboard
- `GET /proposals` - Teklif listesi
- `GET|POST /proposal/new` - Yeni teklif
- `GET /proposal/<id>` - Teklif görüntüleme
- `GET /proposal/<id>/edit` - Teklif düzenleme
- `POST /proposal/<id>/delete` - Teklif silme

### API (JSON)
- `GET|POST /api/proposal/<id>/items` - Teklif kalemleri
- `PUT|DELETE /api/proposal/<id>/item/<item_id>` - Kalem güncelleme/silme
- `GET /api/dashboard/stats` - Dashboard istatistikleri

## Geliştirme

### Yeni Özellik Ekleme
1. Veritabanı değişikliği gerekiyorsa modelleri güncelleyin
2. Route'ları app.py'a ekleyin
3. Template'leri oluşturun/güncelleyin
4. Frontend JavaScript kodları ekleyin

### Güvenlik
- Gizli anahtar (SECRET_KEY) production'da değiştirilmeli
- HTTPS kullanılmalı
- Rate limiting eklenebilir
- Input validation güçlendirilebilir

## Deployment

### DigitalOcean Deployment İçin
1. Droplet oluşturun (Ubuntu 20.04+)
2. Gerekli paketleri yükleyin (Python, Nginx, uWSGI)
3. Projeyi klonlayın
4. Virtual environment kurun
5. uWSGI ve Nginx yapılandırın
6. SSL sertifikası ekleyin (Let's Encrypt)

### Çevre Değişkenleri
Production'da şu değişkenler ayarlanmalı:
```bash
export FLASK_ENV=production
export SECRET_KEY=your-super-secret-key
export DATABASE_URL=your-database-url
```

## Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## Destek

Herhangi bir sorun yaşarsanız veya öneriniz varsa lütfen issue açın.
