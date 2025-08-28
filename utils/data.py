from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from geopy.distance import geodesic

class CoolingCenterData:
    # Define cooling centers data
    COOLING_CENTERS = [
        {
            'name': 'Rainier Beach Community Center',
            'address': '8825 Rainier Ave S, Seattle, WA 98118',
            'type': 'Community Center',
            'coordinates': (47.5223, -122.2666),
            'hours': '9:00AM-9:00PM',
            'has_ac': True,
            'features': ['Air Conditioning', 'Water Fountain', 'Restrooms'],
            'notes': 'Regular business hours'
        },
        {
            'name': 'International District/Chinatown Community Center',
            'address': '719 8th Ave S, Seattle, WA 98104',
            'type': 'Community Center',
            'coordinates': (47.5964, -122.3203),
            'hours': '9:00AM-9:00PM',
            'has_ac': True,
            'features': ['Air Conditioning', 'Water Fountain', 'Restrooms'],
            'notes': 'Regular business hours'
        },
        {
            'name': 'Northgate Community Center',
            'address': '10510 5th Ave NE, Seattle, WA 98125',
            'type': 'Community Center',
            'coordinates': (47.7052, -122.3438),
            'hours': '9:00AM-9:00PM',
            'has_ac': True,
            'features': ['Air Conditioning', 'Water Fountain', 'Restrooms'],
            'notes': 'Regular business hours'
        },
        {
            'name': 'Magnuson Community Center',
            'address': '7110 62nd Avenue NE, Seattle, WA 98115',
            'type': 'Community Center',
            'coordinates': (47.6814, -122.2752),
            'hours': '9:00AM-9:00PM',
            'has_ac': True,
            'features': ['Air Conditioning', 'Water Fountain', 'Restrooms'],
            'notes': 'Regular business hours'
        },
        {
            'name': 'Seattle Center Armory',
            'address': 'Food & Event Hall, Seattle Center',
            'type': 'Event Hall',
            'coordinates': (47.6219, -122.3517),
            'hours': '7:00AM-9:00PM',
            'has_ac': True,
            'features': ['Air Conditioning', 'Food Court', 'Restrooms'],
            'notes': 'Summer operation hours'
        },
        {
            'name': 'Central Library',
            'address': '1000 4th Ave, Seattle, WA 98104',
            'type': 'Library',
            'coordinates': (47.6067, -122.3325),
            'hours': '10:00AM-8:00PM',
            'has_ac': True,
            'features': ['Air Conditioning', 'Water Fountain', 'Restrooms', 'Seating'],
            'notes': 'Hours may vary. Check www.spl.org/Today for updates'
        }
    ]

    def __init__(self):
        """Initialize the CoolingCenterData class"""
        self.df = pd.DataFrame(self.COOLING_CENTERS)
        # Split coordinates into lat and lng
        self.df[['lat', 'lng']] = pd.DataFrame(
            self.df['coordinates'].tolist(), 
            index=self.df.index
        )

    def get_all_centers(self) -> pd.DataFrame:
        """Get all cooling centers"""
        return self.df

    def get_open_centers(self) -> pd.DataFrame:
        """Get only currently open centers"""
        return self.df[self.df.apply(lambda x: self._is_center_open(x['hours']), axis=1)]

    def get_nearest_centers(self, 
                          lat: float, 
                          lng: float, 
                          max_distance: float = 5.0,
                          limit: int = None) -> pd.DataFrame:
        """
        Get nearest cooling centers within specified distance
        
        Args:
            lat (float): User latitude
            lng (float): User longitude
            max_distance (float): Maximum distance in miles
            limit (int): Maximum number of results to return
            
        Returns:
            DataFrame: Filtered and sorted cooling centers
        """
        # Calculate distances
        centers = self.df.copy()
        centers['distance'] = centers.apply(
            lambda row: self._calculate_distance(
                lat, lng, row['coordinates'][0], row['coordinates'][1]
            ),
            axis=1
        )
        
        # Filter by distance
        centers = centers[centers['distance'] <= max_distance]
        
        # Sort by distance
        centers = centers.sort_values('distance')
        
        # Add open/closed status
        centers['is_open'] = centers['hours'].apply(self._is_center_open)
        
        # Limit results if specified
        if limit:
            centers = centers.head(limit)
            
        return centers

    def get_centers_by_type(self, center_type: str) -> pd.DataFrame:
        """Get centers of a specific type"""
        return self.df[self.df['type'] == center_type]

    def get_center_by_name(self, name: str) -> Optional[Dict]:
        """Get specific center by name"""
        center = self.df[self.df['name'] == name]
        if not center.empty:
            return center.iloc[0].to_dict()
        return None

    def _calculate_distance(self, 
                          lat1: float, 
                          lng1: float, 
                          lat2: float, 
                          lng2: float) -> float:
        """Calculate distance between two points in miles"""
        return geodesic((lat1, lng1), (lat2, lng2)).miles

    def _is_center_open(self, hours: str) -> bool:
        """
        Check if a center is currently open based on hours string
        Format expected: '9:00AM-9:00PM' or similar
        """
        try:
            now = datetime.now()
            open_time, close_time = hours.split('-')
            
            # Convert to 24-hour format
            def convert_to_24hr(time_str):
                time_str = time_str.strip()
                time = datetime.strptime(time_str, '%I:%M%p')
                return time.hour * 60 + time.minute
            
            open_minutes = convert_to_24hr(open_time)
            close_minutes = convert_to_24hr(close_time)
            current_minutes = now.hour * 60 + now.minute
            
            return open_minutes <= current_minutes <= close_minutes
        except Exception as e:
            print(f"Error checking hours {hours}: {e}")
            return False

    def get_centers_with_feature(self, feature: str) -> pd.DataFrame:
        """Get centers that have a specific feature"""
        return self.df[self.df['features'].apply(lambda x: feature in x)]

    def to_dict(self) -> List[Dict]:
        """Convert centers to list of dictionaries"""
        return self.df.to_dict('records')

    def to_geojson(self) -> Dict:
        """Convert centers to GeoJSON format"""
        features = []
        for _, row in self.df.iterrows():
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [row['coordinates'][1], row['coordinates'][0]]
                },
                'properties': {
                    'name': row['name'],
                    'address': row['address'],
                    'type': row['type'],
                    'hours': row['hours'],
                    'has_ac': row['has_ac'],
                    'features': row['features'],
                    'notes': row['notes']
                }
            }
            features.append(feature)
            
        return {
            'type': 'FeatureCollection',
            'features': features
        }