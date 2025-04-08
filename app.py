import logging
import os
import tempfile

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from extensions import db, login_manager  # 👈 Import modifié

# Création de l'app Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configuration de la base de données
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///gpspathfinder.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialisation des extensions AVANT les imports de blueprints 👇
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = None

# Configuration des uploads
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Import des blueprints APRÈS initialisation des extensions
from routes.auth import auth_bp  # 👈 Ordre modifié
from routes.admin import admin_bp
from routes.main import main_bp

# Enregistrement des blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(main_bp)


# User loader
@login_manager.user_loader
def load_user(user_id):
    from models import User  # 👈 Import local pour éviter les circulaires
    return User.query.get(int(user_id))


# Création de l'admin initial
with app.app_context():
    db.create_all()

    from models import User, UserRole  # 👈 Import local

    if User.query.count() == 0:
        admin = User(
            username='admin',
            email='admin@example.com',
            role=UserRole.ADMIN,
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        logging.info('Admin créé')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
