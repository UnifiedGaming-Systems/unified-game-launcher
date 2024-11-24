# Unified Game Launcher

A cross-platform game library manager that unifies your gaming experience across multiple platforms including Steam, Epic Games, PlayStation, Xbox, and GOG.

## Features
- Single unified game library interface
- Cross-platform installation management
- Console remote play integration
- Smart storage management for multi-platform games
- Unified game launcher

## Setup
1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`

## Configuration
Create a `.env` file in the root directory with your API keys:
```
STEAM_API_KEY=your_steam_api_key
EPIC_CLIENT_ID=your_epic_client_id
EPIC_CLIENT_SECRET=your_epic_client_secret
XBOX_CLIENT_ID=your_xbox_client_id
PS_CLIENT_ID=your_playstation_client_id
```

## Development
- Main application entry point is `src/main.py`
- Run tests with `python -m pytest tests/`

## Contributing
1. Fork the repository
2. Create a new branch for your feature
3. Submit a pull request