// Global variables
let map;
let tilesLayer;
let routeLayer;
let startMarker;
let currentTileData = null;
let currentRoute = null;

// Global variables
let bikeProfiles = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    bindEventListeners();
    loadFromLocalStorage();
    loadBikeProfiles();
});

// Initialize Leaflet map
function initializeMap() {
    map = L.map('map').setView([52.520008, 13.404954], 10);
    
    // Add base map layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
    
    // Add tile legend
    addTileLegend();
    
    // Handle map clicks for setting start point
    map.on('click', function(e) {
        setStartPoint(e.latlng.lat, e.latlng.lng);
    });
}

// Add tile legend to map
function addTileLegend() {
    const legend = document.createElement('div');
    legend.className = 'tile-legend';
    legend.innerHTML = `
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(34, 139, 34, 0.6);"></div>
            <span>Visited Tiles</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(255, 99, 71, 0.6);"></div>
            <span>Unvisited Tiles</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(30, 144, 255, 1); height: 3px;"></div>
            <span>Generated Route</span>
        </div>
    `;
    
    document.getElementById('map-container').appendChild(legend);
}

// Bind event listeners
function bindEventListeners() {
    // Main action buttons
    document.getElementById('load-tiles-btn').addEventListener('click', loadTiles);
    document.getElementById('generate-route-btn').addEventListener('click', generateRoute);
    document.getElementById('use-current-location-btn').addEventListener('click', getCurrentLocation);
    
    // Map controls
    document.getElementById('toggle-tiles-btn').addEventListener('click', toggleTiles);
    document.getElementById('clear-route-btn').addEventListener('click', clearRoute);
    
    // Results actions
    document.getElementById('download-gpx-btn').addEventListener('click', downloadGPX);
    document.getElementById('export-tiles-btn').addEventListener('click', exportTileData);
    
    // Auto-save form data
    const inputs = document.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('change', saveToLocalStorage);
    });
    
    // Update bike type description when selection changes
    document.getElementById('bike-type').addEventListener('change', updateBikeTypeDescription);
}

// Load configuration from localStorage
function loadFromLocalStorage() {
    const saved = localStorage.getItem('statshunters-config');
    if (saved) {
        try {
            const config = JSON.parse(saved);
            Object.keys(config).forEach(key => {
                const element = document.getElementById(key);
                if (element) {
                    if (element.type === 'checkbox') {
                        element.checked = config[key];
                    } else {
                        element.value = config[key];
                    }
                }
            });
        } catch (e) {
            console.error('Error loading config:', e);
        }
    }
}

// Save configuration to localStorage
function saveToLocalStorage() {
    const config = {};
    const inputs = document.querySelectorAll('input, select');
    inputs.forEach(input => {
        if (input.type === 'checkbox') {
            config[input.id] = input.checked;
        } else {
            config[input.id] = input.value;
        }
    });
    localStorage.setItem('statshunters-config', JSON.stringify(config));
}

// Load bike profiles from API
async function loadBikeProfiles() {
    try {
        const response = await fetch('/api/bike-profiles');
        if (response.ok) {
            const data = await response.json();
            bikeProfiles = data.profiles;
            updateBikeTypeDescription(); // Update description with loaded data
        }
    } catch (error) {
        console.warn('Could not load bike profiles:', error);
    }
}

// Update bike type description
function updateBikeTypeDescription() {
    const bikeType = document.getElementById('bike-type').value;
    const descriptionElement = document.getElementById('bike-type-description');
    
    if (bikeProfiles && bikeProfiles[bikeType]) {
        const profile = bikeProfiles[bikeType];
        let description = profile.description;
        
        if (profile.avoids && profile.avoids.length > 0) {
            description += ` • Avoids: ${profile.avoids.join(', ')}`;
        }
        
        if (profile.prefers_green_routes) {
            description += ` • Prefers cycling paths and quiet routes`;
        }
        
        descriptionElement.textContent = description;
        descriptionElement.style.color = '#495057';
    } else {
        descriptionElement.textContent = 'Loading route preferences...';
        descriptionElement.style.color = '#6c757d';
    }
}

// Set start point on map and in form
function setStartPoint(lat, lon) {
    document.getElementById('start-lat').value = lat.toFixed(6);
    document.getElementById('start-lon').value = lon.toFixed(6);
    
    // Remove existing marker
    if (startMarker) {
        map.removeLayer(startMarker);
    }
    
    // Add new marker
    startMarker = L.marker([lat, lon], {
        icon: L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        })
    }).addTo(map);
    
    startMarker.bindPopup('Start Point').openPopup();
    saveToLocalStorage();
}

// Get current location
function getCurrentLocation() {
    if (navigator.geolocation) {
        showLoading(true);
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                setStartPoint(lat, lon);
                map.setView([lat, lon], 12);
                showLoading(false);
                showStatus('Current location set as start point', 'success');
            },
            function(error) {
                showLoading(false);
                showStatus('Error getting location: ' + error.message, 'error');
            }
        );
    } else {
        showStatus('Geolocation is not supported by this browser', 'error');
    }
}

// Load tiles from Statshunters
async function loadTiles() {
    const shareLink = document.getElementById('share-link').value;
    const apiKey = document.getElementById('api-key').value;
    
    if (!shareLink && !apiKey) {
        showStatus('Please provide either a Statshunters share link or API key', 'error');
        return;
    }
    
    const bounds = map.getBounds();
    const requestData = {
        west: bounds.getWest(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        north: bounds.getNorth()
    };
    
    if (shareLink) requestData.share_link = shareLink;
    if (apiKey) requestData.api_key = apiKey;
    
    try {
        showLoading(true);
        const response = await fetch('/api/tiles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load tiles');
        }
        
        const data = await response.json();
        currentTileData = data;
        
        displayTiles(data);
        showStatus(`Loaded ${data.stats.total_tiles} tiles (${data.stats.unvisited_tiles} unvisited)`, 'success');
        
    } catch (error) {
        showStatus('Error loading tiles: ' + error.message, 'error');
        console.error('Tile loading error:', error);
    } finally {
        showLoading(false);
    }
}

// Display tiles on map
function displayTiles(tileData) {
    // Remove existing tiles
    if (tilesLayer) {
        map.removeLayer(tilesLayer);
    }
    
    tilesLayer = L.layerGroup();
    
    // Add visited tiles (green)
    if (tileData.visited && tileData.visited.features) {
        tileData.visited.features.forEach(feature => {
            const coords = feature.geometry.coordinates[0];
            const bounds = coords.map(coord => [coord[1], coord[0]]); // Convert lon,lat to lat,lon
            
            L.polygon(bounds, {
                color: '#228B22',
                fillColor: '#228B22',
                fillOpacity: 0.6,
                weight: 1
            }).bindTooltip('Visited Tile').addTo(tilesLayer);
        });
    }
    
    // Add unvisited tiles (red)
    if (tileData.unvisited && tileData.unvisited.features) {
        tileData.unvisited.features.forEach(feature => {
            const coords = feature.geometry.coordinates[0];
            const bounds = coords.map(coord => [coord[1], coord[0]]);
            
            L.polygon(bounds, {
                color: '#FF6347',
                fillColor: '#FF6347',
                fillOpacity: 0.6,
                weight: 1
            }).bindTooltip('Unvisited Tile').addTo(tilesLayer);
        });
    }
    
    tilesLayer.addTo(map);
}

// Generate optimized route
async function generateRoute() {
    const startLat = parseFloat(document.getElementById('start-lat').value);
    const startLon = parseFloat(document.getElementById('start-lon').value);
    const targetDistance = parseFloat(document.getElementById('distance').value);
    const bikeType = document.getElementById('bike-type').value;
    const maxTiles = parseInt(document.getElementById('max-tiles').value);
    const preferUnvisited = document.getElementById('prefer-unvisited').checked;
    const shareLink = document.getElementById('share-link').value;
    const apiKey = document.getElementById('api-key').value;
    
    // Validation
    if (!startLat || !startLon) {
        showStatus('Please set a start point by clicking on the map', 'error');
        return;
    }
    
    if (!targetDistance || targetDistance < 1) {
        showStatus('Please enter a valid target distance', 'error');
        return;
    }
    
    if (!shareLink && !apiKey) {
        showStatus('Please provide Statshunters credentials', 'error');
        return;
    }
    
    const requestData = {
        start_lat: startLat,
        start_lon: startLon,
        target_distance: targetDistance,
        bike_type: bikeType,
        max_tiles: maxTiles,
        prefer_unvisited: preferUnvisited
    };
    
    if (shareLink) requestData.share_link = shareLink;
    if (apiKey) requestData.api_key = apiKey;
    
    try {
        showLoading(true);
        const response = await fetch('/api/route', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate route');
        }
        
        const routeData = await response.json();
        currentRoute = routeData;
        
        displayRoute(routeData);
        showRouteResults(routeData);
        showStatus('Route generated successfully!', 'success');
        
    } catch (error) {
        showStatus('Error generating route: ' + error.message, 'error');
        console.error('Route generation error:', error);
    } finally {
        showLoading(false);
    }
}

// Display route on map
function displayRoute(routeData) {
    // Remove existing route
    if (routeLayer) {
        map.removeLayer(routeLayer);
    }
    
    if (routeData.route_geojson && routeData.route_geojson.coordinates) {
        const coords = routeData.route_geojson.coordinates.map(coord => [coord[1], coord[0]]);
        
        routeLayer = L.polyline(coords, {
            color: '#1E90FF',
            weight: 4,
            opacity: 0.8
        }).addTo(map);
        
        // Fit map to route bounds
        map.fitBounds(routeLayer.getBounds());
        
        // Add waypoint markers
        const waypoints = [coords[0], coords[coords.length - 1]];
        waypoints.forEach((waypoint, index) => {
            const markerColor = index === 0 ? 'green' : 'red';
            const label = index === 0 ? 'Start' : 'Finish';
            
            L.marker(waypoint, {
                icon: L.icon({
                    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-${markerColor}.png`,
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                })
            }).bindPopup(label).addTo(map);
        });
    }
}

// Show route results
function showRouteResults(routeData) {
    const resultsPanel = document.getElementById('results-panel');
    const statsGrid = document.getElementById('route-stats');
    
    const bikeTypeEmojis = {
        road: '🚴‍♂️',
        gravel: '🚵‍♀️',
        mountain: '🏔️',
        ebike: '⚡'
    };
    
    const bikeType = document.getElementById('bike-type').value;
    
    statsGrid.innerHTML = `
        <div class="stat-item">
            <span class="stat-value">${routeData.distance.toFixed(1)} km</span>
            <div class="stat-label">Distance</div>
        </div>
        <div class="stat-item">
            <span class="stat-value">${routeData.duration.toFixed(1)} h</span>
            <div class="stat-label">Duration</div>
        </div>
        <div class="stat-item">
            <span class="stat-value">${routeData.elevation_gain.toFixed(0)} m</span>
            <div class="stat-label">Elevation Gain</div>
        </div>
        <div class="stat-item">
            <span class="stat-value">${routeData.tiles_covered}</span>
            <div class="stat-label">Total Tiles</div>
        </div>
        <div class="stat-item">
            <span class="stat-value">${routeData.new_tiles}</span>
            <div class="stat-label">New Tiles</div>
        </div>
        <div class="stat-item">
            <span class="stat-value">${bikeTypeEmojis[bikeType] || '🚴'}</span>
            <div class="stat-label">Bike Type</div>
        </div>
    `;
    
    resultsPanel.style.display = 'block';
}

// Toggle tile visibility
function toggleTiles() {
    if (tilesLayer) {
        if (map.hasLayer(tilesLayer)) {
            map.removeLayer(tilesLayer);
            document.getElementById('toggle-tiles-btn').textContent = '👁️ Show Tiles';
        } else {
            map.addLayer(tilesLayer);
            document.getElementById('toggle-tiles-btn').textContent = '🙈 Hide Tiles';
        }
    }
}

// Clear route from map
function clearRoute() {
    if (routeLayer) {
        map.removeLayer(routeLayer);
        routeLayer = null;
    }
    document.getElementById('results-panel').style.display = 'none';
    currentRoute = null;
}

// Download GPX file
function downloadGPX() {
    if (currentRoute && currentRoute.gpx_download_url) {
        window.open(currentRoute.gpx_download_url, '_blank');
    } else {
        showStatus('No route available to download', 'error');
    }
}

// Export tile data
function exportTileData() {
    if (!currentTileData) {
        showStatus('No tile data available to export', 'error');
        return;
    }
    
    const data = JSON.stringify(currentTileData, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = 'statshunters_tiles.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showStatus('Tile data exported successfully', 'success');
}

// Show loading spinner
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'flex' : 'none';
}

// Show status message
function showStatus(message, type = 'info') {
    const statusContainer = document.getElementById('status');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `status-message ${type}`;
    messageDiv.textContent = message;
    
    statusContainer.appendChild(messageDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (statusContainer.contains(messageDiv)) {
            statusContainer.removeChild(messageDiv);
        }
    }, 5000);
    
    // Allow manual removal
    messageDiv.addEventListener('click', () => {
        if (statusContainer.contains(messageDiv)) {
            statusContainer.removeChild(messageDiv);
        }
    });
}