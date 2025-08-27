# 🚴 Statshunters Route Optimizer

A web-based route planner that optimizes cycling routes to discover new Statshunters tiles efficiently. Plan routes for different bike types (road, gravel, mountain) while maximizing coverage of unvisited map tiles.

## Features

- 🗺️ **Tile Visualization**: View visited (green) and unvisited (red) tiles on an interactive map
- 🚴 **Multi-Bike Support**: Route planning for road, gravel, mountain, and e-bikes
- 🎯 **Optimization Algorithm**: Smart route generation to cover maximum unvisited tiles
- 📊 **Route Analytics**: Distance, duration, elevation gain, and tile coverage stats
- 📥 **GPX Export**: Download routes for GPS devices and cycling apps
- 📍 **Location Services**: Use current location or click on map to set start point

## Setup

### Prerequisites

- Python 3.7+
- Statshunters account with share link or API key
- OpenRouteService API key (free at [openrouteservice.org](https://openrouteservice.org/dev/#/signup))

### Installation

1. **Clone and install dependencies:**
   ```bash
   git clone <repository-url>
   cd statshunter_optimizer
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` file with your credentials:
   ```
   # Option 1: Use Statshunters share link
   STATSHUNTERS_SHARE_LINK=https://www.statshunters.com/share/YOUR_CODE
   
   # Option 2: Use API key (if available)
   STATSHUNTERS_API_KEY=your_api_key
   
   # Required: OpenRouteService API key
   ORS_API_KEY=your_ors_api_key
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

## Usage

### Basic Route Planning

1. **Configure Credentials**: Enter your Statshunters share link and ORS API key
2. **Set Start Point**: Click on the map or use current location
3. **Configure Route**: 
   - Set target distance (km)
   - Choose bike type (road/gravel/mountain/e-bike)
   - Adjust max tiles and preferences
4. **Load Tiles**: Click "Load Tiles" to fetch your tile data
5. **Generate Route**: Click "Generate Route" to create optimized route
6. **Export**: Download GPX file for your GPS device

### Bike Type Profiles

- **🚴‍♂️ Road Bike**: Optimized for paved roads, faster speeds
- **🚵‍♀️ Gravel Bike**: Balanced for mixed surfaces, moderate speeds
- **🏔️ Mountain Bike**: Designed for off-road trails and rough terrain  
- **⚡ E-Bike**: Electric bike optimized routing

### Advanced Features

- **Tile Coverage Optimization**: Algorithm prioritizes unvisited tiles within distance constraints
- **Route Visualization**: Interactive map showing route, tiles, and waypoints
- **Export Options**: GPX download and tile data export
- **Responsive Design**: Works on desktop and mobile devices

## API Endpoints

- `POST /api/tiles` - Fetch tile data for map bounds
- `POST /api/route` - Generate optimized route
- `GET /api/download/{filename}` - Download GPX files
- `GET /api/health` - Service health check

## Technical Architecture

### Backend (Python/FastAPI)
- **FastAPI**: Modern web framework for APIs
- **Statshunters Client**: Fetches visited/unvisited tiles
- **OpenRouteService Integration**: Cycling-specific routing
- **Optimization Algorithm**: Modified TSP for tile coverage
- **GPX Generation**: Export routes for GPS devices

### Frontend (HTML/CSS/JavaScript)
- **Leaflet.js**: Interactive mapping
- **Responsive Design**: Works on all devices
- **Local Storage**: Saves configuration between sessions

### Libraries Used
- `mercantile`: Tile coordinate system handling
- `shapely`: Geometric operations
- `networkx`: Graph algorithms for route optimization
- `gpxpy`: GPX file generation
- `openrouteservice`: Route calculation

## Troubleshooting

### Common Issues

1. **"Statshunters credentials not configured"**
   - Ensure share link is correctly formatted
   - Check .env file or enter credentials in UI

2. **"No tiles within target distance"** 
   - Increase target distance
   - Move start point to area with more tiles

3. **"Route generation failed"**
   - Check OpenRouteService API key
   - Ensure start point is on accessible roads

4. **Tiles not loading**
   - Verify share link is public and valid
   - Check network connectivity

### Performance Tips

- Start with smaller distances (20-50km) for testing
- Limit max tiles (10-30) for faster processing
- Use appropriate bike type for terrain

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Submit pull request with detailed description

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [Statshunters.com](https://www.statshunters.com) for the tile hunting platform
- [OpenRouteService](https://openrouteservice.org) for cycling route calculation
- [OpenStreetMap](https://www.openstreetmap.org) contributors for map data