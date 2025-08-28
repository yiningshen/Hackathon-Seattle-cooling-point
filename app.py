import streamlit as st
from streamlit_folium import st_folium
from utils.maps import MapService
from utils.data import CoolingCenterData
from datetime import datetime
import folium
import pandas as pd


class CoolingCenterApp:
    def __init__(self):
        """Initialize app services and configuration"""
        # Initialize services
        self.map_service = MapService()
        self.data_service = CoolingCenterData()
        self.user_lat = None
        self.user_lng = None
        
        # Set page config
        st.set_page_config(
            page_title="Seattle Cool Finder",
            page_icon="🌡️",
            layout="wide"
        )
        
        # Initialize session state
        if 'user_location' not in st.session_state:
            st.session_state.user_location = None
        if 'selected_center' not in st.session_state:
            st.session_state.selected_center = None

    def render_header(self):
        """Render app header and description"""
        st.title("Seattle Cool Finder 🌡️")
        st.markdown("""
        Find your nearest cooling center in Seattle during hot weather.
        These locations provide air conditioning and a safe space to stay cool.
        """)

    def render_sidebar(self):
        """Render sidebar with filters and options"""
        with st.sidebar:
            st.header("Filter Options")
            
            # Distance filter
            max_distance = st.slider(
                "Maximum Distance (miles)",
                min_value=1,
                max_value=10,
                value=5
            )
            
            # Get unique center types from data
            all_types = sorted(self.data_service.df['type'].unique())
            
            # Type filter
            center_types = st.multiselect(
                "Center Types",
                all_types,
                default=all_types
            )
            
            # Feature filters
            show_only_open = st.checkbox("Show Only Open Centers", value=False)
            
            return max_distance, center_types, show_only_open

    def get_user_location(self):
        """Handle user location input"""
        col1, col2, col3 = st.columns([3, 1, 1])
        
        
        with col1:
            address = st.text_input(
                "Enter your address in Seattle:",
                placeholder="123 Main St, Seattle, WA"
            )
        
        with col2:
            use_current = st.button("📍 Use My Location")
            
       
        with col3:
            search_button = st.button("🔍 Search")
            
        
        if search_button:
            location = self.map_service.geocode_address(address)
            if location:
                self.user_lat, self.user_lng = location  # Set the instance variables
                st.session_state.user_location = location
                return True
        
        if use_current:
            # For demo, use downtown Seattle
            self.user_lat, self.user_lng = 47.6062, -122.3321  # Set the instance variables
            st.session_state.user_location = (47.6062, -122.3321)
            return True
            
        return False

    def display_map(self, centers_df):
        """Display map with cooling centers"""
        # Create base map
        m = self.map_service.create_base_map()
        
        # Add user location if available
        if st.session_state.user_location:
            m = self.map_service.add_user_marker(
                m,
                st.session_state.user_location
            )
        
        # Process centers data
        centers = centers_df.copy()
        centers['is_open'] = centers['hours'].apply(self.data_service._is_center_open)
        
        # Add cooling center markers with proper HTML popups
        for _, center in centers.iterrows():
            # Create popup HTML content
            hours_text = center['hours'].replace(';', '<br>')
            features = center['features']
            if isinstance(features, str):
                features = [f.strip() for f in features.split(',')]
            features_html = '<br>'.join([f"• {f.strip()}" for f in features])
            
            popup_content = f"""
    <div style='min-width: 200px'>
        <h4>{center['name']}</h4>
        <p><b>Status:</b> {'🟢 Open' if center['is_open'] else '🔴 Closed'}</p>
        <p><b>Address:</b><br>{center['address']}</p>
        <p><b>Type:</b> {center['type']}</p>
        <p><b>Hours:</b><br>{hours_text}</p>
        <p><b>Features:</b><br>{features_html}</p>
        {self._get_distance_duration_html(center)}
        {f"<p><b>Notes:</b><br>{center['notes']}</p>" if pd.notna(center.get('notes')) else ''}
    </div>
"""
    
    # Add marker with popup
            folium.Marker(
                location=[center['lat'], center['lng']],
                popup=folium.Popup(popup_content, max_width=300),
                icon=folium.Icon(
                    color='green' if center['is_open'] else 'red',
                    icon='info-sign'
                ),
                tooltip=f"{center['name']} ({'Open' if center['is_open'] else 'Closed'})"
            ).add_to(m)
        
        # Add route if center is selected
        if st.session_state.user_location and st.session_state.selected_center:
            center = centers[
                centers['name'] == st.session_state.selected_center
            ].iloc[0]
            destination = (center['lat'], center['lng'])
            m = self.map_service.add_route_to_map(
                m,
                st.session_state.user_location,
                destination
            )
        
        # Display map
        st_folium(m, width=800, height=500)

    def _get_distance_duration_html(self, center) -> str:
        """
        Generate HTML for distance and duration information
        """
        try:
            # Check if we have user location
            if self.user_lat is None or self.user_lng is None:
                return "<p><b>Distance:</b> Set your location to see distance</p>"
                
            user_location = (self.user_lat, self.user_lng)
                
            # Get center coordinates
            if 'lat' in center and 'lng' in center:
                center_location = (float(center['lat']), float(center['lng']))
            elif 'latitude' in center and 'longitude' in center:
                center_location = (float(center['latitude']), float(center['longitude']))
            else:
                return "<p><b>Distance:</b> Coordinates not available</p>"
                
            # Calculate distance and duration
            result = self.map_service.calculate_distance(
                origin=user_location,
                destination=center_location,
                method='google',
                mode='driving'
            )
                
            if result and result.get('status') == 'OK':
                return f"""
                    <p><b>Distance:</b> {result['distance_text']}</p>
                    <p><b>Est. Travel Time:</b> {result['duration_text']}</p>
                """
            else:
                return "<p><b>Distance:</b> Not available</p>"
                    
        except Exception as e:
            print(f"Error calculating distance: {e}")
            return "<p><b>Distance:</b> Not available</p>"

    def display_center_list(self, centers_df):
        """Display list of cooling centers"""
        st.subheader("Nearby Cooling Centers")
        
        if centers_df.empty:
            st.warning("No cooling centers found within the selected criteria.")
            return
        
        for _, center in centers_df.iterrows():
            # Determine if center is open
            is_open = self.data_service._is_center_open(center['hours'])
            status = "🟢 Open" if is_open else "🔴 Closed"
            
            with st.expander(
                f"🏢 {center['name']} ({center['distance']:.1f} mi) - {status}"
            ):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"📍 **Address:** {center['address']}")
                    st.write(f"⏰ **Hours:** {center['hours']}")
                    st.write(f"🏷️ **Type:** {center['type']}")
                    st.write("✨ **Features:**")
                    features = center['features']
                    if isinstance(features, str):
                        features = eval(features)
                    for feature in features:
                        st.write(f"  • {feature}")
                    if pd.notna(center.get('notes')):
                        st.write(f"📝 **Notes:** {center['notes']}")
                
                with col2:
                    if st.button("Get Directions", key=center['name']):
                        st.session_state.selected_center = center['name']

    def run(self):
        """Main app execution"""
        self.render_header()
        
        # Get filters from sidebar
        max_distance, center_types, show_only_open = self.render_sidebar()
        
        # Get user location
        has_location = self.get_user_location()
        
        if has_location:
            # Get filtered centers
            centers = self.data_service.get_nearest_centers(
                st.session_state.user_location[0],
                st.session_state.user_location[1],
                max_distance=max_distance,
                show_only_open=show_only_open
            )
            
            # Apply filters
            if center_types:
                centers = centers[centers['type'].isin(center_types)]
                
            
            # Display results
            if not centers.empty:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    self.display_map(centers)
                
                with col2:
                    self.display_center_list(centers)
            else:
                st.warning(
                    "No cooling centers found matching your criteria. " +
                    "Try increasing the distance or adjusting filters."
                )
        else:
            st.info("👆 Enter your address to find nearby cooling centers.")
            
            # Show all centers with filters applied
            all_centers = self.data_service.get_all_centers()
            
    
            # Apply filters to initial view
            if show_only_open:
                all_centers = all_centers[
                    all_centers['hours'].apply(self.data_service._is_center_open)
                ]
            if center_types:
                all_centers = all_centers[all_centers['type'].isin(center_types)]
            
            self.display_map(all_centers)

def main():
    try:
        app = CoolingCenterApp()
        app.run()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        if st.checkbox("Show error details"):
            st.exception(e)
    
if __name__ == "__main__":
    main()