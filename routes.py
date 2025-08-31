from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db
from models import User, Proposal, ProposalItem
from datetime import datetime

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
        'total_value': total_value
    }
    
    return render_template('dashboard.html', proposals=proposals, stats=stats)

@app.route('/proposals')
@login_required
def proposals():
    proposals = Proposal.query.filter_by(user_id=current_user.id).order_by(Proposal.created_at.desc()).all()
    return render_template('proposals/list.html', proposals=proposals)

@app.route('/proposal/new', methods=['GET', 'POST'])
@login_required
def new_proposal():
    if request.method == 'POST':
        proposal = Proposal(
            title=request.form['title'],
            description=request.form['description'],
            client_name=request.form['client_name'],
            client_email=request.form['client_email'],
            client_phone=request.form['client_phone'],
            user_id=current_user.id
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

@app.route('/proposal/<int:id>/edit')
@login_required
def edit_proposal(id):
    proposal = Proposal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('proposals/edit.html', proposal=proposal)

@app.route('/proposal/<int:id>/delete', methods=['POST'])
@login_required
def delete_proposal(id):
    proposal = Proposal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(proposal)
    db.session.commit()
    flash('Teklif başarıyla silindi!', 'success')
    return redirect(url_for('proposals'))

# API Routes
@app.route('/api/proposal/<int:id>/items', methods=['GET', 'POST'])
@login_required
def proposal_items_api(id):
    proposal = Proposal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        data = request.get_json()
        
        item = ProposalItem(
            name=data['name'],
            description=data.get('description', ''),
            quantity=int(data['quantity']),
            unit_price=float(data['unit_price']),
            proposal_id=proposal.id
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
            'total_price': item.total_price
        }
        for item in proposal.items
    ]
    
    return jsonify({'items': items})

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
