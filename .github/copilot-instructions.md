<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Teklif Arayüzü - Copilot Instructions

Bu proje Flask tabanlı bir teklif yönetim sistemidir. Aşağıdaki kurallara ve teknolojilere uygun kod üretiniz:

## Teknoloji Stack
- **Backend**: Python Flask 3.0+
- **Database**: SQLite + SQLAlchemy ORM
- **Authentication**: Flask-Login
- **Frontend**: Bootstrap 5.3, HTML5, CSS3, JavaScript (Vanilla)
- **Charts**: Chart.js
- **Icons**: Bootstrap Icons

## Kod Standartları

### Python/Flask
- Python 3.8+ syntax kullanın
- Flask best practices'i takip edin
- SQLAlchemy ORM patterns kullanın
- Type hints kullanın (mümkün olduğunda)
- Error handling ekleyin
- Flask-Login decorators (@login_required) kullanın

### Frontend
- Bootstrap 5.3 component'leri kullanın
- Responsive design (mobile-first)
- Accessibility (ARIA attributes) ekleyin
- Vanilla JavaScript (jQuery yok)
- Modern ES6+ syntax
- Chart.js için profesyonel konfigürasyonlar

### Template'ler (Jinja2)
- base.html'den extend edin
- Turkish language support
- Flash message handling
- CSRF protection (forms)
- Semantic HTML5 kullanın

## Proje Yapısı

```
app.py              # Ana uygulama (models, routes dahil)
templates/          # Jinja2 templates
├── base.html       # Ana template
├── index.html      # Landing page
├── dashboard.html  # Dashboard with charts
├── auth/           # Authentication templates
└── proposals/      # Proposal management templates
static/             # CSS, JS, images
requirements.txt    # Python dependencies
```

## Özellik Gereksinimleri

### Kimlik Doğrulama
- Kayıt/Giriş/Çıkış
- Password hashing (Werkzeug)
- Session management
- Role-based access (admin/user)

### Teklif Yönetimi
- CRUD operations (Create, Read, Update, Delete)
- Status tracking (draft, sent, approved, rejected)
- Item management (kalem ekleme/çıkarma)
- Automatic total calculation
- Client information management

### Dashboard
- Visual charts (Chart.js)
- Statistics summary
- Recent proposals list
- Status distribution
- Monthly analytics

### API Endpoints
- RESTful JSON APIs
- Proper HTTP status codes
- Error handling with JSON responses
- AJAX support for dynamic updates

## Güvenlik
- Input validation and sanitization
- SQL injection prevention (SQLAlchemy ORM)
- XSS protection
- CSRF tokens in forms
- Secure password handling

## UI/UX Patterns
- Turkish language interface
- Consistent Bootstrap theming
- Loading states and feedback
- Confirmation dialogs for destructive actions
- Form validation (client + server side)
- Pagination for large lists
- Search and filtering capabilities

## Code Examples

### Route Pattern:
```python
@app.route('/proposals')
@login_required
def proposals():
    proposals = Proposal.query.filter_by(user_id=current_user.id).all()
    return render_template('proposals/list.html', proposals=proposals)
```

### API Pattern:
```python
@app.route('/api/proposal/<int:id>/items', methods=['GET', 'POST'])
@login_required
def proposal_items_api(id):
    proposal = Proposal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    # Implementation
    return jsonify({'success': True, 'data': data})
```

### Template Pattern:
```html
{% extends "base.html" %}
{% block title %}Page Title{% endblock %}
{% block content %}
<!-- Bootstrap 5 components -->
{% endblock %}
```

## Naming Conventions
- Python: snake_case
- JavaScript: camelCase
- CSS classes: kebab-case (Bootstrap convention)
- Database: snake_case
- URLs: kebab-case

## Comments & Documentation
- Turkish comments for business logic
- English for technical documentation
- Docstrings for functions
- Inline comments for complex logic

Bu talimatları takip ederek tutarlı, güvenli ve kullanıcı dostu kod üretin.
