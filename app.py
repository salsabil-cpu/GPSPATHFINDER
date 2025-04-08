import os
import tempfile
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
import pandas as pd
import folium
from flask_login import LoginManager, current_user
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash
from models import db, User, UserRole

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Configure file uploads
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Authentification requise pour accéder à cette fonctionnalité.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.main import main_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(main_bp)

# Create initial admin user if no users exist
with app.app_context():
    # Create tables
    db.create_all()
    
    # Check if there are any users in the database
    if User.query.count() == 0:
        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            role=UserRole.ADMIN,
            is_active=True
        )
        admin.set_password('admin123')  # Set a secure password in production
        db.session.add(admin)
        db.session.commit()
        logging.info('Initial admin user created')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
