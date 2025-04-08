import os
import tempfile
import logging
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
import pandas as pd
import folium
from werkzeug.utils import secure_filename
from utils.route_optimizer import optimize_route
from utils.geo_utils import validate_coordinates, calculate_distance

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure file uploads
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate_route', methods=['POST'])
def calculate_route():
    try:
        # Get form data
        start_lat = float(request.form.get('start_lat', 0))
        start_lng = float(request.form.get('start_lng', 0))
        
        # Validate starting point
        if not validate_coordinates(start_lat, start_lng):
            flash('Invalid starting coordinates', 'danger')
            return redirect(url_for('index'))
        
        # Process waypoints from form
        waypoints = []
        waypoint_names = request.form.getlist('waypoint_name[]')
        waypoint_lats = request.form.getlist('waypoint_lat[]')
        waypoint_lngs = request.form.getlist('waypoint_lng[]')
        
        # Process each waypoint
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
                logging.error(f"Error processing waypoint {i}: {e}")
                continue
        
        # Check if we have enough waypoints
        if len(waypoints) < 1:
            flash('Please add at least one valid waypoint', 'warning')
            return redirect(url_for('index'))
        
        # Starting point
        start_point = {
            'name': 'Start',
            'lat': start_lat,
            'lng': start_lng
        }
        
        # Optimize route (TSP solution)
        optimized_route = optimize_route(start_point, waypoints)
        
        # Create map
        map_center = [start_lat, start_lng]
        m = folium.Map(location=map_center, zoom_start=13)
        
        # Add markers and path to map
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
        
        # Add polyline
        folium.PolyLine(
            coordinates,
            weight=3,
            color='blue',
            opacity=0.7
        ).add_to(m)
        
        # Generate Google Maps URL
        google_maps_url = "https://www.google.com/maps/dir/?api=1&origin={},{}&destination={},{}&waypoints={}".format(
            start_lat, 
            start_lng,
            optimized_route[-1]['lat'],
            optimized_route[-1]['lng'],
            "|".join([f"{p['lat']},{p['lng']}" for p in optimized_route[1:-1]])
        )
        
        # Calculate total distance
        total_distance = 0
        for i in range(len(optimized_route) - 1):
            point1 = (optimized_route[i]['lat'], optimized_route[i]['lng'])
            point2 = (optimized_route[i + 1]['lat'], optimized_route[i + 1]['lng'])
            total_distance += calculate_distance(point1, point2)
        
        # Save map to HTML file
        map_html = m._repr_html_()
        
        return render_template(
            'map.html',
            map_html=map_html,
            route=optimized_route,
            google_maps_url=google_maps_url,
            total_distance=total_distance
        )
    
    except Exception as e:
        logging.error(f"Error calculating route: {str(e)}")
        flash(f'Error calculating route: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Read Excel file
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            # Validate required columns
            required_columns = ['name', 'lat', 'lng']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return jsonify({
                    'error': f'Missing required columns: {", ".join(missing_columns)}. ' +
                            'File must contain columns: name, lat, lng'
                }), 400
            
            # Convert to list of dictionaries
            waypoints = df.to_dict('records')
            
            # Validate coordinates
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
            logging.error(f"Error processing Excel file: {str(e)}")
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
        
        finally:
            # Clean up temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    return jsonify({'error': 'Invalid file type. Please upload .xlsx, .xls, or .csv files'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
