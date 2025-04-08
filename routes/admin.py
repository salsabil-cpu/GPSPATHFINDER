from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from app import db
from models import User, UserRole, SavedRoute

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
    # Récupérer des statistiques
    stats = {
        'total_users': User.query.count(),
        'total_routes': SavedRoute.query.count()
    }
    
    # Récupérer les utilisateurs actifs
    active_users = User.query.filter_by(is_active=True).order_by(User.username).all()
    
    # Date actuelle pour les informations du serveur
    now = datetime.utcnow()
    
    return render_template('admin/index.html', stats=stats, active_users=active_users, now=now)

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
        access_days = int(request.form.get('access_days', 0))
        
        # Vérifier si l'utilisateur existe déjà
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Un utilisateur avec ce nom ou cet email existe déjà.', 'danger')
            return redirect(url_for('admin.add_user'))
        
        # Créer le nouvel utilisateur
        new_user = User(
            username=username,
            email=email,
            role=role,
            is_active=is_active
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
    
    return render_template('admin/add_user.html')

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
        user.is_active = is_active
        
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
    
    return render_template('admin/edit_user.html', user=user)

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