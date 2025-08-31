# Domain DNS Ayar Rehberi

## 🌐 Domain Hazır Olduğunda Yapılacak DNS Ayarları

### Digital Ocean Droplet IP: **104.248.26.69**

---

## 📋 DNS Kayıtları (Domain sağlayıcınızda ekleyin)

### Ana Domain Kayıtları:
```
Kayıt Tipi: A
Host: @
Değer: 104.248.26.69
TTL: 300 (5 dakika)

Kayıt Tipi: A  
Host: www
Değer: 104.248.26.69
TTL: 300
```

### Subdomain Kayıtları (Multi-tenant için):
```
Kayıt Tipi: A
Host: *
Değer: 104.248.26.69
TTL: 300

# Bu wildcard kayıt şunları sağlar:
# test.epica.com.tr -> 104.248.26.69
# sirket1.epica.com.tr -> 104.248.26.69
# herhangi.epica.com.tr -> 104.248.26.69
```

---

## 🎯 Domain Sağlayıcısına Göre Ayar Örnekleri

### **Turhost.com** (Türkiye):
1. Turhost paneline girin
2. "DNS Yönetimi" bölümüne gidin
3. Aşağıdaki kayıtları ekleyin:

```
A     @           104.248.26.69    300
A     www         104.248.26.69    300  
A     *           104.248.26.69    300
```

### **GoDaddy**:
1. GoDaddy hesabınıza girin
2. "My Products" > "DNS" 
3. Kayıtları ekleyin:

```
Type: A, Name: @, Value: 104.248.26.69
Type: A, Name: www, Value: 104.248.26.69
Type: A, Name: *, Value: 104.248.26.69
```

### **Cloudflare** (Önerilen):
1. Domain'i Cloudflare'e transfer edin
2. DNS kayıtlarını ekleyin:

```
Type: A, Name: epica.com.tr, Content: 104.248.26.69, Proxy: Orange (Proxied)
Type: A, Name: www, Content: 104.248.26.69, Proxy: Orange
Type: A, Name: *, Content: 104.248.26.69, Proxy: Gray (DNS Only)
```

**Not**: Wildcard subdomain için Cloudflare'de "DNS Only" modunu kullanın.

---

## ⏱️ DNS Propagation Süresi

- **Turhost**: 30 dakika - 2 saat
- **GoDaddy**: 1-24 saat  
- **Cloudflare**: 2-5 dakika

### DNS Propagation Test:
```bash
# Ana domain test
nslookup epica.com.tr

# Subdomain test  
nslookup test.epica.com.tr

# Beklenen sonuç: 104.248.26.69
```

---

## 🚀 Domain Hazır Olunca Deployment

### 1. Sunucuya Bağlan:
```bash
ssh root@104.248.26.69
```

### 2. Domain ile Deploy:
```bash
cd epica
./deploy.sh epica.com.tr
```

### 3. Test URL'leri:
```
✅ Ana Platform: https://epica.com.tr
✅ Admin Panel: https://epica.com.tr/admin/login  
✅ Fiyat Planları: https://epica.com.tr/pricing
✅ Tenant Test: https://test.epica.com.tr
```

---

## 🔧 Troubleshooting

### DNS Çalışmıyor mu?
```bash
# DNS test komutları
dig epica.com.tr
dig test.epica.com.tr
dig www.epica.com.tr

# Global DNS test: https://dnschecker.org
```

### SSL Sertifikası Sorunu:
```bash
# Sunucuda SSL kontrol
sudo certbot certificates
sudo certbot renew --dry-run
```

### Subdomain Çalışmıyor:
- Wildcard (*) kaydının doğru eklendiğini kontrol edin
- TTL değerini düşürün (300 saniye)
- DNS propagation süresini bekleyin

---

## 📞 Destek

Domain ayarlarında sorun yaşarsanız:
1. Domain sağlayıcısının destek hattını arayın
2. DNS ayarlarının ekran görüntüsünü alın
3. 24 saat sonra hala çalışmıyorsa teknik destek isteyin

**Domain hazır olduğunda tek komutla production'a geçiyoruz! 🎉**
