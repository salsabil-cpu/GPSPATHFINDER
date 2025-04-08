from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash


from models import User, UserRole, SavedRoute
# from app import db
from extensions import db, login_manager  # 👈 Import modifié
# Créer le blueprint d'administration
admin_bp = Blueprint('admin', __name__)

# Décorateur qui vérifie si l'utilisateur est un administrateur
def admin_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('Accès refusé. Vous devez être administrateur pour accéder à cette page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/admin')
@admin_required
def index():
    # Rediriger directement vers la page des utilisateurs au lieu d'essayer d'utiliser le template manquant
    return redirect(url_for('admin.users'))

@admin_bp.route('/admin/users')
@admin_required
def users():
    # Récupérer tous les utilisateurs
    users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = UserRole.ADMIN if request.form.get('role') == 'admin' else UserRole.USER
        is_active = 'is_active' in request.form
        is_verified = 'is_verified' in request.form
        access_days = int(request.form.get('access_days', 0))
        
        # Vérifier si l'utilisateur existe déjà
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Un utilisateur avec ce nom ou cet email existe déjà.', 'danger')
            return redirect(url_for('admin.users'))
        
        # Créer le nouvel utilisateur
        # L'activation et la vérification des administrateurs sont gérées dans le modèle User
            
        new_user = User(
            username=username,
            email=email,
            role=role,
            is_active=is_active,
            is_verified=is_verified
        )
        new_user.set_password(password)
        
        # Configurer la date d'expiration si nécessaire
        if access_days > 0:
            new_user.access_until = datetime.utcnow() + timedelta(days=access_days)
        
        # Enregistrer l'utilisateur dans la base de données
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'L\'utilisateur {username} a été créé avec succès.', 'success')
        return redirect(url_for('admin.users'))
    
    # Création d'un formulaire HTML intégré directement dans la fonction
    form_html = """
    <!DOCTYPE html>
    <html lang="fr" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ajouter un utilisateur - GPS Route Optimizer</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        <div class="container py-4">
            <div class="row mb-4">
                <div class="col-12">
                    <h1 class="text-center"><i class="fas fa-route"></i> GPS Route Optimizer</h1>
                    <p class="text-center lead">Ajouter un utilisateur</p>
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
                        <a href="/profile" class="list-group-item list-group-item-action">
                            <i class="fas fa-user-circle"></i> Mon profil
                        </a>
                        <a href="/admin" class="list-group-item list-group-item-action">
                            <i class="fas fa-tachometer-alt"></i> Tableau de bord
                        </a>
                        <a href="/admin/users" class="list-group-item list-group-item-action">
                            <i class="fas fa-users"></i> Utilisateurs
                        </a>
                        <a href="/logout" class="list-group-item list-group-item-action text-danger">
                            <i class="fas fa-sign-out-alt"></i> Déconnexion
                        </a>
                    </div>
                </div>
                <div class="col-md-9">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="mb-0"><i class="fas fa-user-plus"></i> Nouvel utilisateur</h3>
                        </div>
                        <div class="card-body">
                            <form method="POST" action="/admin/users/add">
                                <div class="mb-3">
                                    <label for="username" class="form-label">Nom d'utilisateur</label>
                                    <input type="text" class="form-control" id="username" name="username" required>
                                </div>
                                <div class="mb-3">
                                    <label for="email" class="form-label">Email</label>
                                    <input type="email" class="form-control" id="email" name="email" required>
                                </div>
                                <div class="mb-3">
                                    <label for="password" class="form-label">Mot de passe</label>
                                    <input type="password" class="form-control" id="password" name="password" required>
                                </div>
                                <div class="mb-3">
                                    <label for="role" class="form-label">Rôle</label>
                                    <select class="form-select" id="role" name="role">
                                        <option value="user">Utilisateur</option>
                                        <option value="admin">Administrateur</option>
                                    </select>
                                </div>
                                <div class="mb-3 form-check">
                                    <input type="checkbox" class="form-check-input" id="is_active" name="is_active" checked>
                                    <label class="form-check-label" for="is_active">Compte actif</label>
                                </div>
                                <div class="mb-3 form-check">
                                    <input type="checkbox" class="form-check-input" id="is_verified" name="is_verified" checked>
                                    <label class="form-check-label" for="is_verified">Compte vérifié</label>
                                </div>
                                <div class="mb-3">
                                    <label for="access_days" class="form-label">Durée d'accès (jours)</label>
                                    <input type="number" class="form-control" id="access_days" name="access_days" min="0" value="0">
                                    <div class="form-text">0 = Accès illimité</div>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <a href="/admin/users" class="btn btn-outline-secondary">
                                        <i class="fas fa-arrow-left"></i> Retour
                                    </a>
                                    <button type="submit" class="btn btn-primary">
                                        <i class="fas fa-save"></i> Enregistrer
                                    </button>
                                </div>
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
    return form_html

@admin_bp.route('/admin/users/<int:user_id>/generate-activation', methods=['GET'])
@admin_required
def generate_activation_code(user_id):
    # Récupérer l'utilisateur
    user = User.query.get_or_404(user_id)
    
    # Générer un nouveau code d'activation
    activation_code = user.generate_activation_code()
    
    # Enregistrer les modifications
    db.session.commit()
    
    flash(f'Code d\'activation généré pour {user.username}: {activation_code}', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    # Récupérer l'utilisateur à modifier
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = UserRole.ADMIN if request.form.get('role') == 'admin' else UserRole.USER
        is_active = 'is_active' in request.form
        is_verified = 'is_verified' in request.form  # Nouvel attribut
        reset_access = 'reset_access' in request.form
        access_days = int(request.form.get('access_days', 0))
        
        # Vérifier si un autre utilisateur avec le même nom ou email existe
        existing_user = User.query.filter(
            (User.id != user_id) & ((User.username == username) | (User.email == email))
        ).first()
        
        if existing_user:
            flash('Un autre utilisateur avec ce nom ou cet email existe déjà.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
        
        # Mettre à jour les informations de l'utilisateur
        user.username = username
        user.email = email
        user.role = role
        
        # L'activation et la vérification des administrateurs sont gérées dans le modèle User
            
        user.is_active = is_active
        user.is_verified = is_verified
        
        # Mettre à jour le mot de passe si fourni
        if password:
            user.set_password(password)
        
        # Réinitialiser la date d'accès si demandé
        if reset_access:
            if access_days > 0:
                user.access_until = datetime.utcnow() + timedelta(days=access_days)
            else:
                user.access_until = None
        
        # Enregistrer les modifications
        db.session.commit()
        
        flash(f'L\'utilisateur {username} a été mis à jour avec succès.', 'success')
        return redirect(url_for('admin.users'))
    
    # Création d'un formulaire HTML intégré directement dans la fonction
    form_html = f"""
    <!DOCTYPE html>
    <html lang="fr" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Modifier un utilisateur - GPS Route Optimizer</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        <div class="container py-4">
            <div class="row mb-4">
                <div class="col-12">
                    <h1 class="text-center"><i class="fas fa-route"></i> GPS Route Optimizer</h1>
                    <p class="text-center lead">Modifier un utilisateur</p>
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
                        <a href="/profile" class="list-group-item list-group-item-action">
                            <i class="fas fa-user-circle"></i> Mon profil
                        </a>
                        <a href="/admin" class="list-group-item list-group-item-action">
                            <i class="fas fa-tachometer-alt"></i> Tableau de bord
                        </a>
                        <a href="/admin/users" class="list-group-item list-group-item-action">
                            <i class="fas fa-users"></i> Utilisateurs
                        </a>
                        <a href="/logout" class="list-group-item list-group-item-action text-danger">
                            <i class="fas fa-sign-out-alt"></i> Déconnexion
                        </a>
                    </div>
                </div>
                <div class="col-md-9">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="mb-0"><i class="fas fa-user-edit"></i> Modifier un utilisateur</h3>
                        </div>
                        <div class="card-body">
                            <form method="POST" action="/admin/users/{user_id}/edit" id="edit-user-form">
                                <div class="mb-3">
                                    <label for="username" class="form-label">Nom d'utilisateur</label>
                                    <input type="text" class="form-control" id="username" name="username" value="{user.username}" required>
                                </div>
                                <div class="mb-3">
                                    <label for="email" class="form-label">Email</label>
                                    <input type="email" class="form-control" id="email" name="email" value="{user.email}" required>
                                </div>
                                <div class="mb-3">
                                    <label for="password" class="form-label">Mot de passe (laisser vide pour conserver l'actuel)</label>
                                    <input type="password" class="form-control" id="password" name="password">
                                    <div class="form-text">Laissez ce champ vide si vous ne souhaitez pas modifier le mot de passe</div>
                                </div>
                                <div class="mb-3">
                                    <label for="role" class="form-label">Rôle</label>
                                    <select class="form-select" id="role" name="role">
                                        <option value="user" {"selected" if user.role == UserRole.USER else ""}>Utilisateur</option>
                                        <option value="admin" {"selected" if user.role == UserRole.ADMIN else ""}>Administrateur</option>
                                    </select>
                                    <div class="form-text">Note: Les administrateurs sont automatiquement activés et vérifiés.</div>
                                </div>
                                <div class="mb-3 form-check">
                                    <input type="checkbox" class="form-check-input" id="is_active" name="is_active" {"checked" if user.is_active else ""}>
                                    <label class="form-check-label" for="is_active">Compte actif</label>
                                </div>
                                <div class="mb-3 form-check">
                                    <input type="checkbox" class="form-check-input" id="is_verified" name="is_verified" {"checked" if user.is_verified else ""}>
                                    <label class="form-check-label" for="is_verified">Compte vérifié</label>
                                </div>

                                <div class="mb-3 form-check">
                                    <input type="checkbox" class="form-check-input" id="reset_access" name="reset_access">
                                    <label class="form-check-label" for="reset_access">Réinitialiser la durée d'accès</label>
                                </div>
                                <div class="mb-3">
                                    <label for="access_days" class="form-label">Nouvelle durée d'accès (jours)</label>
                                    <input type="number" class="form-control" id="access_days" name="access_days" min="0" value="0">
                                    <div class="form-text">0 = Accès illimité. Ne sera appliqué que si "Réinitialiser la durée d'accès" est coché.</div>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <a href="/admin/users" class="btn btn-outline-secondary">
                                        <i class="fas fa-arrow-left"></i> Retour
                                    </a>
                                    <button type="submit" class="btn btn-primary">
                                        <i class="fas fa-save"></i> Enregistrer
                                    </button>
                                </div>
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
    return form_html

@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    # Récupérer l'utilisateur à supprimer
    user = User.query.get_or_404(user_id)
    
    # Vérifier que l'utilisateur n'essaie pas de se supprimer lui-même
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('admin.users'))
    
    # Supprimer l'utilisateur
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'L\'utilisateur {username} a été supprimé avec succès.', 'success')
    return redirect(url_for('admin.users'))