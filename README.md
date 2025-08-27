# 🚴 Statshunters Route Optimizer

A web-based route planner that optimizes cycling routes to discover new Statshunters tiles efficiently. Plan routes for different bike types using multiple routing services, while maximizing coverage of unvisited map tiles.

## Features

- 🗺️ **Tile Visualization**: View visited (green) and unvisited (red) tiles on an interactive map
- 🚴 **Multi-Bike Support**: Route planning for road, gravel, mountain, and e-bikes
- 🛣️ **Multiple Routing Services**: OpenRouteService for global coverage, Mapy.cz for superior mountain biking
- 🎯 **Optimization Algorithm**: Smart route generation to cover maximum unvisited tiles
- 📊 **Route Analytics**: Distance, duration, elevation gain, and tile coverage stats
- 📥 **GPX Export**: Download routes for GPS devices and cycling apps
- 📍 **Location Services**: Use current location or click on map to set start point
- 🎛️ **Service Selection**: Choose between OpenRouteService and Mapy.cz routing services

## Setup

### Prerequisites

- Python 3.7+
- Statshunters account with share link or API key
- At least one routing service API key:
  - **OpenRouteService** (global coverage, free at [openrouteservice.org](https://openrouteservice.org/dev/#/signup))
  - **Mapy.cz** (Central European routing, excellent for mountain biking, free at [developer.mapy.com](https://developer.mapy.com/))

### Installation

1. **Clone and install dependencies:**
   ```bash
   git clone <repository-url>
   cd statshunter_optimizer
   pip install -r requirements.txt
   ```

2. **Configure environment (REQUIRED):**
   ```bash
   cp .env.example .env
   ```
   **Edit `.env` file with your API keys - this is required for routing services:**
   ```
   # Routing services (at least one required for route generation)
   ORS_API_KEY=your_openrouteservice_key      # Global routing
   MAPY_API_KEY=your_mapy_cz_key              # Central European routing
   
   # Statshunters credentials (optional - can also be entered in UI)
   STATSHUNTERS_SHARE_LINK=https://www.statshunters.com/share/YOUR_CODE
   # OR
   STATSHUNTERS_API_KEY=abc123def
   ```

3. **Run the application:**
   ```bash
   # Option 1: Using the startup script
   python run_server.py
   
   # Option 2: Direct from backend
   cd backend
   python main.py
   
   # Option 3: On Windows
   run_server.bat
   ```
   
4. **Open your browser:**
   Navigate to `http://localhost:8000`

## Getting Your Credentials

### Statshunters Share Link
1. Go to [Statshunters.com](https://www.statshunters.com)
2. Login to your account
3. Go to your profile settings
4. Copy the share link (format: `https://www.statshunters.com/share/abc123`)

### OpenRouteService API Key
1. Sign up at [OpenRouteService](https://openrouteservice.org/dev/#/signup)
2. Create a new token
3. Copy the API key

### Mapy.cz API Key (Recommended for Mountain Biking)
1. Create a Seznam account at [Mapy.cz Developer Portal](https://developer.mapy.com/)
2. Log in to My Account portal
3. Create an API Project
4. Copy the automatically generated API key
5. **Free tier**: 250,000 requests/month (much higher than OpenRouteService!)

## Usage

### Basic Route Planning

1. **Configure Credentials**: Enter your Statshunters credentials in the UI (routing API keys are configured via .env file)
2. **Select Routing Service**: Choose between OpenRouteService or Mapy.cz
3. **Set Start Point**: Click on the map or use current location
4. **Configure Route**: 
   - Set target distance (km)
   - Choose bike type (available options depend on routing service)
   - Adjust max tiles and preferences
5. **Load Tiles**: Click "Load Tiles" to fetch your tile data
6. **Generate Route**: Click "Generate Route" to create optimized route
7. **Export**: Download GPX file for your GPS device

### Bike Type Profiles & Routing Services

**OpenRouteService** (Global coverage):
- **🚴‍♂️ Road Bike**: Fast paved routes, avoids highways
- **🚵‍♀️ Gravel Bike**: Mixed surfaces, quiet scenic routes
- **🏔️ Mountain Bike**: Off-road capable, allows varied terrain
- **⚡ E-Bike**: Gentle gradients, electric motor assistance

**Mapy.cz** (Central European specialist):
- **🚴‍♂️ Road Bike**: Prefers asphalt and cycle paths
- **🏔️ Mountain/Touring Bike**: Excellent for bike touring, prefers cycle paths regardless of surface

**💡 Service Selection Tips:**
- For mountain biking and touring → Mapy.cz (superior mountain bike routing)  
- For road/gravel/e-bike routing → OpenRouteService (more bike type options)
- For Central/Eastern Europe → Mapy.cz often has better local routing

### Advanced Features

- **Tile Coverage Optimization**: Algorithm prioritizes unvisited tiles within distance constraints
- **Route Visualization**: Interactive map showing route, tiles, and waypoints
- **Export Options**: GPX download and tile data export
- **Responsive Design**: Works on desktop and mobile devices

## API Endpoints

- `GET /api/routing-services` - Get available routing services and bike types
- `POST /api/tiles` - Fetch tile data for map bounds
- `POST /api/route` - Generate optimized route with service selection (uses .env API keys)
- `GET /api/download/{filename}` - Download GPX files
- `GET /api/bike-profiles` - Get bike type profiles for selected service

## Technical Architecture

### Backend (Python/FastAPI)
- **FastAPI**: Modern web framework for APIs
- **Statshunters Client**: Fetches visited/unvisited tiles  
- **Routing Services**: 
  - OpenRouteService integration for global routing
  - Mapy.cz integration for Central European routing
  - Factory pattern for service selection and fallback
- **Optimization Algorithm**: Modified TSP for tile coverage
- **GPX Generation**: Export routes for GPS devices

### Frontend (HTML/CSS/JavaScript)
- **Leaflet.js**: Interactive mapping
- **Dynamic UI**: Routing service selector with bike type adaptation
- **Responsive Design**: Works on all devices
- **Local Storage**: Saves configuration between sessions

### Libraries Used
- `mercantile`: Tile coordinate system handling
- `shapely`: Geometric operations
- `networkx`: Graph algorithms for route optimization
- `gpxpy`: GPX file generation
- `openrouteservice`: OpenRouteService API client
- `requests`: HTTP client for Mapy.cz API

## Troubleshooting

### Common Issues

1. **"Statshunters credentials not configured"**
   - Ensure share link is correctly formatted
   - Check .env file or enter credentials in UI

2. **"No tiles within target distance"** 
   - Increase target distance
   - Move start point to area with more tiles

3. **"Route generation failed"** or **"No routing services configured"**
   - Check your `.env` file has valid API keys (ORS_API_KEY or MAPY_API_KEY)
   - Restart the backend after updating .env file
   - Try different routing service if one fails
   - Ensure start point is on accessible roads

4. **Tiles not loading**
   - Verify share link is public and valid
   - Check network connectivity

### Performance Tips

- Start with smaller distances (20-50km) for testing
- Limit max tiles (10-30) for faster processing
- Use appropriate bike type and routing service for terrain
- Mapy.cz has higher rate limits (250k vs 2k daily) for heavy usage

### Security Notes

- **API Keys**: Routing API keys are configured via `.env` file only (not in UI) for security
- **Never commit**: Add `.env` to your `.gitignore` to avoid committing API keys
- **Environment separation**: Use different API keys for development and production

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Submit pull request with detailed description

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [Statshunters.com](https://www.statshunters.com) for the tile hunting platform
- [OpenRouteService](https://openrouteservice.org) for global cycling route calculation
- [Mapy.cz](https://mapy.cz) and Seznam for Central European routing services
- [OpenStreetMap](https://www.openstreetmap.org) contributors for map data