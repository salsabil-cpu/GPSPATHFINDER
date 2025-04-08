from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, get_flashed_messages
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError
import re

from app import db
from models import User, UserRole

# Créer le blueprint d'authentification
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation des données
        if not username or not email or not password or not confirm_password:
            flash('Tous les champs sont requis.', 'danger')
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('auth.register'))
            
        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Validation du format de l'email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash('Adresse e-mail invalide.', 'danger')
            return redirect(url_for('auth.register'))
            
        # Vérifier si l'utilisateur ou l'email existe déjà
        username_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()
        
        if username_exists:
            flash('Ce nom d\'utilisateur est déjà utilisé.', 'danger')
            return redirect(url_for('auth.register'))
            
        if email_exists:
            flash('Cette adresse e-mail est déjà utilisée.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Créer un nouvel utilisateur (inactif par défaut)
        try:
            new_user = User(
                username=username,
                email=email,
                role=UserRole.USER,
                is_active=False,
                is_verified=False
            )
            new_user.set_password(password)
            
            # Générer un code d'activation
            activation_code = new_user.generate_activation_code()
            
            db.session.add(new_user)
            db.session.commit()
            
            flash(f'Inscription réussie! Veuillez contacter un administrateur pour obtenir votre code d\'activation.', 'success')
            return redirect(url_for('auth.activate_account'))
        except IntegrityError:
            db.session.rollback()
            flash('Une erreur est survenue lors de l\'inscription. Veuillez réessayer.', 'danger')
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html')

@auth_bp.route('/activate', methods=['GET', 'POST'])
def activate_account():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        activation_code = request.form.get('activation_code')
        
        if not username or not activation_code:
            flash('Tous les champs sont requis.', 'danger')
            return redirect(url_for('auth.activate_account'))
        
        # Rechercher l'utilisateur
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if not user:
            flash('Utilisateur non trouvé.', 'danger')
            return redirect(url_for('auth.activate_account'))
            
        # Vérifier si le compte est déjà activé
        if user.is_verified and user.is_active:
            flash('Ce compte est déjà activé. Vous pouvez vous connecter.', 'info')
            return redirect(url_for('auth.login'))
            
        # Activer le compte
        if user.activate_account(activation_code):
            db.session.commit()
            flash('Votre compte a été activé avec succès! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Code d\'activation invalide ou expiré.', 'danger')
            return redirect(url_for('auth.activate_account'))
    
    return render_template('auth/activate.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        # Récupérer l'utilisateur par nom d'utilisateur ou email
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        # Vérifier si l'utilisateur existe et si le mot de passe est correct
        if not user or not user.check_password(password):
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'danger')
            return redirect(url_for('auth.login'))
            
        # Vérifier si le compte est actif
        if not user.is_active:
            flash('Ce compte a été désactivé. Veuillez contacter un administrateur.', 'warning')
            return redirect(url_for('auth.login'))
            
        # Vérifier si le compte est vérifié
        if not user.is_verified:
            flash('Ce compte n\'a pas encore été vérifié. Veuillez activer votre compte avec le code fourni par l\'administrateur.', 'warning')
            return redirect(url_for('auth.activate_account'))
            
        # Vérifier si l'accès est encore valide
        if not user.has_valid_access():
            flash('Votre période d\'accès a expiré. Veuillez contacter un administrateur.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Connexion réussie, mettre à jour last_login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Se connecter
        login_user(user, remember=remember)
        flash(f'Bienvenue, {user.username}!', 'success')
        
        # Rediriger vers la page demandée ou la page d'accueil
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
@login_required
def profile():
    # Création d'une page HTML simple sans utiliser Jinja2
    html = """
    <!DOCTYPE html>
    <html lang="fr" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mon profil - GPS Route Optimizer</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        <div class="container py-4">
            <div class="row mb-4">
                <div class="col-12">
                    <h1 class="text-center"><i class="fas fa-route"></i> GPS Route Optimizer</h1>
                    <p class="text-center lead">Mon profil</p>
                </div>
            </div>

            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="list-group">
                        <a href="/index" class="list-group-item list-group-item-action">
                            <i class="fas fa-map-marked-alt"></i> Calculer un itinéraire
                        </a>
                        <a href="/my_routes" class="list-group-item list-group-item-action">
                            <i class="fas fa-list"></i> Mes itinéraires
                        </a>
                        <a href="/profile" class="list-group-item list-group-item-action active">
                            <i class="fas fa-user-circle"></i> Mon profil
                        </a>
    """
    
    # Ajouter le lien d'administration si l'utilisateur est admin
    if current_user.is_admin():
        html += """
                        <a href="/admin" class="list-group-item list-group-item-action">
                            <i class="fas fa-tachometer-alt"></i> Administration
                        </a>
        """
        
    html += """
                        <a href="/logout" class="list-group-item list-group-item-action text-danger">
                            <i class="fas fa-sign-out-alt"></i> Déconnexion
                        </a>
                    </div>
                </div>
                <div class="col-md-9">
    """
    
    # Ajouter les messages flash
    messages = []
    with_categories = True
    for category, message in get_flashed_messages(with_categories=with_categories):
        messages.append(f"""
            <div class="alert alert-{category} alert-dismissible fade show" role="alert">
                {message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        """)
    
    if messages:
        for message in messages:
            html += message
    
    html += f"""
                    <div class="card mb-4">
                        <div class="card-header">
                            <h3 class="mb-0"><i class="fas fa-info-circle"></i> Informations du compte</h3>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>Nom d'utilisateur:</strong> {current_user.username}</p>
                                    <p><strong>Email:</strong> {current_user.email}</p>
                                    <p><strong>Rôle:</strong> {"Administrateur" if current_user.is_admin() else "Utilisateur"}</p>
                                </div>
                                <div class="col-md-6">
                                    <p><strong>Compte actif:</strong> {"Oui" if current_user.is_active else "Non"}</p>
                                    <p><strong>Compte vérifié:</strong> {"Oui" if current_user.is_verified else "Non"}</p>
                                    <p><strong>Accès jusqu'au:</strong> {current_user.access_until.strftime('%d/%m/%Y') if current_user.access_until else "Illimité"}</p>
                                    <p><strong>Dernière connexion:</strong> {current_user.last_login.strftime('%d/%m/%Y %H:%M') if current_user.last_login else "Jamais"}</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-header">
                            <h3 class="mb-0"><i class="fas fa-key"></i> Changer le mot de passe</h3>
                        </div>
                        <div class="card-body">
                            <form method="POST" action="/change-password">
                                <div class="mb-3">
                                    <label for="current_password" class="form-label">Mot de passe actuel</label>
                                    <input type="password" class="form-control" id="current_password" name="current_password" required>
                                </div>
                                <div class="mb-3">
                                    <label for="new_password" class="form-label">Nouveau mot de passe</label>
                                    <input type="password" class="form-control" id="new_password" name="new_password" required>
                                </div>
                                <div class="mb-3">
                                    <label for="confirm_password" class="form-label">Confirmer le nouveau mot de passe</label>
                                    <input type="password" class="form-control" id="confirm_password" name="confirm_password" required>
                                </div>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save"></i> Mettre à jour le mot de passe
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    
    # Retourner le HTML directement
    return html

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Vérifier si le mot de passe actuel est correct
    if not current_user.check_password(current_password):
        flash('Le mot de passe actuel est incorrect.', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Vérifier si les nouveaux mots de passe correspondent
    if new_password != confirm_password:
        flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Vérifier si le nouveau mot de passe est suffisamment long
    if len(new_password) < 6:
        flash('Le nouveau mot de passe doit contenir au moins 6 caractères.', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Mettre à jour le mot de passe
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Votre mot de passe a été mis à jour avec succès.', 'success')
    return redirect(url_for('auth.profile'))