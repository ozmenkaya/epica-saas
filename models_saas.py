# Multi-Tenant SaaS Models for Epica
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
import secrets
import string

db = SQLAlchemy()

# Tenant (Firma) Model - Her abonen firma için
class Tenant(db.Model):
    __tablename__ = 'tenants'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=False)  # firma.epica.com.tr
    domain = db.Column(db.String(100), nullable=True)  # Özel domain (opsiyonel)
    
    # İletişim Bilgileri
    contact_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(20))
    
    # Adres Bilgileri
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    country = db.Column(db.String(50), default='Türkiye')
    
    # Abonelik Bilgileri
    subscription_plan = db.Column(db.String(20), default='basic')  # basic, pro, enterprise
    subscription_status = db.Column(db.String(20), default='trial')  # trial, active, suspended, cancelled
    subscription_start = db.Column(db.DateTime, default=datetime.utcnow)
    subscription_end = db.Column(db.DateTime)
    monthly_fee = db.Column(db.Float, default=0.0)
    
    # Limitler
    max_users = db.Column(db.Integer, default=5)
    max_customers = db.Column(db.Integer, default=50)
    max_suppliers = db.Column(db.Integer, default=20)
    max_products = db.Column(db.Integer, default=500)
    max_monthly_requests = db.Column(db.Integer, default=100)
    
    # Güvenlik
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Zaman Damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    users = db.relationship('User', backref='tenant', lazy=True, cascade='all, delete-orphan')
    customers = db.relationship('Customer', backref='tenant', lazy=True, cascade='all, delete-orphan')
    suppliers = db.relationship('Supplier', backref='tenant', lazy=True, cascade='all, delete-orphan')
    products = db.relationship('Product', backref='tenant', lazy=True, cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='tenant', lazy=True, cascade='all, delete-orphan')
    price_requests = db.relationship('PriceRequest', backref='tenant', lazy=True, cascade='all, delete-orphan')
    proposals = db.relationship('Proposal', backref='tenant', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.api_key:
            self.api_key = self.generate_api_key()
    
    def generate_api_key(self):
        """Benzersiz API key oluştur"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
    
    @property
    def full_domain(self):
        """Tam domain adresini döndür"""
        if self.domain:
            return self.domain
        return f"{self.subdomain}.epica.com.tr"
    
    @property
    def is_subscription_active(self):
        """Abonelik aktif mi kontrol et"""
        if self.subscription_status != 'active':
            return False
        if self.subscription_end and self.subscription_end < datetime.utcnow():
            return False
        return True
    
    def get_usage_stats(self):
        """Kullanım istatistiklerini döndür"""
        return {
            'users_count': len(self.users),
            'customers_count': len(self.customers),
            'suppliers_count': len(self.suppliers),
            'products_count': len(self.products),
            'price_requests_count': len(self.price_requests),
            'proposals_count': len(self.proposals)
        }
    
    def check_limits(self, resource_type):
        """Kaynak limitlerini kontrol et"""
        stats = self.get_usage_stats()
        limits = {
            'users': self.max_users,
            'customers': self.max_customers,
            'suppliers': self.max_suppliers,
            'products': self.max_products
        }
        
        current_count = stats.get(f'{resource_type}_count', 0)
        max_count = limits.get(resource_type, 0)
        
        return current_count < max_count
    
    def __repr__(self):
        return f'<Tenant {self.company_name}>'

# Kullanıcı Modeli - Tenant'a bağlı
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Kişisel Bilgiler
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    
    # Yetki ve Durum
    role = db.Column(db.String(20), default='admin')  # admin, manager, user
    is_active = db.Column(db.Boolean, default=True)
    is_tenant_admin = db.Column(db.Boolean, default=False)  # Firma admin'i mi?
    
    # Giriş Bilgileri
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    
    # Zaman Damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    proposals = db.relationship('Proposal', backref='creator', lazy=True)
    
    # Tenant ile benzersizlik
    __table_args__ = (db.UniqueConstraint('tenant_id', 'username', name='_tenant_username_uc'),
                      db.UniqueConstraint('tenant_id', 'email', name='_tenant_email_uc'),)
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def __repr__(self):
        return f'<User {self.username} @ {self.tenant.company_name}>'

# Müşteri Modeli - Tenant'a bağlı
class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    
    # Şirket Bilgileri
    company_name = db.Column(db.String(200), nullable=False)
    tax_number = db.Column(db.String(20))
    tax_office = db.Column(db.String(100))
    
    # İletişim Bilgileri
    contact_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(20))
    
    # Adres Bilgileri
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    country = db.Column(db.String(50), default='Türkiye')
    
    # Portal Erişimi
    portal_access = db.Column(db.Boolean, default=True)
    portal_password_hash = db.Column(db.String(255))
    last_portal_login = db.Column(db.DateTime)
    
    # Durum
    is_active = db.Column(db.Boolean, default=True)
    
    # Zaman Damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    price_requests = db.relationship('PriceRequest', backref='customer', lazy=True)
    proposals = db.relationship('Proposal', backref='customer', lazy=True)
    
    def __repr__(self):
        return f'<Customer {self.company_name} @ {self.tenant.company_name}>'

# Tedarikçi Modeli - Tenant'a bağlı
class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    
    # Şirket Bilgileri
    company_name = db.Column(db.String(200), nullable=False)
    tax_number = db.Column(db.String(20))
    tax_office = db.Column(db.String(100))
    
    # İletişim Bilgileri
    contact_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(20))
    
    # Adres Bilgileri
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    country = db.Column(db.String(50), default='Türkiye')
    
    # Portal Erişimi
    portal_access = db.Column(db.Boolean, default=True)
    portal_password_hash = db.Column(db.String(255))
    last_portal_login = db.Column(db.DateTime)
    
    # Uzmanlik Alanları
    specialties = db.Column(db.Text)  # JSON formatında kategoriler
    
    # Durum
    is_active = db.Column(db.Boolean, default=True)
    
    # Zaman Damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    quotes = db.relationship('SupplierQuote', backref='supplier', lazy=True)
    
    def __repr__(self):
        return f'<Supplier {self.company_name} @ {self.tenant.company_name}>'

# Kategori Modeli - Tenant'a bağlı
class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Hiyerarşi için parent-child ilişkisi
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    products = db.relationship('Product', backref='category', lazy=True)
    price_request_items = db.relationship('PriceRequestItem', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name} @ {self.tenant.company_name}>'

# Ürün Modeli - Tenant'a bağlı
class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Ürün Bilgileri
    sku = db.Column(db.String(50))  # Stok kodu
    barcode = db.Column(db.String(50))
    unit = db.Column(db.String(20), default='Adet')
    
    # Fiyat Bilgileri
    cost_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    currency = db.Column(db.String(3), default='TL')
    
    # Vergi ve Maliyet
    tax_rate = db.Column(db.Float, default=18.0)  # KDV oranı
    
    # Durum
    is_active = db.Column(db.Boolean, default=True)
    
    # Zaman Damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Product {self.name} @ {self.tenant.company_name}>'

# Ana SaaS platform için global modeller (tenant-independent)
class PlatformAdmin(UserMixin, db.Model):
    """Platform genel admin'leri için"""
    __tablename__ = 'platform_admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    
    is_super_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<PlatformAdmin {self.username}>'

class AuditLog(db.Model):
    """Sistem audit log'ları"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    
    user_type = db.Column(db.String(20))  # 'platform_admin', 'user', 'customer', 'supplier'
    user_id = db.Column(db.Integer)
    
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    
    old_values = db.Column(db.Text)  # JSON
    new_values = db.Column(db.Text)  # JSON
    
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_type}:{self.user_id}>'

# Fiyat talebi ve diğer mevcut modeller de tenant_id ile güncellenecek...

# Fiyat Talebi Modeli - Tenant'a bağlı
class PriceRequest(db.Model):
    __tablename__ = 'price_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Teklif Detayları
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    deadline = db.Column(db.Date)
    
    # Durum Takibi
    status = db.Column(db.String(20), default='draft')  # draft, sent, assigned, quoted, closed
    
    # Atama Bilgileri
    assigned_suppliers = db.Column(db.Text)  # JSON - Hangi tedarikçilere gönderildi
    
    # Zaman Damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = db.Column(db.DateTime)  # Tedarikçilere gönderilme tarihi
    
    # İlişkiler
    items = db.relationship('PriceRequestItem', backref='price_request', lazy=True, cascade='all, delete-orphan')
    quotes = db.relationship('SupplierQuote', backref='price_request', lazy=True)
    
    @property
    def status_text(self):
        status_map = {
            'draft': 'Taslak',
            'sent': 'Gönderildi',
            'assigned': 'Tedarikçiye Atandı',
            'quoted': 'Teklif Alındı',
            'closed': 'Kapatıldı'
        }
        return status_map.get(self.status, self.status)
    
    @property
    def priority_text(self):
        priority_map = {
            'low': 'Düşük',
            'normal': 'Normal',
            'high': 'Yüksek',
            'urgent': 'Acil'
        }
        return priority_map.get(self.priority, self.priority)
    
    def calculate_total_budget(self):
        total_min = sum(item.budget_min or 0 for item in self.items)
        total_max = sum(item.budget_max or 0 for item in self.items)
        return {'min': total_min, 'max': total_max}
    
    def __repr__(self):
        return f'<PriceRequest {self.title} @ {self.tenant.company_name}>'

class PriceRequestItem(db.Model):
    __tablename__ = 'price_request_items'
    
    id = db.Column(db.Integer, primary_key=True)
    price_request_id = db.Column(db.Integer, db.ForeignKey('price_requests.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Miktar ve Birim
    quantity = db.Column(db.Float, default=1.0)
    unit = db.Column(db.String(20), default='Adet')
    
    # Bütçe Bilgileri
    budget_min = db.Column(db.Float)
    budget_max = db.Column(db.Float)
    currency = db.Column(db.String(3), default='TL')
    
    # Teknik Özellikler
    specifications = db.Column(db.Text)  # JSON formatında
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PriceRequestItem {self.name}>'

# Teklif Modeli - Tenant'a bağlı (Customer Proposals)
class Proposal(db.Model):
    __tablename__ = 'proposals'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Teklifi hazırlayan kullanıcı
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Müşteri Bilgileri (Kopya - Değişebilir)
    client_name = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(120))
    client_phone = db.Column(db.String(20))
    
    # Teklif Detayları
    status = db.Column(db.String(20), default='draft')  # draft, sent, approved, rejected, expired
    validity_days = db.Column(db.Integer, default=30)  # Geçerlilik süresi
    
    # Finansal Bilgiler
    total_amount = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='TL')
    
    # Koşullar
    payment_terms = db.Column(db.Text)  # Ödeme koşulları
    delivery_terms = db.Column(db.Text)  # Teslimat koşulları
    warranty_terms = db.Column(db.Text)  # Garanti koşulları
    
    # Zaman Damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    
    # İlişkiler
    items = db.relationship('ProposalItem', backref='proposal', lazy=True, cascade='all, delete-orphan')
    
    @property
    def status_text(self):
        status_map = {
            'draft': 'Taslak',
            'sent': 'Gönderildi',
            'approved': 'Onaylandı',
            'rejected': 'Reddedildi',
            'expired': 'Süresi Doldu'
        }
        return status_map.get(self.status, self.status)
    
    @property
    def is_expired(self):
        if not self.sent_at or not self.validity_days:
            return False
        expiry_date = self.sent_at + timedelta(days=self.validity_days)
        return datetime.utcnow() > expiry_date
    
    def calculate_total(self):
        total = sum(item.total_price for item in self.items)
        subtotal = sum(item.subtotal for item in self.items)
        total_tax = sum(item.tax_amount for item in self.items)
        self.total_amount = total
        return {
            'subtotal': subtotal,
            'tax_amount': total_tax,
            'total': total
        }
    
    def __repr__(self):
        return f'<Proposal {self.title} @ {self.tenant.company_name}>'

class ProposalItem(db.Model):
    __tablename__ = 'proposal_items'
    
    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'), nullable=False)
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Miktar ve Birim
    quantity = db.Column(db.Float, default=1.0)
    unit = db.Column(db.String(20), default='Adet')
    
    # Fiyat Bilgileri
    unit_price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='TL')
    
    # Vergi Bilgileri
    tax_rate = db.Column(db.Float, default=18.0)  # KDV oranı
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def subtotal(self):
        return self.quantity * self.unit_price
    
    @property
    def tax_amount(self):
        return self.subtotal * (self.tax_rate / 100)
    
    @property
    def total_price(self):
        return self.subtotal + self.tax_amount
    
    def __repr__(self):
        return f'<ProposalItem {self.name}>'

# Tedarikçi Teklifi Modeli - Tenant'a bağlı
class SupplierQuote(db.Model):
    __tablename__ = 'supplier_quotes'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    price_request_id = db.Column(db.Integer, db.ForeignKey('price_requests.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    
    # Teklif Bilgileri
    title = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text)
    
    # Finansal Toplam
    total_amount = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='TL')
    
    # Koşullar
    validity_days = db.Column(db.Integer, default=30)
    payment_terms = db.Column(db.Text)
    delivery_terms = db.Column(db.Text)
    
    # Durum
    status = db.Column(db.String(20), default='draft')  # draft, submitted, accepted, rejected
    
    # Zaman Damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    
    # İlişkiler
    items = db.relationship('SupplierQuoteItem', backref='quote', lazy=True, cascade='all, delete-orphan')
    
    @property
    def status_text(self):
        status_map = {
            'draft': 'Taslak',
            'submitted': 'Gönderildi',
            'accepted': 'Kabul Edildi',
            'rejected': 'Reddedildi'
        }
        return status_map.get(self.status, self.status)
    
    def calculate_total(self):
        total = sum(item.total_price for item in self.items)
        self.total_amount = total
        return total
    
    def __repr__(self):
        return f'<SupplierQuote {self.title} by {self.supplier.company_name}>'

class SupplierQuoteItem(db.Model):
    __tablename__ = 'supplier_quote_items'
    
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('supplier_quotes.id'), nullable=False)
    price_request_item_id = db.Column(db.Integer, db.ForeignKey('price_request_items.id'), nullable=False)
    
    # Teklif Edilen Ürün/Hizmet
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    brand = db.Column(db.String(100))  # Marka
    model = db.Column(db.String(100))  # Model
    
    # Miktar ve Birim
    quantity = db.Column(db.Float, default=1.0)
    unit = db.Column(db.String(20), default='Adet')
    
    # Fiyat Bilgileri
    unit_price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='TL')
    
    # Vergi
    tax_rate = db.Column(db.Float, default=18.0)
    
    # Teslimat
    delivery_time = db.Column(db.String(100))  # Teslimat süresi
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def subtotal(self):
        return self.quantity * self.unit_price
    
    @property
    def tax_amount(self):
        return self.subtotal * (self.tax_rate / 100)
    
    @property
    def total_price(self):
        return self.subtotal + self.tax_amount
    
    def __repr__(self):
        return f'<SupplierQuoteItem {self.name}>'
