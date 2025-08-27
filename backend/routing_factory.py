from typing import Optional, Union, Dict, List
import logging
import os
from enum import Enum

from routing import RouteService
from mapy_routing import MapyRouteService

logger = logging.getLogger(__name__)

class RoutingServiceType(Enum):
    OPENROUTE = "openroute"
    MAPY = "mapy"

class RoutingServiceFactory:
    """Factory for creating and managing routing services."""
    
    # Available bike types per service
    SERVICE_BIKE_TYPES = {
        RoutingServiceType.OPENROUTE: {
            'road': '🚴‍♂️ Road Bike',
            'gravel': '🚵‍♀️ Gravel Bike', 
            'mountain': '🏔️ Mountain Bike',
            'ebike': '⚡ E-Bike'
        },
        RoutingServiceType.MAPY: {
            'road': '🚴‍♂️ Road Bike',
            'mountain': '🏔️ Mountain/Touring Bike'
        }
    }
    
    # Default service preferences by bike type
    DEFAULT_SERVICE_PREFERENCE = {
        'road': RoutingServiceType.OPENROUTE,
        'gravel': RoutingServiceType.OPENROUTE,
        'mountain': RoutingServiceType.MAPY,  # Mapy.cz is better for mountain/touring
        'ebike': RoutingServiceType.OPENROUTE
    }
    
    def __init__(self):
        self._openroute_service: Optional[RouteService] = None
        self._mapy_service: Optional[MapyRouteService] = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize available routing services based on API keys."""
        # Initialize OpenRouteService if API key is available
        ors_key = os.getenv("ORS_API_KEY")
        if ors_key:
            try:
                self._openroute_service = RouteService(ors_key)
                logger.info("OpenRouteService initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenRouteService: {e}")
        else:
            logger.warning("ORS_API_KEY not found. OpenRouteService will be unavailable.")
        
        # Initialize Mapy.cz if API key is available  
        mapy_key = os.getenv("MAPY_API_KEY")
        if mapy_key:
            try:
                self._mapy_service = MapyRouteService(mapy_key)
                logger.info("Mapy.cz routing service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Mapy.cz service: {e}")
        else:
            logger.warning("MAPY_API_KEY not found. Mapy.cz routing will be unavailable.")
    
    def get_available_services(self) -> List[Dict]:
        """
        Get list of available routing services.
        
        Returns:
            List of available services with metadata
        """
        services = []
        
        if self._openroute_service:
            services.append({
                'id': 'openroute',
                'name': 'OpenRouteService',
                'description': 'Global routing with multiple bike profiles',
                'bike_types': self.SERVICE_BIKE_TYPES[RoutingServiceType.OPENROUTE],
                'strengths': ['Global coverage', 'Multiple bike types', 'Advanced avoid options']
            })
        
        if self._mapy_service:
            services.append({
                'id': 'mapy',
                'name': 'Mapy.cz',
                'description': 'Central European routing optimized for bike touring',
                'bike_types': self.SERVICE_BIKE_TYPES[RoutingServiceType.MAPY],
                'strengths': ['Excellent for bike touring', 'Superior mountain bike routing', 'High rate limits']
            })
        
        return services
    
    def get_bike_types_for_service(self, service_type: str) -> Dict[str, str]:
        """
        Get available bike types for a specific service.
        
        Args:
            service_type: Service type ('openroute' or 'mapy')
            
        Returns:
            Dictionary of bike type key -> display name
        """
        service_enum = RoutingServiceType(service_type)
        return self.SERVICE_BIKE_TYPES.get(service_enum, {})
    
    def get_recommended_service(self, bike_type: str) -> Optional[str]:
        """
        Get recommended service for a bike type.
        
        Args:
            bike_type: Type of bike
            
        Returns:
            Recommended service ID or None
        """
        service_enum = self.DEFAULT_SERVICE_PREFERENCE.get(bike_type)
        if service_enum:
            service_id = service_enum.value
            # Check if recommended service is actually available
            available_services = [s['id'] for s in self.get_available_services()]
            if service_id in available_services:
                return service_id
        
        # Fallback to any available service
        available_services = self.get_available_services()
        if available_services:
            return available_services[0]['id']
        
        return None
    
    def create_service(self, service_type: Optional[str] = None, bike_type: str = 'mountain') -> Union[RouteService, MapyRouteService]:
        """
        Create a routing service instance.
        
        Args:
            service_type: Preferred service type ('openroute' or 'mapy')
            bike_type: Type of bike for default service selection
            
        Returns:
            Routing service instance
            
        Raises:
            ValueError: If no suitable service is available
        """
        # If no service type specified, use recommendation
        if not service_type:
            service_type = self.get_recommended_service(bike_type)
            if service_type:
                logger.info(f"Auto-selected {service_type} service for {bike_type} bike")
        
        # Try to create requested service
        if service_type == 'openroute' and self._openroute_service:
            return self._openroute_service
        elif service_type == 'mapy' and self._mapy_service:
            return self._mapy_service
        
        # Fallback to any available service
        if self._mapy_service and bike_type == 'mountain':
            logger.info(f"Falling back to Mapy.cz for {bike_type} bike (recommended)")
            return self._mapy_service
        elif self._openroute_service:
            logger.info(f"Falling back to OpenRouteService for {bike_type} bike")
            return self._openroute_service
        elif self._mapy_service:
            logger.info(f"Falling back to Mapy.cz for {bike_type} bike (only option)")
            return self._mapy_service
        
        # No services available
        available_services = self.get_available_services()
        if not available_services:
            raise ValueError(
                "No routing services are available. Please configure at least one of: "
                "ORS_API_KEY (OpenRouteService) or MAPY_API_KEY (Mapy.cz)"
            )
        
        raise ValueError(f"Requested service '{service_type}' is not available")
    
    def validate_service_bike_combination(self, service_type: str, bike_type: str) -> bool:
        """
        Validate if a service supports a specific bike type.
        
        Args:
            service_type: Service type ('openroute' or 'mapy')
            bike_type: Type of bike
            
        Returns:
            True if combination is valid
        """
        try:
            service_enum = RoutingServiceType(service_type)
            available_types = self.SERVICE_BIKE_TYPES.get(service_enum, {})
            return bike_type in available_types
        except ValueError:
            return False
    
    def get_service_info(self, service_type: str) -> Optional[Dict]:
        """
        Get information about a specific service.
        
        Args:
            service_type: Service type ('openroute' or 'mapy')
            
        Returns:
            Service information or None if not available
        """
        available_services = self.get_available_services()
        for service in available_services:
            if service['id'] == service_type:
                return service
        return None