from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, inch
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.platypus import Table, TableStyle
from io import BytesIO

# Flask uygulamasını oluştur
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teklif_arayuzu.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Jinja2 custom filters
@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to <br> tags"""
    if text:
        return text.replace('\n', '<br>')
    return text

# Extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Bu sayfaya erişmek için giriş yapmanız gerekir.'
login_manager.login_message_category = 'info'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')  # admin, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    proposals = db.relationship('Proposal', backref='creator', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Proposal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    client_name = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(120))
    client_phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='draft')  # draft, sent, approved, rejected
    total_amount = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='TL')  # Para birimi: TL, EUR, USD, GBP
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)  # Opsiyonel müşteri bağlantısı
    
    # İlişkiler
    items = db.relationship('ProposalItem', backref='proposal', lazy=True, cascade='all, delete-orphan')
    
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
    
    def get_currency_symbol(self):
        """Para birimi sembolünü döndür"""
        currency_symbols = {
            'TL': '₺',
            'EUR': '€',
            'USD': '$',
            'GBP': '£'
        }
        return currency_symbols.get(self.currency, '₺')
    
    def __repr__(self):
        return f'<Proposal {self.title}>'

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    company = db.Column(db.String(100))
    tax_number = db.Column(db.String(50))
    notes = db.Column(db.Text)
    
    # Giriş sistemi için
    password = db.Column(db.String(200))  # Şifre hash'i
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # İlişkiler
    proposals = db.relationship('Proposal', backref='customer_info', lazy=True)
    
    def check_password(self, password):
        """Şifre kontrolü"""
        if self.password:
            return check_password_hash(self.password, password)
        return False
    
    def get_id(self):
        """Flask-Login için gerekli"""
        return str(self.id)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def __repr__(self):
        return f'<Customer {self.name}>'

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    tax_number = db.Column(db.String(50))
    website = db.Column(db.String(200))
    contact_person = db.Column(db.String(100))  # İletişim kişisi
    payment_terms = db.Column(db.String(100))  # Ödeme koşulları (30 gün, 60 gün vb.)
    category = db.Column(db.String(50))  # Tedarikçi kategorisi (Yazılım, Donanım, Hizmet vb.)
    rating = db.Column(db.Integer, default=5)  # 1-5 arası değerlendirme
    is_active = db.Column(db.Boolean, default=True)  # Aktif/Pasif durumu
    notes = db.Column(db.Text)
    
    # Giriş sistemi için
    password = db.Column(db.String(200))  # Şifre hash'i
    last_login = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # İlişkiler - Supplier'dan Proposal'a doğrudan bağlantı yok, Product üzerinden
    products = db.relationship('Product', backref='supplier_info', lazy=True)
    
    def check_password(self, password):
        """Şifre kontrolü"""
        if self.password:
            return check_password_hash(self.password, password)
        return False
    
    def get_id(self):
        """Flask-Login için gerekli"""
        return str(self.id)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def __repr__(self):
        return f'<Supplier {self.name}>'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # İlişkiler
    products = db.relationship('Product', backref='supplier_info', lazy=True)
    
    def __repr__(self):
        return f'<Supplier {self.company}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#6c757d')  # Bootstrap renk kodu
    icon = db.Column(db.String(50), default='bi-tag')  # Bootstrap icon sınıfı
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # İlişkiler
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(100), unique=True)  # Stok Kodu (Stock Keeping Unit)
    unit = db.Column(db.String(50), default='Adet')  # Birim (Adet, Kg, Litre, Metre vb.)
    purchase_price = db.Column(db.Float, default=0.0)  # Alış fiyatı
    sale_price = db.Column(db.Float, default=0.0)  # Satış fiyatı
    tax_rate = db.Column(db.Float, default=20.0)  # KDV oranı
    stock_quantity = db.Column(db.Integer, default=0)  # Stok miktarı
    min_stock_level = db.Column(db.Integer, default=0)  # Minimum stok seviyesi
    barcode = db.Column(db.String(100))  # Barkod
    brand = db.Column(db.String(100))  # Marka
    model = db.Column(db.String(100))  # Model
    specifications = db.Column(db.Text)  # Teknik özellikler (JSON formatında)
    is_active = db.Column(db.Boolean, default=True)  # Aktif/Pasif durumu
    is_service = db.Column(db.Boolean, default=False)  # Ürün mü hizmet mi?
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))  # Kategori ID
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)  # Tedarikçi bağlantısı
    
    def __repr__(self):
        return f'<Product {self.name}>'
    
    @property
    def profit_margin(self):
        """Kar marjını hesapla"""
        if self.purchase_price > 0:
            return ((self.sale_price - self.purchase_price) / self.purchase_price) * 100
        return 0
    
    @property
    def is_low_stock(self):
        """Stok seviyesi düşük mü?"""
        return self.stock_quantity <= self.min_stock_level
    
    def calculate_total_with_tax(self, quantity=1):
        """Vergi dahil toplam fiyatı hesapla"""
        subtotal = self.sale_price * quantity
        tax_amount = subtotal * (self.tax_rate / 100)
        return subtotal + tax_amount
    
    # İlişkiler (Product modelinin sonuna ekle)
    proposal_items = db.relationship('ProposalItem', backref='product_info', lazy=True)

class PriceRequest(db.Model):
    """Müşteri Fiyat Talebi Modeli"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # Talep başlığı
    description = db.Column(db.Text, nullable=False)  # Detaylı açıklama
    deadline = db.Column(db.Date)  # Teslim tarihi
    additional_notes = db.Column(db.Text)  # Ek notlar
    
    # Durum takibi
    status = db.Column(db.String(50), default='pending')  # pending, approved, assigned, completed, cancelled
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    
    # Admin değerlendirmesi
    admin_notes = db.Column(db.Text)  # Admin notları
    approved_at = db.Column(db.DateTime)  # Onaylanma tarihi
    assigned_at = db.Column(db.DateTime)  # Tedarikçiye atanma tarihi
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    assigned_supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Admin kullanıcısı
    
    # İlişkiler
    customer = db.relationship('Customer', backref='price_requests')
    assigned_supplier = db.relationship('Supplier', backref='assigned_requests')
    category = db.relationship('Category', backref='price_requests')
    user = db.relationship('User', backref='price_requests')
    
    def __repr__(self):
        return f'<PriceRequest {self.title}>'
    
    @property
    def status_badge_class(self):
        """Durum için Bootstrap badge class'ı"""
        status_classes = {
            'draft': 'bg-secondary',
            'pending': 'bg-warning',
            'approved': 'bg-info', 
            'assigned': 'bg-primary',
            'completed': 'bg-success',
            'cancelled': 'bg-danger'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    @property
    def status_text(self):
        """Durum metni (Türkçe)"""
        status_texts = {
            'draft': 'Taslak',
            'pending': 'Beklemede',
            'approved': 'Onaylandı',
            'assigned': 'Tedarikçiye Atandı', 
            'completed': 'Tamamlandı',
            'cancelled': 'İptal Edildi'
        }
        return status_texts.get(self.status, 'Bilinmiyor')
    
    @property
    def priority_badge_class(self):
        """Öncelik için badge class'ı"""
        priority_classes = {
            'low': 'bg-secondary',
            'normal': 'bg-info',
            'high': 'bg-warning',
            'urgent': 'bg-danger'
        }
        return priority_classes.get(self.priority, 'bg-info')

class PriceRequestItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price_request_id = db.Column(db.Integer, db.ForeignKey('price_request.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit = db.Column(db.String(50), nullable=False, default='Adet')
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    budget_min = db.Column(db.Float, nullable=True)  # Minimum bütçe
    budget_max = db.Column(db.Float, nullable=True)  # Maksimum bütçe
    supplier_quote = db.Column(db.Float, nullable=True)  # Tedarikçi teklifi
    supplier_notes = db.Column(db.Text)  # Tedarikçi notları
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    price_request = db.relationship('PriceRequest', backref='items')
    category = db.relationship('Category', backref='price_request_items')
    
    def __repr__(self):
        return f'<PriceRequestItem {self.name}>'
    
    @property
    def budget_range_text(self):
        """Bütçe aralığını metin olarak döndür"""
        if self.budget_min and self.budget_max:
            return f"{self.budget_min:,.0f} - {self.budget_max:,.0f} TL"
        elif self.budget_min:
            return f"{self.budget_min:,.0f}+ TL"
        elif self.budget_max:
            return f"Maks {self.budget_max:,.0f} TL"
        return "Belirtilmedi"
    
    @property
    def total_budget_min(self):
        """Toplam minimum bütçe (miktar × min)"""
        return (self.budget_min * self.quantity) if self.budget_min else None
    
    @property
    def total_budget_max(self):
        """Toplam maksimum bütçe (miktar × max)"""
        return (self.budget_max * self.quantity) if self.budget_max else None
    
    @property
    def supplier_total_quote(self):
        """Tedarikçi toplam teklifi (miktar × birim fiyat)"""
        return (self.supplier_quote * self.quantity) if self.supplier_quote else None

class ProposalItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    tax_rate = db.Column(db.Float, default=20.0)  # KDV oranı (%)
    subtotal = db.Column(db.Float)  # Vergi öncesi toplam
    tax_amount = db.Column(db.Float)  # Vergi tutarı
    total_price = db.Column(db.Float)  # Vergi dahil toplam
    
    # Foreign Keys
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposal.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)  # Ürün referansı (opsiyonel)
    
    def __init__(self, **kwargs):
        super(ProposalItem, self).__init__(**kwargs)
        self.calculate_total()
    
    def calculate_total(self):
        self.subtotal = self.quantity * self.unit_price
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total_price = self.subtotal + self.tax_amount
        return self.total_price
    
    def __repr__(self):
        return f'<ProposalItem {self.name}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Geçersiz email veya şifre!', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Kullanıcı zaten var mı kontrol et
        if User.query.filter_by(email=email).first():
            flash('Bu email adresi zaten kayıtlı!', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı zaten alınmış!', 'error')
            return render_template('auth/register.html')
        
        # Yeni kullanıcı oluştur
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Başarıyla çıkış yaptınız!', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    proposals = Proposal.query.filter_by(user_id=current_user.id).order_by(Proposal.created_at.desc()).all()
    
    # Fiyat talepleri istatistikleri
    price_requests = PriceRequest.query.filter_by(user_id=current_user.id).order_by(PriceRequest.created_at.desc()).all()
    pending_requests = len([pr for pr in price_requests if pr.status == 'pending'])
    
    # İstatistikler
    total_proposals = len(proposals)
    draft_count = len([p for p in proposals if p.status == 'draft'])
    sent_count = len([p for p in proposals if p.status == 'sent'])
    approved_count = len([p for p in proposals if p.status == 'approved'])
    
    total_value = sum(p.total_amount for p in proposals if p.status == 'approved')
    
    stats = {
        'total': total_proposals,
        'draft': draft_count,
        'sent': sent_count,
        'approved': approved_count,
        'total_value': total_value,
        'pending_requests': pending_requests
    }
    
    return render_template('dashboard.html', proposals=proposals, stats=stats, price_requests=price_requests[:5])

@app.route('/proposals')
@login_required
def proposals():
    proposals = Proposal.query.filter_by(user_id=current_user.id).order_by(Proposal.created_at.desc()).all()
    return render_template('proposals/list.html', proposals=proposals)

@app.route('/proposal/new', methods=['GET', 'POST'])
@login_required
def new_proposal():
    if request.method == 'POST':
        # Müşteri seçimi varsa customer_id'yi belirle
        customer_id = None
        selected_customer_id = request.form.get('customer_select')
        if selected_customer_id:
            customer_id = int(selected_customer_id)
        
        proposal = Proposal(
            title=request.form['title'],
            description=request.form['description'],
            client_name=request.form['client_name'],
            client_email=request.form['client_email'],
            client_phone=request.form['client_phone'],
            currency=request.form.get('currency', 'TL'),
            user_id=current_user.id,
            customer_id=customer_id
        )
        
        db.session.add(proposal)
        db.session.commit()
        
        flash('Teklif başarıyla oluşturuldu!', 'success')
        return redirect(url_for('edit_proposal', id=proposal.id))
    
    return render_template('proposals/new.html')

@app.route('/proposal/<int:id>')
@login_required
def view_proposal(id):
    proposal = Proposal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('proposals/view.html', proposal=proposal)

@app.route('/proposal/<int:id>/pdf')
@login_required
def proposal_pdf(id):
    proposal = Proposal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # PDF buffer oluştur
    buffer = BytesIO()
    
    # Yatay A4 sayfası oluştur
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Modern renkler
    primary_color = HexColor('#2563eb')  # Mavi
    secondary_color = HexColor('#64748b')  # Gri
    accent_color = HexColor('#06b6d4')  # Açık mavi
    
    # Üst header bölümü - koyu mavi arka plan
    p.setFillColor(primary_color)
    p.rect(0, height - 120, width, 120, fill=1)
    
    # Logo alanı (placeholder)
    p.setFillColor(white)
    p.rect(30, height - 100, 100, 60, fill=1)
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(primary_color)
    p.drawCentredString(80, height - 75, "LOGO")
    
    # Başlık bilgileri - beyaz yazı
    p.setFillColor(white)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(160, height - 60, "TEKLİF FORMU")
    
    p.setFont("Helvetica", 12)
    p.drawString(160, height - 85, f"Teklif No: #{proposal.id}")
    p.drawString(160, height - 105, f"Tarih: {proposal.created_at.strftime('%d.%m.%Y')}")
    
    # Sağ üst - durum badge
    status_text = {
        'draft': 'TASLAK',
        'sent': 'GÖNDERİLDİ', 
        'approved': 'ONAYLANDI',
        'rejected': 'REDDEDİLDİ'
    }.get(proposal.status, 'TASLAK')
    
    status_color = {
        'draft': HexColor('#fbbf24'),
        'sent': HexColor('#3b82f6'),
        'approved': HexColor('#10b981'),
        'rejected': HexColor('#ef4444')
    }.get(proposal.status, HexColor('#fbbf24'))
    
    p.setFillColor(status_color)
    p.roundRect(width - 150, height - 90, 120, 30, 5, fill=1)
    p.setFillColor(white)
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width - 90, height - 80, status_text)
    
    # Ana içerik alanı başlangıcı
    y_position = height - 150
    
    # İki kolon düzeni
    left_col_x = 40
    right_col_x = width / 2 + 20
    col_width = width / 2 - 60
    
    # Sol kolon - Teklif bilgileri
    p.setFillColor(black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(left_col_x, y_position, "Teklif Detayları")
    
    # Beyaz arka planlı kart
    p.setFillColor(HexColor('#f8fafc'))
    p.roundRect(left_col_x, y_position - 120, col_width, 110, 8, fill=1)
    
    p.setFillColor(black)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(left_col_x + 15, y_position - 30, "Başlık:")
    p.setFont("Helvetica", 12)
    p.drawString(left_col_x + 15, y_position - 50, proposal.title[:35])
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(left_col_x + 15, y_position - 75, "Para Birimi:")
    p.setFont("Helvetica", 12)
    p.drawString(left_col_x + 15, y_position - 95, f"{proposal.get_currency_symbol()} {proposal.currency}")
    
    # Sağ kolon - Müşteri bilgileri
    p.setFont("Helvetica-Bold", 16)
    p.drawString(right_col_x, y_position, "Müşteri Bilgileri")
    
    # Beyaz arka planlı kart
    p.setFillColor(HexColor('#f8fafc'))
    p.roundRect(right_col_x, y_position - 120, col_width, 110, 8, fill=1)
    
    p.setFillColor(black)
    if proposal.customer_info:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(right_col_x + 15, y_position - 30, "Firma:")
        p.setFont("Helvetica", 12)
        p.drawString(right_col_x + 15, y_position - 50, proposal.customer_info.name[:25])
        
        if proposal.customer_info.email:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(right_col_x + 15, y_position - 75, "E-posta:")
            p.setFont("Helvetica", 12)
            p.drawString(right_col_x + 15, y_position - 95, proposal.customer_info.email[:25])
    else:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(right_col_x + 15, y_position - 30, "Müşteri:")
        p.setFont("Helvetica", 12)
        p.drawString(right_col_x + 15, y_position - 50, proposal.client_name[:25])
        
        if proposal.client_email:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(right_col_x + 15, y_position - 75, "E-posta:")
            p.setFont("Helvetica", 12)
            p.drawString(right_col_x + 15, y_position - 95, proposal.client_email[:25])
    
    # Ürünler tablosu
    y_position -= 180
    
    p.setFont("Helvetica-Bold", 18)
    p.drawString(left_col_x, y_position, "Ürün Listesi")
    y_position -= 40
    
    if proposal.items:
        # Modern tablo header
        header_height = 35
        p.setFillColor(primary_color)
        p.roundRect(left_col_x, y_position - header_height, width - 80, header_height, 5, fill=1)
        
        # Tablo başlıkları
        p.setFillColor(white)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(left_col_x + 15, y_position - 20, "Ürün Adı")
        p.drawString(left_col_x + 200, y_position - 20, "Miktar")
        p.drawString(left_col_x + 280, y_position - 20, "Birim Fiyat")
        p.drawString(left_col_x + 380, y_position - 20, "KDV %")
        p.drawString(left_col_x + 460, y_position - 20, "Ara Toplam")
        p.drawString(left_col_x + 560, y_position - 20, "Toplam")
        
        y_position -= header_height + 10
        
        # Ürün satırları
        p.setFillColor(black)
        p.setFont("Helvetica", 10)
        row_height = 25
        
        total_subtotal = 0
        total_tax = 0
        total_amount = 0
        
        for i, item in enumerate(proposal.items):
            # Alternatif satır rengi
            if i % 2 == 0:
                p.setFillColor(HexColor('#f1f5f9'))
                p.rect(left_col_x, y_position - row_height, width - 80, row_height, fill=1)
            
            p.setFillColor(black)
            p.drawString(left_col_x + 15, y_position - 15, item.name[:25])
            p.drawString(left_col_x + 200, y_position - 15, str(item.quantity))
            p.drawString(left_col_x + 280, y_position - 15, f"{proposal.get_currency_symbol()}{item.unit_price:.2f}")
            p.drawString(left_col_x + 380, y_position - 15, f"%{item.tax_rate}")
            p.drawString(left_col_x + 460, y_position - 15, f"{proposal.get_currency_symbol()}{item.subtotal:.2f}")
            p.drawString(left_col_x + 560, y_position - 15, f"{proposal.get_currency_symbol()}{item.total_price:.2f}")
            
            total_subtotal += item.subtotal
            total_tax += item.tax_amount
            total_amount += item.total_price
            
            y_position -= row_height
            
            # Sayfa sonu kontrolü
            if y_position < 100:
                p.showPage()
                y_position = height - 100
        
        # Toplam bölümü
        y_position -= 20
        
        # Toplam arka planı
        p.setFillColor(HexColor('#f8fafc'))
        p.roundRect(left_col_x + 350, y_position - 90, width - 430, 85, 8, fill=1)
        
        p.setFillColor(black)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(left_col_x + 370, y_position - 20, "Ara Toplam:")
        p.drawRightString(left_col_x + 620, y_position - 20, f"{proposal.get_currency_symbol()}{total_subtotal:.2f}")
        
        p.drawString(left_col_x + 370, y_position - 40, "KDV Toplam:")
        p.drawRightString(left_col_x + 620, y_position - 40, f"{proposal.get_currency_symbol()}{total_tax:.2f}")
        
        # Genel toplam - vurgulu
        p.setFillColor(primary_color)
        p.roundRect(left_col_x + 360, y_position - 75, 270, 25, 5, fill=1)
        
        p.setFillColor(white)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(left_col_x + 370, y_position - 65, "GENEL TOPLAM:")
        p.drawRightString(left_col_x + 620, y_position - 65, f"{proposal.get_currency_symbol()}{total_amount:.2f}")
    
    # Footer
    p.setFillColor(secondary_color)
    p.setFont("Helvetica", 10)
    p.drawCentredString(width / 2, 30, f"Bu teklif {proposal.created_at.strftime('%d.%m.%Y')} tarihinde oluşturulmuştur.")
    p.drawCentredString(width / 2, 15, "Bu belge elektronik olarak oluşturulmuş olup imza gerektirmez.")
    
    # PDF'i kapat
    p.save()
    
    # Response oluştur
    pdf_data = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="teklif_{proposal.id}_{proposal.title[:20]}.pdf"'
    
    return response

@app.route('/proposal/<int:id>/edit')
@login_required
def edit_proposal(id):
    proposal = Proposal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    customers = Customer.query.filter_by(user_id=current_user.id).order_by(Customer.name.asc()).all()
    suppliers = Supplier.query.filter_by(user_id=current_user.id).order_by(Supplier.name.asc()).all()
    return render_template('proposals/edit.html', proposal=proposal, customers=customers, suppliers=suppliers)

@app.route('/proposal/<int:id>/delete', methods=['POST'])
@login_required
def delete_proposal(id):
    proposal = Proposal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(proposal)
    db.session.commit()
    flash('Teklif başarıyla silindi!', 'success')
    return redirect(url_for('proposals'))

# Customer Routes
@app.route('/customers')
@login_required
def customers():
    customers = Customer.query.filter_by(user_id=current_user.id).order_by(Customer.name.asc()).all()
    return render_template('customers/list.html', customers=customers)

@app.route('/customer/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    if request.method == 'POST':
        # Şifre hash'le
        password_hash = None
        if request.form.get('password'):
            password_hash = generate_password_hash(request.form['password'])
        
        customer = Customer(
            name=request.form['name'],
            email=request.form['email'],
            phone=request.form['phone'],
            address=request.form['address'],
            company=request.form['company'],
            tax_number=request.form['tax_number'],
            notes=request.form['notes'],
            password=password_hash,
            is_active=True,
            user_id=current_user.id
        )
        
        db.session.add(customer)
        db.session.commit()
        
        flash('Müşteri başarıyla eklendi! Portal girişi için şifre belirlendi.', 'success')
        return redirect(url_for('customers'))
    
    return render_template('customers/new.html')

@app.route('/customer/<int:id>')
@login_required
def view_customer(id):
    customer = Customer.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    proposals = Proposal.query.filter_by(customer_id=customer.id).order_by(Proposal.created_at.desc()).all()
    return render_template('customers/view.html', customer=customer, proposals=proposals)

@app.route('/customer/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.email = request.form['email']
        customer.phone = request.form['phone']
        customer.address = request.form['address']
        customer.company = request.form['company']
        customer.tax_number = request.form['tax_number']
        customer.notes = request.form['notes']
        customer.updated_at = datetime.utcnow()
        
        # Şifre güncellemesi varsa
        if request.form.get('password'):
            customer.password = generate_password_hash(request.form['password'])
        
        db.session.commit()
        
        flash('Müşteri bilgileri başarıyla güncellendi!', 'success')
        return redirect(url_for('view_customer', id=customer.id))
    
    return render_template('customers/edit.html', customer=customer)

@app.route('/customer/<int:id>/delete', methods=['POST'])
@login_required
def delete_customer(id):
    customer = Customer.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # Bu müşteriyle ilişkili tekliflerin customer_id'sini null yap
    proposals = Proposal.query.filter_by(customer_id=customer.id).all()
    for proposal in proposals:
        proposal.customer_id = None
    
    db.session.delete(customer)
    db.session.commit()
    flash('Müşteri başarıyla silindi!', 'success')
    return redirect(url_for('customers'))

# Supplier Routes
@app.route('/suppliers')
@login_required
def suppliers():
    suppliers = Supplier.query.filter_by(user_id=current_user.id).order_by(Supplier.company.asc()).all()
    return render_template('suppliers/list.html', suppliers=suppliers)

@app.route('/supplier/new', methods=['GET', 'POST'])
@login_required
def new_supplier():
    if request.method == 'POST':
        # Şifre hash'le
        password_hash = None
        if request.form.get('password'):
            password_hash = generate_password_hash(request.form['password'])
        
        supplier = Supplier(
            name=request.form['name'],
            company=request.form['company'],
            email=request.form['email'],
            phone=request.form['phone'],
            address=request.form['address'],
            tax_number=request.form['tax_number'],
            website=request.form['website'],
            contact_person=request.form['contact_person'],
            payment_terms=request.form['payment_terms'],
            category=request.form['category'],
            rating=int(request.form['rating']),
            notes=request.form['notes'],
            password=password_hash,
            is_active=True,
            user_id=current_user.id
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        flash('Tedarikçi başarıyla eklendi! Portal girişi için şifre belirlendi.', 'success')
        return redirect(url_for('suppliers'))
    
    return render_template('suppliers/new.html')

@app.route('/supplier/<int:id>')
@login_required
def view_supplier(id):
    supplier = Supplier.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('suppliers/view.html', supplier=supplier)

@app.route('/supplier/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    supplier = Supplier.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        supplier.name = request.form['name']
        supplier.company = request.form['company']
        supplier.email = request.form['email']
        supplier.phone = request.form['phone']
        supplier.address = request.form['address']
        supplier.tax_number = request.form['tax_number']
        supplier.website = request.form['website']
        supplier.contact_person = request.form['contact_person']
        supplier.payment_terms = request.form['payment_terms']
        supplier.category = request.form['category']
        supplier.rating = int(request.form['rating'])
        supplier.is_active = 'is_active' in request.form
        supplier.notes = request.form['notes']
        supplier.updated_at = datetime.utcnow()
        
        # Şifre güncellemesi varsa
        if request.form.get('password'):
            supplier.password = generate_password_hash(request.form['password'])
        
        db.session.commit()
        
        flash('Tedarikçi bilgileri başarıyla güncellendi!', 'success')
        return redirect(url_for('view_supplier', id=supplier.id))
    
    return render_template('suppliers/edit.html', supplier=supplier)

@app.route('/supplier/<int:id>/delete', methods=['POST'])
@login_required
def delete_supplier(id):
    supplier = Supplier.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    db.session.delete(supplier)
    db.session.commit()
    flash('Tedarikçi başarıyla silindi!', 'success')
    return redirect(url_for('suppliers'))

@app.route('/supplier/<int:id>/toggle-status', methods=['POST'])
@login_required
def toggle_supplier_status(id):
    supplier = Supplier.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    supplier.is_active = not supplier.is_active
    db.session.commit()
    
    status_text = "aktif" if supplier.is_active else "pasif"
    flash(f'Tedarikçi durumu {status_text} olarak güncellendi!', 'success')
    return redirect(url_for('view_supplier', id=supplier.id))

# Category Routes
@app.route('/categories')
@login_required
def categories():
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.sort_order.asc(), Category.name.asc()).all()
    return render_template('categories/list.html', categories=categories)

@app.route('/category/new', methods=['GET', 'POST'])
@login_required
def new_category():
    if request.method == 'POST':
        category = Category(
            name=request.form['name'],
            description=request.form.get('description'),
            color=request.form.get('color', '#6c757d'),
            icon=request.form.get('icon', 'bi-tag'),
            sort_order=int(request.form.get('sort_order', 0)),
            user_id=current_user.id
        )
        
        try:
            db.session.add(category)
            db.session.commit()
            flash('Kategori başarıyla eklendi!', 'success')
            return redirect(url_for('categories'))
        except Exception as e:
            db.session.rollback()
            flash('Kategori eklenirken bir hata oluştu!', 'error')
    
    return render_template('categories/new.html')

@app.route('/category/<int:id>')
@login_required
def view_category(id):
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    products_count = Product.query.filter_by(category_id=id, user_id=current_user.id).count()
    return render_template('categories/view.html', category=category, products_count=products_count)

@app.route('/category/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        category.name = request.form['name']
        category.description = request.form.get('description')
        category.color = request.form.get('color', '#6c757d')
        category.icon = request.form.get('icon', 'bi-tag')
        category.sort_order = int(request.form.get('sort_order', 0))
        
        try:
            db.session.commit()
            flash('Kategori başarıyla güncellendi!', 'success')
            return redirect(url_for('view_category', id=category.id))
        except Exception as e:
            db.session.rollback()
            flash('Kategori güncellenirken bir hata oluştu!', 'error')
    
    return render_template('categories/edit.html', category=category)

@app.route('/category/<int:id>/delete', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # Bu kategoriye ait ürün var mı kontrol et
    products_count = Product.query.filter_by(category_id=id, user_id=current_user.id).count()
    if products_count > 0:
        flash(f'Bu kategoriye ait {products_count} ürün bulunduğu için silinemez!', 'error')
        return redirect(url_for('view_category', id=category.id))
    
    try:
        db.session.delete(category)
        db.session.commit()
        flash('Kategori başarıyla silindi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Kategori silinirken bir hata oluştu!', 'error')
    
    return redirect(url_for('categories'))

@app.route('/category/<int:id>/toggle-status', methods=['POST'])
@login_required
def toggle_category_status(id):
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    category.is_active = not category.is_active
    db.session.commit()
    
    status_text = "aktif" if category.is_active else "pasif"
    flash(f'Kategori durumu {status_text} olarak güncellendi!', 'success')
    return redirect(url_for('view_category', id=category.id))

# Price Request Routes (Admin)
@app.route('/admin/price-requests')
@login_required
def admin_price_requests():
    price_requests = PriceRequest.query.filter_by(user_id=current_user.id).order_by(PriceRequest.created_at.desc()).all()
    suppliers = Supplier.query.filter_by(user_id=current_user.id, is_active=True).order_by(Supplier.company.asc()).all()
    return render_template('admin/price_requests.html', price_requests=price_requests, suppliers=suppliers)

@app.route('/admin/price-request/<int:id>')
@login_required
def admin_view_price_request(id):
    price_request = PriceRequest.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    suppliers = Supplier.query.filter_by(user_id=current_user.id, is_active=True).order_by(Supplier.company.asc()).all()
    return render_template('admin/price_request_detail.html', price_request=price_request, suppliers=suppliers)

@app.route('/admin/price-request/<int:id>/approve', methods=['POST'])
@login_required
def admin_approve_price_request(id):
    price_request = PriceRequest.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if price_request.status != 'pending':
        flash('Bu talep zaten işlenmiş.', 'warning')
        return redirect(url_for('admin_view_price_request', id=id))
    
    # Admin notları ve tedarikçi ataması
    price_request.admin_notes = request.form.get('admin_notes')
    price_request.status = 'approved'
    price_request.approved_at = datetime.utcnow()
    
    # Tedarikçi ataması varsa
    assigned_supplier_id = request.form.get('assigned_supplier_id')
    if assigned_supplier_id:
        price_request.assigned_supplier_id = int(assigned_supplier_id)
        price_request.status = 'assigned'
        price_request.assigned_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Fiyat talebi başarıyla onaylandı!', 'success')
    return redirect(url_for('admin_price_requests'))

@app.route('/admin/price-request/<int:id>/reject', methods=['POST'])
@login_required
def admin_reject_price_request(id):
    price_request = PriceRequest.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if price_request.status != 'pending':
        flash('Bu talep zaten işlenmiş.', 'warning')
        return redirect(url_for('admin_view_price_request', id=id))
    
    price_request.admin_notes = request.form.get('admin_notes', 'Talep reddedildi.')
    price_request.status = 'cancelled'
    
    db.session.commit()
    
    flash('Fiyat talebi reddedildi.', 'info')
    return redirect(url_for('admin_price_requests'))

# Product Routes
@app.route('/products')
@login_required
def products():
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.name.asc()).all()
    categories = Category.query.filter_by(user_id=current_user.id, is_active=True).order_by(Category.sort_order.asc(), Category.name.asc()).all()
    return render_template('products/list.html', products=products, categories=categories)

@app.route('/product/new', methods=['GET', 'POST'])
@login_required
def new_product():
    if request.method == 'POST':
        category_id = int(request.form['category_id']) if request.form.get('category_id') else None
        
        product = Product(
            name=request.form['name'],
            description=request.form['description'],
            sku=request.form['sku'] if request.form['sku'] else None,
            category_id=category_id,
            unit=request.form['unit'],
            purchase_price=float(request.form['purchase_price']) if request.form['purchase_price'] else 0.0,
            sale_price=float(request.form['sale_price']) if request.form['sale_price'] else 0.0,
            tax_rate=float(request.form['tax_rate']),
            stock_quantity=int(request.form['stock_quantity']) if request.form['stock_quantity'] else 0,
            min_stock_level=int(request.form['min_stock_level']) if request.form['min_stock_level'] else 0,
            barcode=request.form['barcode'] if request.form['barcode'] else None,
            brand=request.form['brand'],
            model=request.form['model'],
            specifications=request.form['specifications'],
            is_service='is_service' in request.form,
            notes=request.form['notes'],
            supplier_id=int(request.form['supplier_id']) if request.form['supplier_id'] else None,
            user_id=current_user.id
        )
        
        db.session.add(product)
        db.session.commit()
        
        flash('Ürün başarıyla eklendi!', 'success')
        return redirect(url_for('products'))
    
    suppliers = Supplier.query.filter_by(user_id=current_user.id, is_active=True).order_by(Supplier.company.asc()).all()
    categories = Category.query.filter_by(user_id=current_user.id, is_active=True).order_by(Category.sort_order.asc(), Category.name.asc()).all()
    return render_template('products/new.html', suppliers=suppliers, categories=categories)

@app.route('/product/<int:id>')
@login_required
def view_product(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('products/view.html', product=product)

@app.route('/product/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.sku = request.form['sku'] if request.form['sku'] else None
        product.category_id = int(request.form['category_id']) if request.form.get('category_id') else None
        product.unit = request.form['unit']
        product.purchase_price = float(request.form['purchase_price']) if request.form['purchase_price'] else 0.0
        product.sale_price = float(request.form['sale_price']) if request.form['sale_price'] else 0.0
        product.tax_rate = float(request.form['tax_rate'])
        product.stock_quantity = int(request.form['stock_quantity']) if request.form['stock_quantity'] else 0
        product.min_stock_level = int(request.form['min_stock_level']) if request.form['min_stock_level'] else 0
        product.barcode = request.form['barcode'] if request.form['barcode'] else None
        product.brand = request.form['brand']
        product.model = request.form['model']
        product.specifications = request.form['specifications']
        product.is_service = 'is_service' in request.form
        product.is_active = 'is_active' in request.form
        product.notes = request.form['notes']
        product.supplier_id = int(request.form['supplier_id']) if request.form['supplier_id'] else None
        product.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Ürün bilgileri başarıyla güncellendi!', 'success')
        return redirect(url_for('view_product', id=product.id))
    
    suppliers = Supplier.query.filter_by(user_id=current_user.id, is_active=True).order_by(Supplier.company.asc()).all()
    categories = Category.query.filter_by(user_id=current_user.id, is_active=True).order_by(Category.sort_order.asc(), Category.name.asc()).all()
    return render_template('products/edit.html', product=product, suppliers=suppliers, categories=categories)

@app.route('/product/<int:id>/delete', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    db.session.delete(product)
    db.session.commit()
    flash('Ürün başarıyla silindi!', 'success')
    return redirect(url_for('products'))

@app.route('/product/<int:id>/toggle-status', methods=['POST'])
@login_required
def toggle_product_status(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    product.is_active = not product.is_active
    db.session.commit()
    
    status_text = "aktif" if product.is_active else "pasif"
    flash(f'Ürün durumu {status_text} olarak güncellendi!', 'success')
    return redirect(url_for('view_product', id=product.id))

@app.route('/product/<int:id>/update-stock', methods=['POST'])
@login_required
def update_product_stock(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    operation = request.form['operation']  # 'add' or 'remove'
    quantity = int(request.form['quantity'])
    
    if operation == 'add':
        product.stock_quantity += quantity
        flash(f'{quantity} adet stok eklendi!', 'success')
    elif operation == 'remove':
        if product.stock_quantity >= quantity:
            product.stock_quantity -= quantity
            flash(f'{quantity} adet stok çıkarıldı!', 'success')
        else:
            flash('Yetersiz stok!', 'error')
            return redirect(url_for('view_product', id=product.id))
    
    db.session.commit()
    return redirect(url_for('view_product', id=product.id))

# API Routes
@app.route('/api/customers')
@login_required
def customers_api():
    customers = Customer.query.filter_by(user_id=current_user.id).order_by(Customer.name.asc()).all()
    
    customers_data = [
        {
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'company': customer.company
        }
        for customer in customers
    ]
    
    return jsonify({'customers': customers_data})

@app.route('/api/suppliers')
@login_required
def suppliers_api():
    suppliers = Supplier.query.filter_by(user_id=current_user.id).order_by(Supplier.company.asc()).all()
    
    suppliers_data = [
        {
            'id': supplier.id,
            'name': supplier.name,
            'company': supplier.company,
            'email': supplier.email,
            'phone': supplier.phone,
            'category': supplier.category,
            'rating': supplier.rating,
            'is_active': supplier.is_active
        }
        for supplier in suppliers
    ]
    
    return jsonify({'suppliers': suppliers_data})

@app.route('/api/products')
@login_required
def products_api():
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.name.asc()).all()
    
    products_data = []
    for product in products:
        # Kategori bilgisini ayrı olarak al
        category_name = 'Kategori Yok'
        if product.category_id:
            category = Category.query.get(product.category_id)
            if category:
                category_name = category.name
        
        products_data.append({
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'sku': product.sku,
            'category': category_name,
            'unit': product.unit,
            'sale_price': product.sale_price,
            'tax_rate': product.tax_rate,
            'stock_quantity': product.stock_quantity,
            'is_active': product.is_active,
            'is_service': product.is_service,
            'is_low_stock': product.is_low_stock
        })
    
    return jsonify({'products': products_data})

@app.route('/api/proposal/<int:id>/items', methods=['GET', 'POST'])
@login_required
def proposal_items_api(id):
    proposal = Proposal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        data = request.get_json()
        
        # Güvenli veri dönüşümü
        try:
            tax_rate = float(data.get('tax_rate') or 20.0)
        except (ValueError, TypeError):
            tax_rate = 20.0
            
        try:
            unit_price = float(data.get('unit_price') or 0.0)
        except (ValueError, TypeError):
            unit_price = 0.0
            
        try:
            quantity = int(data.get('quantity') or 1)
        except (ValueError, TypeError):
            quantity = 1
        
        item = ProposalItem(
            name=data.get('name', ''),
            description=data.get('description', ''),
            quantity=quantity,
            unit_price=unit_price,
            tax_rate=tax_rate,
            proposal_id=proposal.id,
            product_id=int(data['product_id']) if data.get('product_id') else None
        )
        
        db.session.add(item)
        proposal.calculate_total()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'item': {
                'id': item.id,
                'name': item.name,
                'description': item.description,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'tax_rate': item.tax_rate,
                'subtotal': item.subtotal,
                'tax_amount': item.tax_amount,
                'total_price': item.total_price
            }
        })
    
    # GET request
    items = [
        {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'tax_rate': item.tax_rate,
            'subtotal': item.subtotal,
            'tax_amount': item.tax_amount,
            'total_price': item.total_price
        }
        for item in proposal.items
    ]
    
    return jsonify({'items': items})

@app.route('/api/proposal/<int:proposal_id>', methods=['PUT'])
@login_required
def update_proposal_api(proposal_id):
    proposal = Proposal.query.filter_by(id=proposal_id, user_id=current_user.id).first_or_404()
    
    data = request.get_json()
    
    try:
        # Güncelleme verilerini kontrol et
        if 'title' in data:
            if not data['title'].strip():
                return jsonify({'success': False, 'message': 'Teklif başlığı gereklidir.'}), 400
            proposal.title = data['title'].strip()
        
        if 'description' in data:
            proposal.description = data['description']
        
        if 'customer_id' in data:
            if data['customer_id']:
                customer = Customer.query.filter_by(id=data['customer_id'], user_id=current_user.id).first()
                if not customer:
                    return jsonify({'success': False, 'message': 'Geçersiz müşteri seçimi.'}), 400
            proposal.customer_id = data['customer_id'] if data['customer_id'] else None
        
        if 'supplier_id' in data:
            if data['supplier_id']:
                supplier = Supplier.query.filter_by(id=data['supplier_id'], user_id=current_user.id).first()
                if not supplier:
                    return jsonify({'success': False, 'message': 'Geçersiz tedarikçi seçimi.'}), 400
            proposal.supplier_id = data['supplier_id'] if data['supplier_id'] else None
        
        if 'currency' in data:
            if data['currency'] not in ['TL', 'EUR', 'USD', 'GBP']:
                return jsonify({'success': False, 'message': 'Geçersiz para birimi.'}), 400
            proposal.currency = data['currency']
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Teklif başarıyla güncellendi!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Teklif güncellenirken hata oluştu.'}), 500

@app.route('/api/proposal/<int:proposal_id>/item/<int:item_id>', methods=['PUT', 'DELETE'])
@login_required
def proposal_item_api(proposal_id, item_id):
    proposal = Proposal.query.filter_by(id=proposal_id, user_id=current_user.id).first_or_404()
    item = ProposalItem.query.filter_by(id=item_id, proposal_id=proposal.id).first_or_404()
    
    if request.method == 'DELETE':
        db.session.delete(item)
        proposal.calculate_total()
        db.session.commit()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        
        item.name = data['name']
        item.description = data.get('description', '')
        item.quantity = int(data['quantity'])
        item.unit_price = float(data['unit_price'])
        item.tax_rate = float(data.get('tax_rate', item.tax_rate))
        item.product_id = int(data['product_id']) if data.get('product_id') else None
        item.calculate_total()
        
        proposal.calculate_total()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'item': {
                'id': item.id,
                'name': item.name,
                'description': item.description,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'tax_rate': item.tax_rate,
                'subtotal': item.subtotal,
                'tax_amount': item.tax_amount,
                'total_price': item.total_price
            }
        })

@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats_api():
    proposals = Proposal.query.filter_by(user_id=current_user.id).all()
    
    # Aylık veriler (son 12 ay)
    monthly_data = {}
    for proposal in proposals:
        month_key = proposal.created_at.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {'count': 0, 'value': 0}
        monthly_data[month_key]['count'] += 1
        if proposal.status == 'approved':
            monthly_data[month_key]['value'] += proposal.total_amount
    
    # Status dağılımı
    status_data = {}
    for proposal in proposals:
        status = proposal.status
        if status not in status_data:
            status_data[status] = 0
        status_data[status] += 1
    
    return jsonify({
        'monthly': monthly_data,
        'status': status_data
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Admin kullanıcı oluştur
        if not User.query.filter_by(email='admin@admin.com').first():
            admin = User(
                username='admin',
                email='admin@admin.com',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            
            # Default kategoriler ekle
            default_categories = [
                {'name': 'Teknoloji', 'description': 'Teknoloji ürünleri', 'color': '#007bff', 'icon': 'bi-laptop', 'sort_order': 1},
                {'name': 'Yazılım', 'description': 'Yazılım ürün ve hizmetleri', 'color': '#28a745', 'icon': 'bi-code-slash', 'sort_order': 2},
                {'name': 'Donanım', 'description': 'Donanım ürünleri', 'color': '#dc3545', 'icon': 'bi-cpu', 'sort_order': 3},
                {'name': 'Hizmet', 'description': 'Hizmet ürünleri', 'color': '#ffc107', 'icon': 'bi-gear', 'sort_order': 4},
                {'name': 'Ofis Malzemeleri', 'description': 'Ofis ve büro malzemeleri', 'color': '#6f42c1', 'icon': 'bi-briefcase', 'sort_order': 5},
                {'name': 'Mobilya', 'description': 'Mobilya ürünleri', 'color': '#fd7e14', 'icon': 'bi-house', 'sort_order': 6}
            ]
            
            for cat_data in default_categories:
                category = Category(
                    name=cat_data['name'],
                    description=cat_data['description'],
                    color=cat_data['color'],
                    icon=cat_data['icon'],
                    sort_order=cat_data['sort_order'],
                    user_id=admin.id
                )
                db.session.add(category)
            
            db.session.commit()

# Müşteri Portal Route'ları
@app.route('/customer_login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        customer = Customer.query.filter_by(email=email).first()
        
        if customer and customer.check_password(password):
            # Müşteri girişi için session oluştur
            session['customer_id'] = customer.id
            customer.last_login = datetime.utcnow()
            db.session.commit()
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('customer_dashboard'))
        else:
            flash('E-posta veya şifre hatalı.', 'danger')
    
    return render_template('customer_portal/login.html')

@app.route('/customer_register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        company = request.form.get('company', '')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        tax_number = request.form.get('tax_number', '')
        
        # E-posta kontrolü
        existing_customer = Customer.query.filter_by(email=email).first()
        if existing_customer:
            flash('Bu e-posta adresi zaten kayıtlı.', 'danger')
            return render_template('customer_portal/register.html')
        
        # Admin kullanıcıyı bul (geçici olarak)
        admin_user = User.query.filter_by(role='admin').first()
        
        # Yeni müşteri oluştur
        customer = Customer(
            name=name,
            email=email,
            password=generate_password_hash(password),
            company=company,
            phone=phone,
            address=address,
            tax_number=tax_number,
            user_id=admin_user.id
        )
        
        db.session.add(customer)
        db.session.commit()
        
        flash('Hesabınız başarıyla oluşturuldu! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('customer_login'))
    
    return render_template('customer_portal/register.html')

@app.route('/customer_dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer = Customer.query.get(session['customer_id'])
    if not customer:
        session.pop('customer_id', None)
        return redirect(url_for('customer_login'))
    
    # Müşteriye ait teklifleri getir
    proposals = Proposal.query.filter_by(customer_id=customer.id).order_by(Proposal.created_at.desc()).all()
    
    # Müşteriye ait fiyat taleplerini getir
    price_requests = PriceRequest.query.filter_by(customer_id=customer.id).order_by(PriceRequest.created_at.desc()).all()
    
    # İstatistikleri hesapla
    proposal_stats = {
        'total': len(proposals),
        'pending': len([p for p in proposals if p.status == 'sent']),
        'approved': len([p for p in proposals if p.status == 'approved']),
        'rejected': len([p for p in proposals if p.status == 'rejected'])
    }
    
    # Fiyat talebi istatistikleri
    price_request_stats = {
        'total': len(price_requests),
        'draft': len([pr for pr in price_requests if pr.status == 'draft']),
        'pending': len([pr for pr in price_requests if pr.status == 'pending']),
        'approved': len([pr for pr in price_requests if pr.status == 'approved']),
        'assigned': len([pr for pr in price_requests if pr.status == 'assigned']),
        'completed': len([pr for pr in price_requests if pr.status == 'completed'])
    }
    
    return render_template('customer_portal/dashboard.html', 
                         current_customer=customer, 
                         proposals=proposals,
                         proposal_stats=proposal_stats,
                         price_requests=price_requests,
                         price_request_stats=price_request_stats)

@app.route('/customer-portal/proposal/<int:id>')
def customer_proposal_view(id):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer = Customer.query.get(session['customer_id'])
    proposal = Proposal.query.filter_by(id=id, customer_id=customer.id).first_or_404()
    
    return render_template('proposals/view.html', proposal=proposal)

@app.route('/customer-portal/proposal/<int:id>/status', methods=['POST'])
def customer_update_proposal_status(id):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'})
    
    customer = Customer.query.get(session['customer_id'])
    proposal = Proposal.query.filter_by(id=id, customer_id=customer.id).first()
    
    if not proposal:
        return jsonify({'success': False, 'message': 'Teklif bulunamadı'})
    
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status in ['approved', 'rejected']:
        proposal.status = new_status
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Geçersiz durum'})

@app.route('/customer-portal/proposal/<int:id>/edit', methods=['GET', 'POST'])
def customer_edit_proposal(id):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer = Customer.query.get(session['customer_id'])
    if not customer:
        session.pop('customer_id', None)
        return redirect(url_for('customer_login'))
    
    # Teklifi bul (sadece müşterinin kendi teklifleri)
    proposal = Proposal.query.filter_by(id=id, customer_id=customer.id).first()
    if not proposal:
        flash('Teklif bulunamadı.', 'danger')
        return redirect(url_for('customer_dashboard'))
    
    # Sadece draft durumundaki teklifleri düzenleye bilsin
    if proposal.status != 'draft':
        flash('Sadece taslak durumundaki teklifler düzenlenebilir.', 'warning')
        return redirect(url_for('customer_dashboard'))
    
    if request.method == 'POST':
        try:
            # Form verilerini al
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            
            # Gerekli alanları kontrol et
            if not title:
                flash('Başlık alanı gereklidir.', 'danger')
                return redirect(url_for('customer_edit_proposal', id=id))
            
            # Teklifi güncelle
            proposal.title = title
            proposal.description = description
            proposal.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Teklifiniz başarıyla güncellendi!', 'success')
            return redirect(url_for('customer_edit_proposal', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Teklif güncellenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('customer_edit_proposal', id=id))
    
    # GET request için teklif bilgilerini getir
    return render_template('customer_portal/edit_proposal.html', 
                         current_customer=customer, 
                         proposal=proposal)

@app.route('/customer-portal/proposal/<int:id>/delete', methods=['POST'])
def customer_delete_proposal(id):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Giriş yapmanız gerekir.'}), 401
    
    customer = Customer.query.get(session['customer_id'])
    if not customer:
        return jsonify({'success': False, 'message': 'Müşteri bulunamadı.'}), 404
    
    # Teklifi bul (sadece müşterinin kendi teklifleri)
    proposal = Proposal.query.filter_by(id=id, customer_id=customer.id).first()
    if not proposal:
        return jsonify({'success': False, 'message': 'Teklif bulunamadı.'}), 404
    
    # Sadece draft durumundaki teklifleri silebilsin
    if proposal.status != 'draft':
        return jsonify({'success': False, 'message': 'Sadece taslak durumundaki teklifler silinebilir.'}), 400
    
    try:
        # Teklifi sil
        db.session.delete(proposal)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Teklif başarıyla silindi.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Silme işlemi sırasında hata oluştu: {str(e)}'}), 500

@app.route('/customer_logout')
def customer_logout():
    session.pop('customer_id', None)
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('customer_login'))

# Müşteri Fiyat Talebi Route'ları
@app.route('/customer-portal/price-request/new', methods=['GET', 'POST'])
def customer_new_price_request():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer = Customer.query.get(session['customer_id'])
    if not customer:
        session.pop('customer_id', None)
        return redirect(url_for('customer_login'))
    
    if request.method == 'POST':
        # Admin kullanıcısını bul
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user:
            flash('Sistem hatası: Admin kullanıcısı bulunamadı.', 'danger')
            return redirect(url_for('customer_new_price_request'))
        
        try:
            # Ana fiyat talebini oluştur (artık miktar, birim ve bütçe yok)
            price_request = PriceRequest(
                title=request.form['title'],
                description=request.form['description'],
                deadline=datetime.strptime(request.form['deadline'], '%Y-%m-%d').date() if request.form.get('deadline') else None,
                additional_notes=request.form.get('additional_notes'),
                priority=request.form.get('priority', 'normal'),
                customer_id=customer.id,
                user_id=admin_user.id,
                status='pending'
            )
            
            db.session.add(price_request)
            db.session.flush()  # ID'yi almak için flush
            
            # Form verilerindeki ürün/hizmet kalemlerini işle
            items_data = {}
            
            # Form verilerini parse et (items[0][name], items[0][description] vb.)
            for key, value in request.form.items():
                if key.startswith('items[') and '][' in key:
                    # items[0][name] -> index=0, field=name
                    parts = key.split('][')
                    index_part = parts[0].replace('items[', '')
                    field_part = parts[1].replace(']', '')
                    
                    index = int(index_part)
                    
                    if index not in items_data:
                        items_data[index] = {}
                    items_data[index][field_part] = value
            
            # Her ürün/hizmet kalemi için PriceRequestItem oluştur
            created_items = 0
            for index, item_data in items_data.items():
                if item_data.get('name'):  # İsim varsa kaydet
                    # Kategori ID'sini kontrol et
                    category_id = None
                    if item_data.get('category_id'):
                        try:
                            category_id = int(item_data['category_id'])
                        except (ValueError, TypeError):
                            category_id = None
                    
                    # Bütçe min/max değerlerini işle
                    budget_min = None
                    budget_max = None
                    if item_data.get('budget_min'):
                        try:
                            budget_min = float(item_data['budget_min'])
                        except (ValueError, TypeError):
                            budget_min = None
                    if item_data.get('budget_max'):
                        try:
                            budget_max = float(item_data['budget_max'])
                        except (ValueError, TypeError):
                            budget_max = None
                    
                    price_request_item = PriceRequestItem(
                        price_request_id=price_request.id,
                        name=item_data['name'],
                        description=item_data.get('description', ''),
                        quantity=int(item_data.get('quantity', 1)),
                        unit=item_data.get('unit', 'Adet'),
                        category_id=category_id,
                        budget_min=budget_min,
                        budget_max=budget_max
                    )
                    
                    db.session.add(price_request_item)
                    created_items += 1
            
            if created_items == 0:
                flash('En az bir ürün/hizmet eklemelisiniz!', 'danger')
                db.session.rollback()
                return redirect(url_for('customer_new_price_request'))
            
            db.session.commit()
            
            flash(f'Fiyat talebiniz başarıyla gönderildi! {created_items} ürün/hizmet kalemi eklendi. Admin onayı bekleniyor.', 'success')
            return redirect(url_for('customer_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fiyat talebi oluşturulurken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('customer_new_price_request'))
    
    # GET request için kategorileri getir
    categories = Category.query.all()
    return render_template('customer_portal/new_price_request.html', 
                         current_customer=customer, 
                         categories=categories)

@app.route('/customer-portal/price-requests')
def customer_price_requests():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer = Customer.query.get(session['customer_id'])
    if not customer:
        session.pop('customer_id', None)
        return redirect(url_for('customer_login'))
    
    # Müşterinin fiyat taleplerini getir
    price_requests = PriceRequest.query.filter_by(customer_id=customer.id).order_by(PriceRequest.created_at.desc()).all()
    
    return render_template('customer_portal/price_requests.html', 
                         current_customer=customer, 
                         price_requests=price_requests)

@app.route('/customer-portal/price-request/<int:id>/edit', methods=['GET', 'POST'])
def customer_edit_price_request(id):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer = Customer.query.get(session['customer_id'])
    if not customer:
        session.pop('customer_id', None)
        return redirect(url_for('customer_login'))
    
    # Fiyat talebini bul (sadece müşterinin kendi talepleri)
    price_request = PriceRequest.query.filter_by(id=id, customer_id=customer.id).first()
    if not price_request:
        flash('Fiyat talebi bulunamadı.', 'danger')
        return redirect(url_for('customer_dashboard'))
    
    # Sadece draft durumundaki talepleri düzenleye bilsin
    if price_request.status != 'draft':
        flash('Sadece taslak durumundaki fiyat talepleri düzenlenebilir.', 'warning')
        return redirect(url_for('customer_dashboard'))
    
    if request.method == 'POST':
        try:
            # Form verilerini al
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            priority = request.form.get('priority', 'normal')
            deadline = request.form.get('deadline')
            
            # Gerekli alanları kontrol et
            if not title:
                flash('Başlık alanı gereklidir.', 'danger')
                return redirect(url_for('customer_edit_price_request', id=id))
            
            # Fiyat talebini güncelle
            price_request.title = title
            price_request.description = description
            price_request.priority = priority
            
            if deadline:
                price_request.deadline = datetime.strptime(deadline, '%Y-%m-%d').date()
            
            # Mevcut kalemleri sil
            PriceRequestItem.query.filter_by(price_request_id=price_request.id).delete()
            
            # Yeni kalemleri ekle
            items_data = request.form.getlist('items')
            created_items = 0
            
            for item_json in items_data:
                if item_json.strip():
                    try:
                        item_data = json.loads(item_json)
                        item = PriceRequestItem(
                            price_request_id=price_request.id,
                            name=item_data.get('name', ''),
                            description=item_data.get('description', ''),
                            quantity=float(item_data.get('quantity', 1)),
                            unit=item_data.get('unit', 'Adet'),
                            category_id=int(item_data.get('category_id', 1)) if item_data.get('category_id') else 1,
                            budget_min=float(item_data.get('budget_min', 0)) if item_data.get('budget_min') else None,
                            budget_max=float(item_data.get('budget_max', 0)) if item_data.get('budget_max') else None
                        )
                        db.session.add(item)
                        created_items += 1
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        continue
            
            if created_items == 0:
                flash('En az bir ürün/hizmet kalemi eklemeniz gerekir.', 'danger')
                return redirect(url_for('customer_edit_price_request', id=id))
            
            # Güncellemeleri kaydet
            price_request.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash(f'Fiyat talebiniz başarıyla güncellendi! {created_items} ürün/hizmet kalemi güncellendi.', 'success')
            return redirect(url_for('customer_edit_price_request', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fiyat talebi güncellenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('customer_edit_price_request', id=id))
    
    # GET request için mevcut bilgileri ve kategorileri getir
    categories = Category.query.all()
    items = PriceRequestItem.query.filter_by(price_request_id=price_request.id).all()
    
    return render_template('customer_portal/edit_price_request.html', 
                         current_customer=customer, 
                         price_request=price_request,
                         items=items,
                         categories=categories)

@app.route('/customer-portal/price-request/<int:id>/delete', methods=['POST'])
def customer_delete_price_request(id):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Giriş yapmanız gerekir.'}), 401
    
    customer = Customer.query.get(session['customer_id'])
    if not customer:
        return jsonify({'success': False, 'message': 'Müşteri bulunamadı.'}), 404
    
    # Fiyat talebini bul (sadece müşterinin kendi talepleri)
    price_request = PriceRequest.query.filter_by(id=id, customer_id=customer.id).first()
    if not price_request:
        return jsonify({'success': False, 'message': 'Fiyat talebi bulunamadı.'}), 404
    
    # Sadece draft durumundaki talepleri silebilsin
    if price_request.status != 'draft':
        return jsonify({'success': False, 'message': 'Sadece taslak durumundaki fiyat talepleri silinebilir.'}), 400
    
    try:
        # İlgili kalemleri de sil (CASCADE ile otomatik silinir ama explisit yapalım)
        PriceRequestItem.query.filter_by(price_request_id=price_request.id).delete()
        
        # Fiyat talebini sil
        db.session.delete(price_request)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Fiyat talebi başarıyla silindi.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Silme işlemi sırasında hata oluştu: {str(e)}'}), 500

# Tedarikçi Portal Route'ları
@app.route('/supplier_login', methods=['GET', 'POST'])
def supplier_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        supplier = Supplier.query.filter_by(email=email).first()
        
        if supplier and supplier.check_password(password):
            session['supplier_id'] = supplier.id
            supplier.last_login = datetime.utcnow()
            db.session.commit()
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('supplier_dashboard'))
        else:
            flash('E-posta veya şifre hatalı.', 'danger')
    
    return render_template('supplier_portal/login.html')

@app.route('/supplier_register', methods=['GET', 'POST'])
def supplier_register():
    if request.method == 'POST':
        name = request.form['name']
        company = request.form['company']
        email = request.form['email']
        password = request.form['password']
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        tax_number = request.form.get('tax_number', '')
        website = request.form.get('website', '')
        category = request.form.get('category', '')
        
        # E-posta kontrolü
        existing_supplier = Supplier.query.filter_by(email=email).first()
        if existing_supplier:
            flash('Bu e-posta adresi zaten kayıtlı.', 'danger')
            return render_template('supplier_portal/register.html')
        
        # Admin kullanıcıyı bul
        admin_user = User.query.filter_by(role='admin').first()
        
        # Yeni tedarikçi oluştur
        supplier = Supplier(
            name=name,
            company=company,
            email=email,
            password=generate_password_hash(password),
            phone=phone,
            address=address,
            tax_number=tax_number,
            website=website,
            category=category,
            user_id=admin_user.id
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        flash('Hesabınız başarıyla oluşturuldu! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('supplier_login'))
    
    return render_template('supplier_portal/register.html')

@app.route('/supplier_dashboard')
def supplier_dashboard():
    if 'supplier_id' not in session:
        return redirect(url_for('supplier_login'))
    
    supplier = Supplier.query.get(session['supplier_id'])
    if not supplier:
        session.pop('supplier_id', None)
        return redirect(url_for('supplier_login'))
    
    # Tedarikçiye ait ürünleri getir
    products = Product.query.filter_by(supplier_id=supplier.id).all()
    
    return render_template('supplier_portal/dashboard.html', 
                         current_supplier=supplier, 
                         products=products)

# Supplier Price Request Routes
@app.route('/supplier/price-requests')
def supplier_price_requests():
    if 'supplier_id' not in session:
        return redirect(url_for('supplier_login'))
    
    supplier = Supplier.query.get(session['supplier_id'])
    if not supplier:
        session.pop('supplier_id', None)
        return redirect(url_for('supplier_login'))
    
    # Tedarikçiye atanan fiyat taleplerini getir
    price_requests = PriceRequest.query.filter_by(assigned_supplier_id=supplier.id).order_by(PriceRequest.assigned_at.desc()).all()
    
    # Bugünün tarihini template'e gönder
    from datetime import date
    today = date.today()
    
    return render_template('supplier_portal/price_requests.html', 
                         current_supplier=supplier, 
                         price_requests=price_requests,
                         today=today)

@app.route('/supplier/price-request/<int:id>')
def supplier_view_price_request(id):
    if 'supplier_id' not in session:
        return redirect(url_for('supplier_login'))
    
    supplier = Supplier.query.get(session['supplier_id'])
    if not supplier:
        session.pop('supplier_id', None)
        return redirect(url_for('supplier_login'))
    
    # Sadece tedarikçiye atanan talepleri görüntüleyebilir
    price_request = PriceRequest.query.filter_by(id=id, assigned_supplier_id=supplier.id).first_or_404()
    
    return render_template('supplier_portal/price_request_detail.html', 
                         current_supplier=supplier, 
                         price_request=price_request)

@app.route('/supplier/price-request/<int:id>/quote', methods=['GET', 'POST'])
def supplier_submit_quote(id):
    if 'supplier_id' not in session:
        return redirect(url_for('supplier_login'))
    
    supplier = Supplier.query.get(session['supplier_id'])
    if not supplier:
        session.pop('supplier_id', None)
        return redirect(url_for('supplier_login'))
    
    price_request = PriceRequest.query.filter_by(id=id, assigned_supplier_id=supplier.id).first_or_404()
    
    if price_request.status != 'assigned':
        flash('Bu talep için teklif verilemez.', 'warning')
        return redirect(url_for('supplier_view_price_request', id=id))
    
    if request.method == 'POST':
        # Teklif bilgilerini kaydet
        price_request.supplier_quote = float(request.form['quote_price'])
        price_request.supplier_notes = request.form.get('quote_notes')
        price_request.quote_valid_until = datetime.strptime(request.form['valid_until'], '%Y-%m-%d').date()
        price_request.status = 'completed'
        price_request.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Teklifiniz başarıyla gönderildi!', 'success')
        return redirect(url_for('supplier_price_requests'))
    
    return render_template('supplier_portal/submit_quote.html', 
                         current_supplier=supplier, 
                         price_request=price_request)

@app.route('/supplier_logout')
def supplier_logout():
    session.pop('supplier_id', None)
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('supplier_login'))

if __name__ == '__main__':
    app.run(debug=True, port=5005)