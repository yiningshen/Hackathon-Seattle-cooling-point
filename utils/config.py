import os
from dotenv import load_dotenv



class Config:
    # Load environment variables
    load_dotenv()
    
    # Get API key
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
    
    # Default Seattle coordinates
    DEFAULT_LAT = 47.6062
    DEFAULT_LNG = -122.3321
    
    # Center Types
    CENTER_TYPES = [
        'Community Center',
        'Library',
        'Event Hall'
    ]
    
    # Map Settings
    DEFAULT_ZOOM = 12
    MAX_DISTANCE = 10  # miles
    
    @classmethod
    def validate_api_key(cls):
        """Validate Google Maps API key exists"""
        if not cls.GOOGLE_MAPS_API_KEY:
            raise ValueError("""
                Google Maps API key not found!
                1. Create a .env file in project root
                2. Add: GOOGLE_MAPS_API_KEY=your_api_key_here
            """)