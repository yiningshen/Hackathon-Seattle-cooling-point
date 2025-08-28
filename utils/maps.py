import googlemaps
import folium
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from .config import Config

class MapService:
    def __init__(self):
        """Initialize MapService with Google Maps client"""
        # Validate API key before initializing
        Config.validate_api_key()
        self.gmaps = googlemaps.Client(key=Config.GOOGLE_MAPS_API_KEY)

    def create_base_map(self, 
                       center_lat: float = Config.DEFAULT_LAT, 
                       center_lng: float = Config.DEFAULT_LNG,
                       zoom: int = 12) -> folium.Map:
        """
        Create a base Folium map centered on specific coordinates
        
        Args:
            center_lat (float): Latitude for map center
            center_lng (float): Longitude for map center
            zoom (int): Initial zoom level
            
        Returns:
            folium.Map: Initialized map object
        """
        return folium.Map(
            location=[center_lat, center_lng],
            zoom_start=zoom,
            tiles='CartoDB positron',  # Clean, light style map
            width='100%'
        )

    def add_user_marker(self, 
                       map_obj: folium.Map, 
                       location: Tuple[float, float],
                       popup: str = "Your Location") -> folium.Map:
        """
        Add a marker for user's location
        
        Args:
            map_obj (folium.Map): Map to add marker to
            location (tuple): (latitude, longitude)
            popup (str): Text to show when marker is clicked
        """
        folium.Marker(
            location=location,
            popup=popup,
            icon=folium.Icon(color='red', icon='info-sign'),
            tooltip="You are here"
        ).add_to(map_obj)
        return map_obj

    def add_cooling_center_markers(self, 
                                 map_obj: folium.Map, 
                                 centers: List[Dict]) -> folium.Map:
        """
        Add markers for all cooling centers
        
        Args:
            map_obj (folium.Map): Map to add markers to
            centers (list): List of cooling center dictionaries
        """
        for center in centers:
            # Create popup HTML
            popup_html = self._create_center_popup(center)
            
            # Determine marker color based on open status
            color = 'green' if center.get('is_open', True) else 'gray'
            
            # Add marker to map
            folium.Marker(
                location=[center['lat'], center['lng']],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=color, icon='info-sign'),
                tooltip=center['name']
            ).add_to(map_obj)
        
        return map_obj

    def _create_center_popup(self, center: Dict) -> str:
        """Create HTML content for cooling center popup"""
        return f"""
            <div style="min-width: 200px">
                <h4>{center['name']}</h4>
                <p><b>Hours:</b> {center['hours']}</p>
                <p><b>Address:</b> {center['address']}</p>
                <p><b>Distance:</b> {center.get('distance', 'N/A')} miles</p>
                <p><b>Status:</b> {'Open' if center.get('is_open', True) else 'Closed'}</p>
            </div>
        """

    def get_route(self, 
                 origin: Tuple[float, float], 
                 destination: Tuple[float, float], 
                 mode: str = 'transit') -> Optional[Dict]:
        """
        Get route information between two points
        
        Args:
            origin (tuple): (latitude, longitude) of start point
            destination (tuple): (latitude, longitude) of end point
            mode (str): 'transit', 'walking', 'driving', or 'bicycling'
            
        Returns:
            dict: Route information or None if route not found
        """
        try:
            directions = self.gmaps.directions(
                origin=origin,
                destination=destination,
                mode=mode,
                departure_time=datetime.now()
            )
            
            if directions:
                return self._process_route(directions[0])
            return None
            
        except Exception as e:
            print(f"Error getting directions: {e}")
            return None

    def _process_route(self, route: Dict) -> Dict:
        """Process and format route information"""
        if 'legs' not in route:
            return {}
            
        leg = route['legs'][0]
        return {
            'distance': leg.get('distance', {}).get('text', 'N/A'),
            'duration': leg.get('duration', {}).get('text', 'N/A'),
            'steps': self._process_steps(leg.get('steps', [])),
            'polyline': route.get('overview_polyline', {}).get('points', '')
        }

    def _process_steps(self, steps: List[Dict]) -> List[Dict]:
        """Process and format route steps"""
        processed_steps = []
        for step in steps:
            processed_step = {
                'instruction': step.get('html_instructions', ''),
                'distance': step.get('distance', {}).get('text', ''),
                'duration': step.get('duration', {}).get('text', ''),
                'mode': step.get('travel_mode', '').lower()
            }
            
            # Add transit details if available
            if 'transit_details' in step:
                processed_step['transit_details'] = {
                    'line': step['transit_details'].get('line', {}).get('name', ''),
                    'departure_stop': step['transit_details'].get('departure_stop', {}).get('name', ''),
                    'arrival_stop': step['transit_details'].get('arrival_stop', {}).get('name', ''),
                    'departure_time': step['transit_details'].get('departure_time', {}).get('text', ''),
                    'arrival_time': step['transit_details'].get('arrival_time', {}).get('text', '')
                }
            
            processed_steps.append(processed_step)
        
        return processed_steps

    def add_route_to_map(self, 
                        map_obj: folium.Map, 
                        origin: Tuple[float, float], 
                        destination: Tuple[float, float],
                        mode: str = 'transit') -> folium.Map:
        """
        Add a route line to the map
        
        Args:
            map_obj (folium.Map): Map to add route to
            origin (tuple): (latitude, longitude) of start point
            destination (tuple): (latitude, longitude) of end point
            mode (str): Transportation mode
        """
        route = self.get_route(origin, destination, mode)
        if route and 'polyline' in route:
            # Decode Google's polyline format
            from polyline import decode
            route_coordinates = decode(route['polyline'])
            
            # Add the route line to the map
            folium.PolyLine(
                route_coordinates,
                weight=3,
                color='blue',
                opacity=0.8,
                tooltip=f"{route['duration']} ({route['distance']})"
            ).add_to(map_obj)
        
        return map_obj

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to coordinates
        
        Args:
            address (str): Address to geocode
            
        Returns:
            tuple: (latitude, longitude) or None if geocoding fails
        """
        try:
            result = self.gmaps.geocode(address)
            if result:
                location = result[0]['geometry']['location']
                return location['lat'], location['lng']
            return None
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None
        
    def calculate_distance(self,
                     origin: Tuple[float, float],
                     destination: Tuple[float, float],
                     method: str = 'google',
                     mode: str = 'driving') -> Dict:
        """
        Calculate distance between two points
        """
        try:
            # Convert coordinates to string format
            origin_str = f"{origin[0]},{origin[1]}"
            dest_str = f"{destination[0]},{destination[1]}"
            
            # Get distance matrix from Google Maps
            result = self.gmaps.distance_matrix(
                origins=[origin_str],
                destinations=[dest_str],
                mode=mode,
                units='imperial'  # Use miles
            )
            
            # Extract route information
            route = result['rows'][0]['elements'][0]
            
            if route['status'] == 'OK':
                return {
                    'status': 'OK',
                    'distance_text': route['distance']['text'],
                    'duration_text': route['duration']['text'],
                    'distance_value': route['distance']['value'],
                    'duration_value': route['duration']['value']
                }
            else:
                return {'status': 'FAILED'}
                
        except Exception as e:
            print(f"Error in calculate_distance: {e}")
            return {'status': 'ERROR'}