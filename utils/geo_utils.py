from geopy.distance import geodesic
import math

def validate_coordinates(lat, lng):
    """
    Validates if the given latitude and longitude are valid.
    
    Args:
        lat (float): Latitude
        lng (float): Longitude
    
    Returns:
        bool: True if coordinates are valid, False otherwise
    """
    try:
        lat = float(lat)
        lng = float(lng)
        return -90 <= lat <= 90 and -180 <= lng <= 180
    except (ValueError, TypeError):
        return False

def calculate_distance(point1, point2):
    """
    Calculates the distance between two points in kilometers.
    
    Args:
        point1 (tuple): (latitude, longitude) of first point
        point2 (tuple): (latitude, longitude) of second point
    
    Returns:
        float: Distance in kilometers
    """
    return geodesic(point1, point2).kilometers

def format_distance(distance_km):
    """
    Formats a distance in kilometers to a human-readable string.
    
    Args:
        distance_km (float): Distance in kilometers
    
    Returns:
        str: Formatted distance string
    """
    if distance_km < 1:
        return f"{math.ceil(distance_km * 1000)} m"
    else:
        return f"{distance_km:.1f} km"
