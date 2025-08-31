# Epica SaaS - Multi-Tenant Teklif Yönetim Sistemi
# epica.com.tr - Ana Platform

from flask import Flask, request, session, redirect, url_for, render_template, flash, jsonify, g, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import re
import json
from urllib.parse import urlparse

# SaaS Multi-Tenant Configuration
class Config:
    # Veritabanı - Production'da PostgreSQL kullanın
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///epica_saas.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Güvenlik
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'epica-saas-2025-super-secret-key'
    
    # Domain Configuration
    MAIN_DOMAIN = 'localhost:5001'  # Development için
    SUBDOMAIN_REGEX = r'^([a-zA-Z0-9-]+)\.localhost:5001$'
    
    # SaaS Planları ve Limitler
    PLANS = {
        'trial': {
            'name': 'Deneme',
            'monthly_fee': 0,
            'max_users': 2,
            'max_customers': 10,
            'max_suppliers': 5,
            'max_products': 50,
            'max_monthly_requests': 20,
            'duration_days': 15
        },
        'basic': {
            'name': 'Temel',
            'monthly_fee': 299,
            'max_users': 5,
            'max_customers': 100,
            'max_suppliers': 50,
            'max_products': 1000,
            'max_monthly_requests': 500
        },
        'pro': {
            'name': 'Profesyonel',
            'monthly_fee': 599,
            'max_users': 15,
            'max_customers': 500,
            'max_suppliers': 200,
            'max_products': 5000,
            'max_monthly_requests': 2000
        },
        'enterprise': {
            'name': 'Kurumsal',
            'monthly_fee': 1299,
            'max_users': 50,
            'max_customers': 2000,
            'max_suppliers': 1000,
            'max_products': 20000,
            'max_monthly_requests': 10000
        }
    }

app = Flask(__name__, template_folder='templates_saas')
app.config.from_object(Config)

# Database
from models_saas import db, Tenant, User, Customer, Supplier, Product, Category
from models_saas import PlatformAdmin, AuditLog, PriceRequest, Proposal
db.init_app(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.login'
login_manager.login_message = 'Bu sayfaya erişmek için giriş yapmanız gerekir.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    # Multi-tenant user loading
    user_type = session.get('user_type', 'user')
    
    if user_type == 'platform_admin':
        return PlatformAdmin.query.get(int(user_id))
    else:
        return User.query.get(int(user_id))

# Tenant Context Middleware
@app.before_request
def load_tenant():
    """Her istekte tenant bilgisini yükle"""
    g.tenant = None
    g.is_subdomain = False
    
    # Host bilgisini al
    host = request.host.lower()
    
    # Ana domain kontrolü
    if host == app.config['MAIN_DOMAIN'] or host == f"www.{app.config['MAIN_DOMAIN']}":
        g.is_subdomain = False
        return
    
    # Subdomain kontrolü
    subdomain_match = re.match(app.config['SUBDOMAIN_REGEX'], host)
    if subdomain_match:
        subdomain = subdomain_match.group(1)
        
        # Tenant'ı veritabanından bul
        tenant = Tenant.query.filter_by(subdomain=subdomain, is_active=True).first()
        if tenant:
            g.tenant = tenant
            g.is_subdomain = True
            
            # Abonelik kontrolü
            if not tenant.is_subscription_active:
                return render_template('errors/subscription_expired.html', tenant=tenant), 403
        else:
            # Geçersiz subdomain
            return render_template('errors/tenant_not_found.html'), 404

# Ana Platform Routes (epica.com.tr)
@app.route('/')
def index():
    """Ana sayfa - epica.com.tr"""
    if g.is_subdomain:
        # Subdomain ise tenant dashboard'una yönlendir
        return redirect(url_for('tenant.dashboard'))
    
    # Ana platform sayfası
    return render_template('main/index.html')

@app.route('/pricing')
def pricing():
    """Fiyatlandırma sayfası"""
    if g.is_subdomain:
        return redirect(url_for('tenant.dashboard'))
    
    return render_template('main/pricing.html', plans=app.config['PLANS'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Yeni firma kaydı"""
    if g.is_subdomain:
        return redirect(url_for('tenant.dashboard'))
    
    if request.method == 'POST':
        try:
            # Form verilerini al
            company_name = request.form.get('company_name', '').strip()
            subdomain = request.form.get('subdomain', '').lower().strip()
            contact_name = request.form.get('contact_name', '').strip()
            contact_email = request.form.get('contact_email', '').strip()
            contact_phone = request.form.get('contact_phone', '').strip()
            admin_username = request.form.get('admin_username', '').strip()
            admin_password = request.form.get('admin_password', '')
            plan = request.form.get('plan', 'trial')
            
            # Validasyon
            errors = []
            
            if not company_name:
                errors.append('Şirket adı gereklidir.')
            
            if not subdomain or not re.match(r'^[a-zA-Z0-9-]+$', subdomain):
                errors.append('Geçerli bir subdomain giriniz (sadece harf, rakam ve tire).')
            
            if len(subdomain) < 3 or len(subdomain) > 20:
                errors.append('Subdomain 3-20 karakter arası olmalıdır.')
            
            # Yasak subdomain'ler
            forbidden_subdomains = ['www', 'api', 'admin', 'support', 'help', 'mail', 'ftp', 'blog']
            if subdomain in forbidden_subdomains:
                errors.append('Bu subdomain kullanılamaz.')
            
            # Subdomain benzersizlik kontrolü
            if Tenant.query.filter_by(subdomain=subdomain).first():
                errors.append('Bu subdomain zaten kullanılıyor.')
            
            if not contact_email or '@' not in contact_email:
                errors.append('Geçerli bir email adresi giriniz.')
            
            if not admin_username or len(admin_username) < 3:
                errors.append('Admin kullanıcı adı en az 3 karakter olmalıdır.')
            
            if not admin_password or len(admin_password) < 6:
                errors.append('Admin şifresi en az 6 karakter olmalıdır.')
            
            if plan not in app.config['PLANS']:
                errors.append('Geçersiz plan seçimi.')
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('main/register.html', plans=app.config['PLANS'])
            
            # Yeni tenant oluştur
            plan_config = app.config['PLANS'][plan]
            subscription_end = None
            
            if plan == 'trial':
                subscription_end = datetime.utcnow() + timedelta(days=plan_config['duration_days'])
            
            new_tenant = Tenant(
                company_name=company_name,
                subdomain=subdomain,
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                subscription_plan=plan,
                subscription_status='trial' if plan == 'trial' else 'active',
                subscription_end=subscription_end,
                monthly_fee=plan_config['monthly_fee'],
                max_users=plan_config['max_users'],
                max_customers=plan_config['max_customers'],
                max_suppliers=plan_config['max_suppliers'],
                max_products=plan_config['max_products'],
                max_monthly_requests=plan_config['max_monthly_requests']
            )
            
            db.session.add(new_tenant)
            db.session.flush()  # ID'yi al
            
            # Tenant admin kullanıcısı oluştur
            admin_user = User(
                tenant_id=new_tenant.id,
                username=admin_username,
                email=contact_email,
                password_hash=generate_password_hash(admin_password),
                first_name=contact_name.split()[0] if contact_name else '',
                last_name=' '.join(contact_name.split()[1:]) if len(contact_name.split()) > 1 else '',
                role='admin',
                is_tenant_admin=True
            )
            
            db.session.add(admin_user)
            
            # Varsayılan kategoriler oluştur
            default_categories = [
                {'name': 'Genel', 'description': 'Genel ürün ve hizmetler'},
                {'name': 'Teknoloji', 'description': 'Bilgisayar, yazılım ve teknolojik ürünler'},
                {'name': 'Ofis Malzemeleri', 'description': 'Kırtasiye ve ofis ekipmanları'},
                {'name': 'Hizmetler', 'description': 'Danışmanlık ve profesyonel hizmetler'}
            ]
            
            for cat_data in default_categories:
                category = Category(
                    tenant_id=new_tenant.id,
                    name=cat_data['name'],
                    description=cat_data['description']
                )
                db.session.add(category)
            
            db.session.commit()
            
            # Audit log
            audit = AuditLog(
                tenant_id=new_tenant.id,
                user_type='system',
                user_id=0,
                action='tenant_created',
                resource_type='tenant',
                resource_id=new_tenant.id,
                new_values=json.dumps({
                    'company_name': company_name,
                    'subdomain': subdomain,
                    'plan': plan
                }),
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            db.session.add(audit)
            db.session.commit()
            
            flash(f'Hesabınız başarıyla oluşturuldu! {subdomain}.epica.com.tr adresinden giriş yapabilirsiniz.', 'success')
            
            # Tenant subdomain'ine yönlendir
            return redirect(f"http://{subdomain}.epica.com.tr/login")
            
        except Exception as e:
            db.session.rollback()
            flash(f'Hesap oluşturulurken hata oluştu: {str(e)}', 'danger')
            return render_template('main/register.html', plans=app.config['PLANS'])
    
    return render_template('main/register.html', plans=app.config['PLANS'])

@app.route('/login', methods=['GET', 'POST'])
def platform_login():
    """Platform admin girişi"""
    if g.is_subdomain:
        return redirect(url_for('tenant.login'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = PlatformAdmin.query.filter_by(username=username, is_active=True).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            session['user_type'] = 'platform_admin'
            session['user_id'] = admin.id
            admin.last_login = datetime.utcnow()
            db.session.commit()
            
            flash('Platform admin olarak giriş yaptınız.', 'success')
            return redirect(url_for('platform_admin.dashboard'))
        
        flash('Geçersiz kullanıcı adı veya şifre.', 'danger')
    
    return render_template('main/platform_login.html')

# Tenant Routes (subdomain.epica.com.tr)
@app.route('/tenant/')
def tenant_index():
    """Tenant ana sayfası"""
    if not g.is_subdomain or not g.tenant:
        return redirect(url_for('index'))
    
    return render_template('tenant/index.html', tenant=g.tenant)

@app.route('/tenant/login', methods=['GET', 'POST'])
def tenant_login():
    """Tenant kullanıcı girişi"""
    if not g.is_subdomain or not g.tenant:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(
            tenant_id=g.tenant.id,
            username=username,
            is_active=True
        ).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_type'] = 'user'
            session['user_id'] = user.id
            session['tenant_id'] = g.tenant.id
            
            user.last_login = datetime.utcnow()
            user.login_count += 1
            db.session.commit()
            
            flash(f'Hoş geldiniz, {user.full_name}!', 'success')
            return redirect(url_for('tenant.dashboard'))
        
        flash('Geçersiz kullanıcı adı veya şifre.', 'danger')
    
    return render_template('tenant/login.html', tenant=g.tenant)

@app.route('/tenant/dashboard')
@login_required
def tenant_dashboard():
    """Tenant dashboard"""
    if not g.is_subdomain or not g.tenant:
        return redirect(url_for('index'))
    
    # Kullanım istatistikleri
    stats = g.tenant.get_usage_stats()
    
    # Son aktiviteler
    recent_activities = AuditLog.query.filter_by(
        tenant_id=g.tenant.id
    ).order_by(AuditLog.created_at.desc()).limit(10).all()
    
    return render_template('tenant/dashboard.html', 
                         tenant=g.tenant, 
                         stats=stats,
                         recent_activities=recent_activities)

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Template Filters
@app.template_filter('currency')
def currency_filter(amount):
    """Para birimi formatı"""
    if amount is None:
        return "0,00 ₺"
    return f"{amount:,.2f} ₺".replace(',', '.')

@app.template_filter('date_tr')
def date_tr_filter(date):
    """Türkçe tarih formatı"""
    if not date:
        return ""
    
    months = [
        '', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
        'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'
    ]
    
    return f"{date.day} {months[date.month]} {date.year}"

# Database İlklendirme
def init_database():
    """Veritabanını ve ilk verileri oluştur"""
    with app.app_context():
        db.create_all()
        
        # İlk platform admin'i oluştur
        if not PlatformAdmin.query.first():
            admin = PlatformAdmin(
                username='epicaadmin',
                email='admin@epica.com.tr',
                password_hash=generate_password_hash('EpicaAdmin2025!'),
                first_name='Platform',
                last_name='Admin',
                is_super_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Platform admin oluşturuldu: epicaadmin / EpicaAdmin2025!")

if __name__ == '__main__':
    init_database()
    
    # Development sunucusu - Production'da Gunicorn kullanın
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True
    )
