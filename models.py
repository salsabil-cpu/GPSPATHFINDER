from datetime import datetime, timedelta
import random
import string
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from enum import Enum

db = SQLAlchemy()

class UserRole(Enum):
    ADMIN = 'admin'
    USER = 'user'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)  # Changé à False par défaut
    is_verified = db.Column(db.Boolean, default=False, nullable=False)  # Nouveau champ pour vérification
    activation_code = db.Column(db.String(20), nullable=True, index=True)  # Code d'activation
    activation_code_expires = db.Column(db.DateTime, nullable=True)  # Date d'expiration du code
    access_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relations
    saved_routes = db.relationship('SavedRoute', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == UserRole.ADMIN
    
    def has_valid_access(self):
        if self.is_admin():
            return True
        if not self.is_active or not self.is_verified:
            return False
        if self.access_until is None:
            return True
        return datetime.utcnow() <= self.access_until
    
    def generate_activation_code(self, expiration_days=7):
        """Génère un code d'activation unique qui expire après expiration_days jours"""
        # Générer un code de 8 caractères (lettres majuscules et chiffres)
        code_chars = string.ascii_uppercase + string.digits
        self.activation_code = ''.join(random.choice(code_chars) for _ in range(8))
        
        # Définir la date d'expiration
        self.activation_code_expires = datetime.utcnow() + timedelta(days=expiration_days)
        
        return self.activation_code
    
    def check_activation_code(self, code):
        """Vérifie si le code d'activation fourni est valide et non expiré"""
        if not self.activation_code or not code:
            return False
        
        if not self.activation_code_expires or datetime.utcnow() > self.activation_code_expires:
            return False
            
        return self.activation_code == code
    
    def activate_account(self, code):
        """Active le compte si le code d'activation est valide"""
        if self.check_activation_code(code):
            self.is_verified = True
            self.is_active = True
            self.activation_code = None
            self.activation_code_expires = None
            return True
        return False

class SavedRoute(db.Model):
    __tablename__ = 'saved_routes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_point = db.Column(db.JSON, nullable=False)
    waypoints = db.Column(db.JSON, nullable=False)
    total_distance = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)