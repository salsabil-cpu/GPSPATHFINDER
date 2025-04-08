import random
import string
from datetime import datetime, timedelta
from enum import Enum

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db  # 👈 Modification clé : import depuis extensions


class UserRole(Enum):
    ADMIN = 'admin'
    USER = 'user'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    # Colonnes principales
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    _role = db.Column('role', db.Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    activation_code = db.Column(db.String(20), nullable=True, index=True)
    activation_code_expires = db.Column(db.DateTime, nullable=True)
    access_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relations
    saved_routes = db.relationship('SavedRoute', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.initialize_admin_properties()

    def initialize_admin_properties(self):
        """Initialise les propriétés spéciales pour les administrateurs"""
        if hasattr(self, '_role') and self._role == UserRole.ADMIN:
            self.is_active = True
            self.is_verified = True

    @property
    def role(self):
        return self._role

    @role.setter
    def role(self, value):
        self._role = value
        if value == UserRole.ADMIN:
            self.is_active = True
            self.is_verified = True

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self._role == UserRole.ADMIN

    def has_valid_access(self):
        if self.is_admin():
            return True
        return self.is_active and self.is_verified and (
                self.access_until is None or datetime.utcnow() <= self.access_until
        )

    def generate_activation_code(self, expiration_days=7):
        """Génère un code d'activation unique"""
        code_chars = string.ascii_uppercase + string.digits
        self.activation_code = ''.join(random.choices(code_chars, k=8))
        self.activation_code_expires = datetime.utcnow() + timedelta(days=expiration_days)
        return self.activation_code

    def check_activation_code(self, code):
        """Vérifie la validité du code d'activation"""
        return (
                self.activation_code and
                code and
                self.activation_code_expires and
                datetime.utcnow() <= self.activation_code_expires and
                self.activation_code == code
        )

    def activate_account(self, code):
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
