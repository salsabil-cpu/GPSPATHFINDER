import os
import logging
import tempfile
import json
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
import pandas as pd
import folium
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from models import SavedRoute
from utils.route_optimizer import optimize_route
from utils.geo_utils import validate_coordinates, calculate_distance, format_distance

# Définir les extensions de fichiers autorisées
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Créer le blueprint principal
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    return render_template('index.html')

@main_bp.route('/calculate_route', methods=['POST'])
@login_required
def calculate_route():
    try:
        # Récupérer les données du formulaire
        start_lat = float(request.form.get('start_lat', 0))
        start_lng = float(request.form.get('start_lng', 0))
        
        # Valider le point de départ
        if not validate_coordinates(start_lat, start_lng):
            flash('Coordonnées de départ invalides', 'danger')
            return redirect(url_for('main.index'))
        
        # Traiter les points de passage du formulaire
        waypoints = []
        waypoint_names = request.form.getlist('waypoint_name[]')
        waypoint_lats = request.form.getlist('waypoint_lat[]')
        waypoint_lngs = request.form.getlist('waypoint_lng[]')
        
        # Traiter chaque point de passage
        for i in range(len(waypoint_lats)):
            try:
                name = waypoint_names[i] if i < len(waypoint_names) else f"Point {i+1}"
                lat = float(waypoint_lats[i])
                lng = float(waypoint_lngs[i])
                
                if validate_coordinates(lat, lng):
                    waypoints.append({
                        'name': name,
                        'lat': lat,
                        'lng': lng
                    })
            except (ValueError, IndexError) as e:
                logging.error(f"Erreur de traitement du point {i}: {e}")
                continue
        
        # Vérifier si nous avons assez de points de passage
        if len(waypoints) < 1:
            flash('Veuillez ajouter au moins un point de passage valide', 'warning')
            return redirect(url_for('main.index'))
        
        # Point de départ
        start_point = {
            'name': 'Départ',
            'lat': start_lat,
            'lng': start_lng
        }
        
        # Optimiser l'itinéraire (solution TSP)
        optimized_route = optimize_route(start_point, waypoints)
        
        # Créer la carte
        map_center = [start_lat, start_lng]
        m = folium.Map(location=map_center, zoom_start=13)
        
        # Ajouter des marqueurs et un chemin à la carte
        coordinates = []
        for i, point in enumerate(optimized_route):
            tooltip = point['name']
            icon_color = 'green' if i == 0 else 'red' if i == len(optimized_route) - 1 else 'blue'
            folium.Marker(
                [point['lat'], point['lng']], 
                tooltip=tooltip,
                popup=tooltip,
                icon=folium.Icon(color=icon_color)
            ).add_to(m)
            coordinates.append([point['lat'], point['lng']])
        
        # Ajouter une ligne pour le trajet
        folium.PolyLine(
            coordinates,
            weight=3,
            color='blue',
            opacity=0.7
        ).add_to(m)
        
        # Générer l'URL Google Maps
        google_maps_url = "https://www.google.com/maps/dir/?api=1&origin={},{}&destination={},{}&waypoints={}".format(
            start_lat, 
            start_lng,
            optimized_route[-1]['lat'],
            optimized_route[-1]['lng'],
            "|".join([f"{p['lat']},{p['lng']}" for p in optimized_route[1:-1]])
        )
        
        # Calculer la distance totale
        total_distance = 0
        for i in range(len(optimized_route) - 1):
            point1 = (optimized_route[i]['lat'], optimized_route[i]['lng'])
            point2 = (optimized_route[i + 1]['lat'], optimized_route[i + 1]['lng'])
            total_distance += calculate_distance(point1, point2)
        
        # Enregistrer la carte en HTML
        map_html = m._repr_html_()
        
        # On peut sauvegarder la route si l'utilisateur est connecté
        can_save = current_user.is_authenticated
        
        return render_template(
            'map.html',
            map_html=map_html,
            route=optimized_route,
            google_maps_url=google_maps_url,
            total_distance=total_distance,
            can_save=can_save,
            saved_route=False
        )
    
    except Exception as e:
        logging.error(f"Erreur lors du calcul de l'itinéraire: {str(e)}")
        flash(f'Erreur lors du calcul de l\'itinéraire: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/upload_excel', methods=['POST'])
@login_required
def upload_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(tempfile.gettempdir(), filename)
            file.save(filepath)
            
            # Lire le fichier Excel
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            # Valider les colonnes requises
            required_columns = ['name', 'lat', 'lng']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return jsonify({
                    'error': f'Colonnes manquantes: {", ".join(missing_columns)}. ' +
                            'Le fichier doit contenir les colonnes: name, lat, lng'
                }), 400
            
            # Convertir en liste de dictionnaires
            waypoints = df.to_dict('records')
            
            # Valider les coordonnées
            valid_waypoints = []
            for point in waypoints:
                try:
                    if validate_coordinates(float(point['lat']), float(point['lng'])):
                        valid_waypoints.append({
                            'name': str(point['name']),
                            'lat': float(point['lat']),
                            'lng': float(point['lng'])
                        })
                except (ValueError, TypeError):
                    continue
            
            return jsonify({'waypoints': valid_waypoints})
        
        except Exception as e:
            logging.error(f"Erreur lors du traitement du fichier Excel: {str(e)}")
            return jsonify({'error': f'Erreur lors du traitement du fichier: {str(e)}'}), 500
        
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(filepath):
                os.remove(filepath)
    
    return jsonify({'error': 'Type de fichier invalide. Veuillez télécharger des fichiers .xlsx, .xls ou .csv'}), 400

@main_bp.route('/save_route', methods=['POST'])
@login_required
def save_route():
    try:
        # Récupérer les données du formulaire
        route_name = request.form.get('route_name')
        start_point = json.loads(request.form.get('start_point'))
        waypoints = json.loads(request.form.get('waypoints'))
        total_distance = float(request.form.get('total_distance', 0))
        
        # Créer un nouvel enregistrement d'itinéraire
        new_route = SavedRoute(
            name=route_name,
            user_id=current_user.id,
            start_point=start_point,
            waypoints=waypoints,
            total_distance=total_distance
        )
        
        # Sauvegarder dans la base de données
        db.session.add(new_route)
        db.session.commit()
        
        flash(f'Itinéraire "{route_name}" sauvegardé avec succès.', 'success')
        return redirect(url_for('main.my_routes'))
    
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde de l'itinéraire: {str(e)}")
        flash(f'Erreur lors de la sauvegarde de l\'itinéraire: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/my_routes')
@login_required
def my_routes():
    # Récupérer tous les itinéraires de l'utilisateur actuel
    routes = SavedRoute.query.filter_by(user_id=current_user.id).order_by(SavedRoute.created_at.desc()).all()
    return render_template('my_routes.html', routes=routes)

@main_bp.route('/route/<int:route_id>')
@login_required
def view_route(route_id):
    # Récupérer l'itinéraire sauvegardé
    route = SavedRoute.query.get_or_404(route_id)
    
    # Vérifier si l'utilisateur actuel est propriétaire de cet itinéraire
    if route.user_id != current_user.id and not current_user.is_admin():
        flash('Vous n\'avez pas accès à cet itinéraire.', 'danger')
        return redirect(url_for('main.my_routes'))
    
    # Récupérer les données de l'itinéraire
    start_point = route.start_point
    waypoints = route.waypoints
    
    # Recréer l'itinéraire complet
    optimized_route = [start_point] + waypoints
    
    # Créer la carte
    map_center = [start_point['lat'], start_point['lng']]
    m = folium.Map(location=map_center, zoom_start=13)
    
    # Ajouter des marqueurs et un chemin à la carte
    coordinates = []
    for i, point in enumerate(optimized_route):
        tooltip = point['name']
        icon_color = 'green' if i == 0 else 'red' if i == len(optimized_route) - 1 else 'blue'
        folium.Marker(
            [point['lat'], point['lng']], 
            tooltip=tooltip,
            popup=tooltip,
            icon=folium.Icon(color=icon_color)
        ).add_to(m)
        coordinates.append([point['lat'], point['lng']])
    
    # Ajouter une ligne pour le trajet
    folium.PolyLine(
        coordinates,
        weight=3,
        color='blue',
        opacity=0.7
    ).add_to(m)
    
    # Générer l'URL Google Maps
    google_maps_url = "https://www.google.com/maps/dir/?api=1&origin={},{}&destination={},{}&waypoints={}".format(
        start_point['lat'], 
        start_point['lng'],
        optimized_route[-1]['lat'],
        optimized_route[-1]['lng'],
        "|".join([f"{p['lat']},{p['lng']}" for p in optimized_route[1:-1]])
    )
    
    # Enregistrer la carte en HTML
    map_html = m._repr_html_()
    
    return render_template(
        'map.html',
        map_html=map_html,
        route=optimized_route,
        google_maps_url=google_maps_url,
        total_distance=route.total_distance,
        can_save=False,
        saved_route=True,
        route_name=route.name
    )

@main_bp.route('/route/<int:route_id>/delete', methods=['POST'])
@login_required
def delete_route(route_id):
    # Récupérer l'itinéraire à supprimer
    route = SavedRoute.query.get_or_404(route_id)
    
    # Vérifier si l'utilisateur actuel est propriétaire de cet itinéraire
    if route.user_id != current_user.id and not current_user.is_admin():
        flash('Vous n\'avez pas accès à cet itinéraire.', 'danger')
        return redirect(url_for('main.my_routes'))
    
    # Supprimer l'itinéraire
    route_name = route.name
    db.session.delete(route)
    db.session.commit()
    
    flash(f'Itinéraire "{route_name}" supprimé avec succès.', 'success')
    return redirect(url_for('main.my_routes'))