"""
Data Manager - Handles API requests, Caching, and Mock data
============================================================
Fetches match data from API-Football with intelligent caching to save API/credits.
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

# API Configuration
API_FOOTBALL_HOST = "api-football-v1.p.rapidapi.com"
API_FOOTBALL_BASE = f"https://{API_FOOTBALL_HOST}/v3"
EPL_LEAGUE_ID = 39  # English Premier League
CURRENT_SEASON = 2025 # Default if auto-detect fails

CACHE_FILE = 'fixtures_cache.json'
CACHE_DURATION = 3600  # 1 hour in seconds


def get_headers() -> Dict[str, str]:
    """Get API headers with RapidAPI key."""
    api_key = os.getenv("RAPIDAPI_KEY", "")
    if not api_key:
        logger.warning("RAPIDAPI_KEY not set in environment!")
    return {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": API_FOOTBALL_HOST
    }


def is_mock_mode() -> bool:
    """Check if we should use mock data."""
    return os.getenv("USE_MOCK_DATA", "false").lower() == "true"


def get_current_season() -> int:
    """Auto-detect current football season."""
    now = datetime.now()
    if now.month >= 8:  # August onwards
        return now.year
    else:  # Jan-July
        return now.year - 1


# =============================================================================
# CACHING SYSTEM
# =============================================================================

def load_cache() -> Dict[str, Any]:
    """Load cached data from file."""
    if not os.path.exists(CACHE_FILE):
        return {}
    
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load cache: {e}")
        return {}


def save_cache(data: Dict[str, Any]) -> None:
    """Save data to cache file."""
    try:
        current_cache = load_cache()
        current_cache.update(data)
        
        with open(CACHE_FILE, 'w') as f:
            json.dump(current_cache, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save cache: {e}")


def get_cached_fixtures(league_id: int) -> Optional[List[Dict]]:
    """Get fixtures from cache if they are fresh."""
    cache = load_cache()
    key = f"fixtures_{league_id}"
    
    if key in cache:
        entry = cache[key]
        timestamp = entry.get('timestamp', 0)
        
        # Check if cache is still valid (less than 60 mins old)
        if time.time() - timestamp < CACHE_DURATION:
            logger.info(f"✅ Using CACHED fixtures for League {league_id}")
            return entry.get('data', [])
        else:
            logger.info(f"⚠️ Cache expired for League {league_id}")
    
    return None


def update_fixture_cache(league_id: int, fixtures: List[Dict]) -> None:
    """Update cache with new fixtures."""
    cache_entry = {
        f"fixtures_{league_id}": {
            'timestamp': time.time(),
            'data': fixtures
        }
    }
    save_cache(cache_entry)


# =============================================================================
# MOCK DATA (Fallback)
# =============================================================================

def get_mock_fixtures(league_id: int):
    """Generate fake fixtures for testing when API is down."""
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # EPL Mock
    if league_id == 39:
        return [
            {'fixture_id': 101, 'date': today, 'time': '12:30', 'home_team': 'Arsenal', 'away_team': 'Man Utd'},
            {'fixture_id': 102, 'date': today, 'time': '15:00', 'home_team': 'Liverpool', 'away_team': 'Chelsea'},
            {'fixture_id': 103, 'date': tomorrow, 'time': '16:30', 'home_team': 'Man City', 'away_team': 'Spurs'},
        ]
    # La Liga Mock
    elif league_id == 140:
        return [
            {'fixture_id': 201, 'date': today, 'time': '20:00', 'home_team': 'Real Madrid', 'away_team': 'Barcelona'},
            {'fixture_id': 202, 'date': tomorrow, 'time': '18:30', 'home_team': 'Atletico', 'away_team': 'Sevilla'},
        ]
    return []


# =============================================================================
# MAIN FIXTURE FETCHING
# =============================================================================

def fetch_fixtures_with_cache(league_id: int, count: int = 10) -> List[Dict]:
    """
    Fetch upcoming fixtures with caching and API fallback.
    1. Check Cache
    2. If missing/old -> Call API -> Save Cache
    3. If API fails -> Return Mock Data
    """
    # 1. Check Cache
    cached_data = get_cached_fixtures(league_id)
    if cached_data:
        return cached_data

    # 2. Call API
    season = get_current_season()
    url = f"{API_FOOTBALL_BASE}/fixtures"
    params = {
        "league": league_id,
        "season": season,
        "next": count
    }
    
    logger.info(f"🌐 Calling API for League {league_id}...")
    
    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=15)
        
        # Check quotas
        if response.status_code in [429, 403]:
            logger.warning(f"API Quota Exceeded ({response.status_code}). Using Mock Data.")
            return get_mock_fixtures(league_id)
            
        response.raise_for_status()
        data = response.json()
        
        if data.get('errors'):
            logger.error(f"API Error: {data['errors']}")
            return get_mock_fixtures(league_id)

        fixtures = []
        for fixture in data.get('response', []):
            fixture_data = fixture.get('fixture', {})
            teams = fixture.get('teams', {})
            
            # Parse datetime
            fixture_datetime = fixture_data.get('date', '')
            fixture_date = fixture_datetime[:10] if fixture_datetime else ''
            fixture_time = fixture_datetime[11:16] if len(fixture_datetime) > 11 else '00:00'
            
            fixtures.append({
                'fixture_id': fixture_data.get('id'),
                'date': fixture_date,
                'time': fixture_time,
                'datetime': fixture_datetime,
                'status': fixture_data.get('status', {}).get('short', 'NS'),
                'home_team': teams.get('home', {}).get('name', 'Unknown'),
                'away_team': teams.get('away', {}).get('name', 'Unknown'),
                'home_team_id': teams.get('home', {}).get('id'),
                'away_team_id': teams.get('away', {}).get('id'),
                'league_id': league_id
            })
        
        if not fixtures:
            # Don't cache empty results, maybe just return mock
            return get_mock_fixtures(league_id)
            
        # Save to Cache
        update_fixture_cache(league_id, fixtures)
        logger.info(f"✅ Saved {len(fixtures)} fixtures to cache.")
        return fixtures
    
    except Exception as e:
        logger.error(f"Error fetching fixtures: {e}")
        return get_mock_fixtures(league_id)


# =============================================================================
# TEAM STATISTICS (Legacy Support)
# =============================================================================

def calculate_form_score(form_string: str) -> int:
    """Calculate 0-100 form score."""
    if not form_string: return 50
    points = 0
    for char in form_string.upper():
        if char == 'W': points += 3
        elif char == 'D': points += 1
    max_points = 3 * len(form_string)
    if max_points == 0: return 50
    return int((points / max_points) * 100)


def fetch_team_statistics(team_id: int) -> Dict[str, Any]:
    """Fetch detailed team stats (kept for compatibility)."""
    # Simply delegates raw fetching, we focused optimization on fixtures list
    # Could add caching here too, but prioritized fixtures as requested.
    url = f"{API_FOOTBALL_BASE}/teams/statistics"
    params = {"league": EPL_LEAGUE_ID, "season": CURRENT_SEASON, "team": team_id}
    
    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=15)
        response.raise_for_status()
        data = response.json().get('response', {})
        
        if not data: return {}
        
        team_info = data.get('team', {})
        fixtures = data.get('fixtures', {})
        
        return {
            'team_name': team_info.get('name', 'Unknown'),
            'team_id': team_id,
            'win_rate': round((fixtures.get('wins', {}).get('total', 0) / (fixtures.get('played', {}).get('total', 1))) * 100, 1),
            'form_score': calculate_form_score(data.get('form', ''))
        }
    except Exception:
        return {}


def get_todays_matches() -> List[Dict]:
    """Legacy wrapper for old scripts."""
    return fetch_fixtures_with_cache(EPL_LEAGUE_ID, count=5)


if __name__ == "__main__":
    print("Testing Caching Mechanism...")
    print("1st Call (API):")
    fixtures = fetch_fixtures_with_cache(39)
    print(f"Found {len(fixtures)} matches.")
    
    print("\n2nd Call (Cache):")
    fixtures = fetch_fixtures_with_cache(39)
    print(f"Found {len(fixtures)} matches.")
