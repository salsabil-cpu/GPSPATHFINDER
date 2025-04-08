from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from models import User

# Créer le blueprint d'authentification
auth_bp = Blueprint('auth', __name__)

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
    return render_template('auth/profile.html')

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