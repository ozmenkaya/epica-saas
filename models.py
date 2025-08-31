from app import db
from flask_login import UserMixin
from datetime import datetime

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # İlişkiler
    items = db.relationship('ProposalItem', backref='proposal', lazy=True, cascade='all, delete-orphan')
    
    def calculate_total(self):
        total = sum(item.total_price for item in self.items)
        self.total_amount = total
        return total
    
    def __repr__(self):
        return f'<Proposal {self.title}>'

class ProposalItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float)
    
    # Foreign Keys
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposal.id'), nullable=False)
    
    def __init__(self, **kwargs):
        super(ProposalItem, self).__init__(**kwargs)
        self.calculate_total()
    
    def calculate_total(self):
        self.total_price = self.quantity * self.unit_price
        return self.total_price
    
    def __repr__(self):
        return f'<ProposalItem {self.name}>'
