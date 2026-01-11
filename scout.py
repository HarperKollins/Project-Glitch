"""
Scout - Real-Time Squad Intelligence
=====================================
Fetches lineups, injuries, and calculates squad strength scores.
This makes predictions smarter by checking team news before betting.
"""

import os
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()

# API Configuration
API_HOST = "v3.football.api-sports.io"
API_BASE = f"https://{API_HOST}"


def get_headers() -> Dict[str, str]:
    """Get API headers."""
    return {
        "x-rapidapi-host": API_HOST,
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY", "")
    }


def get_injuries(team_id: int, season: int = 2025) -> List[Dict]:
    """
    Fetch injured/suspended players for a team.
    """
    url = f"{API_BASE}/injuries"
    params = {
        "team": team_id,
        "season": season
    }
    
    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        injuries = []
        for item in data.get('response', []):
            player = item.get('player', {})
            injury = item.get('fixture', {})
            
            injuries.append({
                'player_name': player.get('name', 'Unknown'),
                'player_id': player.get('id'),
                'reason': player.get('reason', 'Unknown'),
                'type': player.get('type', 'Unknown')  # Injury or Suspension
            })
        
        return injuries
    
    except requests.RequestException as e:
        print(f"Error fetching injuries: {e}")
        return []


def get_lineups(fixture_id: int) -> Dict[str, Any]:
    """
    Fetch confirmed lineups for a fixture.
    Returns lineups for both home and away teams.
    """
    url = f"{API_BASE}/fixtures/lineups"
    params = {"fixture": fixture_id}
    
    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        lineups = {
            'home': None,
            'away': None,
            'available': False
        }
        
        response_data = data.get('response', [])
        
        if len(response_data) >= 2:
            lineups['available'] = True
            lineups['home'] = {
                'team': response_data[0].get('team', {}).get('name'),
                'team_id': response_data[0].get('team', {}).get('id'),
                'formation': response_data[0].get('formation'),
                'starting_xi': [p.get('player', {}).get('name') for p in response_data[0].get('startXI', [])],
                'coach': response_data[0].get('coach', {}).get('name')
            }
            lineups['away'] = {
                'team': response_data[1].get('team', {}).get('name'),
                'team_id': response_data[1].get('team', {}).get('id'),
                'formation': response_data[1].get('formation'),
                'starting_xi': [p.get('player', {}).get('name') for p in response_data[1].get('startXI', [])],
                'coach': response_data[1].get('coach', {}).get('name')
            }
        
        return lineups
    
    except requests.RequestException as e:
        print(f"Error fetching lineups: {e}")
        return {'home': None, 'away': None, 'available': False}


def get_squad(team_id: int, season: int = 2025) -> List[Dict]:
    """
    Fetch full squad with player importance markers.
    """
    url = f"{API_BASE}/players/squads"
    params = {"team": team_id}
    
    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        players = []
        response_data = data.get('response', [])
        
        if response_data:
            for player in response_data[0].get('players', []):
                players.append({
                    'id': player.get('id'),
                    'name': player.get('name'),
                    'position': player.get('position'),
                    'number': player.get('number')
                })
        
        return players
    
    except requests.RequestException as e:
        print(f"Error fetching squad: {e}")
        return []


def calculate_squad_strength(team_id: int, injuries: List[Dict], key_players: List[str] = None) -> Dict[str, Any]:
    """
    Calculate Squad Strength Score (0-100).
    
    Scoring Logic:
    - Start with 100 points
    - -15 points if a top scorer/key attacker is missing
    - -10 points if captain/key defender is missing
    - -5 points for each other first-team player injured
    - -3 points for each squad player injured
    
    Returns score and reasoning.
    """
    score = 100
    reasons = []
    
    # Define key player keywords (positions and roles that matter most)
    key_positions = ['Attacker', 'Midfielder']
    critical_positions = ['Goalkeeper', 'Defender']
    
    # Key players by team (top scorers, captains - hardcoded for EPL top teams)
    key_players_db = {
        # Arsenal
        42: ['Saka', 'Saliba', 'Odegaard', 'Rice', 'Havertz'],
        # Chelsea
        49: ['Palmer', 'Jackson', 'Caicedo', 'Reece James'],
        # Man City
        50: ['Haaland', 'De Bruyne', 'Rodri', 'Dias'],
        # Liverpool
        40: ['Salah', 'Van Dijk', 'Alexander-Arnold', 'Mac Allister'],
        # Man United
        33: ['Fernandes', 'Rashford', 'Casemiro', 'Martinez'],
        # Tottenham
        47: ['Son', 'Maddison', 'Romero', 'Van de Ven']
    }
    
    team_key_players = key_players_db.get(team_id, [])
    
    for injury in injuries:
        player_name = injury.get('player_name', '')
        
        # Check if key player
        is_key = any(kp.lower() in player_name.lower() for kp in team_key_players)
        
        if is_key:
            score -= 15
            reasons.append(f"⚠️ KEY PLAYER OUT: {player_name}")
        else:
            score -= 3
            reasons.append(f"❌ {player_name} ({injury.get('reason', 'Injured')})")
    
    # Ensure score doesn't go below 0
    score = max(0, score)
    
    return {
        'score': score,
        'injuries_count': len(injuries),
        'reasons': reasons[:5],  # Limit to top 5 reasons
        'status': 'STRONG' if score >= 85 else ('MODERATE' if score >= 70 else 'WEAK')
    }


def get_team_news(fixture_id: int = None, home_team_id: int = None, away_team_id: int = None) -> Dict[str, Any]:
    """
    Main function to get comprehensive team news.
    
    Args:
        fixture_id: Fixture ID for lineup check
        home_team_id: Home team ID for injury check
        away_team_id: Away team ID for injury check
    
    Returns:
        Dictionary with squad strength for both teams and recommendation.
    """
    result = {
        'home': {'score': 100, 'status': 'UNKNOWN', 'injuries': []},
        'away': {'score': 100, 'status': 'UNKNOWN', 'injuries': []},
        'lineups_available': False,
        'should_skip': False,
        'skip_reason': None
    }
    
    # Check lineups if fixture_id provided
    if fixture_id:
        lineups = get_lineups(fixture_id)
        result['lineups_available'] = lineups.get('available', False)
        if lineups.get('home'):
            result['home']['lineup'] = lineups['home']
            home_team_id = home_team_id or lineups['home'].get('team_id')
        if lineups.get('away'):
            result['away']['lineup'] = lineups['away']
            away_team_id = away_team_id or lineups['away'].get('team_id')
    
    # Check injuries for home team
    if home_team_id:
        home_injuries = get_injuries(home_team_id)
        home_strength = calculate_squad_strength(home_team_id, home_injuries)
        result['home']['score'] = home_strength['score']
        result['home']['status'] = home_strength['status']
        result['home']['injuries'] = home_strength['reasons']
        result['home']['injuries_count'] = home_strength['injuries_count']
    
    # Check injuries for away team
    if away_team_id:
        away_injuries = get_injuries(away_team_id)
        away_strength = calculate_squad_strength(away_team_id, away_injuries)
        result['away']['score'] = away_strength['score']
        result['away']['status'] = away_strength['status']
        result['away']['injuries'] = away_strength['reasons']
        result['away']['injuries_count'] = away_strength['injuries_count']
    
    # Determine if match should be skipped
    min_score = min(result['home']['score'], result['away']['score'])
    if min_score < 70:
        result['should_skip'] = True
        weak_team = 'Home' if result['home']['score'] < result['away']['score'] else 'Away'
        result['skip_reason'] = f"{weak_team} team has too many key players missing (Squad Score: {min_score}%)"
    
    return result


def format_squad_report(news: Dict[str, Any], home_name: str = "Home", away_name: str = "Away") -> str:
    """
    Format squad news into a readable report.
    """
    lines = [
        "📋 *SQUAD INTELLIGENCE REPORT*",
        "─" * 30,
        ""
    ]
    
    # Home team
    home = news['home']
    status_emoji = "🟢" if home['status'] == 'STRONG' else ("🟡" if home['status'] == 'MODERATE' else "🔴")
    lines.extend([
        f"{status_emoji} *{home_name}*",
        f"   Squad Strength: {home['score']}% ({home['status']})"
    ])
    
    if home.get('injuries'):
        for injury in home['injuries'][:3]:
            lines.append(f"   {injury}")
    
    lines.append("")
    
    # Away team
    away = news['away']
    status_emoji = "🟢" if away['status'] == 'STRONG' else ("🟡" if away['status'] == 'MODERATE' else "🔴")
    lines.extend([
        f"{status_emoji} *{away_name}*",
        f"   Squad Strength: {away['score']}% ({away['status']})"
    ])
    
    if away.get('injuries'):
        for injury in away['injuries'][:3]:
            lines.append(f"   {injury}")
    
    lines.append("")
    lines.append("─" * 30)
    
    # Skip warning
    if news['should_skip']:
        lines.extend([
            "",
            "⚠️ *WARNING: MATCH SKIPPED*",
            f"_{news['skip_reason']}_",
            "_Variance too high for reliable prediction._"
        ])
    
    return "\n".join(lines)


# Team ID mapping for common EPL teams
TEAM_IDS = {
    'Arsenal': 42,
    'Aston Villa': 66,
    'Bournemouth': 35,
    'Brentford': 55,
    'Brighton': 51,
    'Chelsea': 49,
    'Crystal Palace': 52,
    'Everton': 45,
    'Fulham': 36,
    'Ipswich': 57,
    'Leicester': 46,
    'Liverpool': 40,
    'Man City': 50,
    'Man United': 33,
    'Manchester City': 50,
    'Manchester United': 33,
    'Newcastle': 34,
    'Nottingham Forest': 65,
    "Nott'm Forest": 65,
    'Southampton': 41,
    'Tottenham': 47,
    'West Ham': 48,
    'Wolves': 39
}


def get_team_id(team_name: str) -> Optional[int]:
    """Get team ID from team name."""
    # Direct match
    if team_name in TEAM_IDS:
        return TEAM_IDS[team_name]
    
    # Partial match
    for name, tid in TEAM_IDS.items():
        if team_name.lower() in name.lower() or name.lower() in team_name.lower():
            return tid
    
    return None


if __name__ == "__main__":
    # Test
    print("🔍 Testing Scout Module...")
    print()
    
    # Test with Arsenal
    arsenal_id = TEAM_IDS['Arsenal']
    print(f"Checking Arsenal (ID: {arsenal_id}) injuries...")
    
    news = get_team_news(home_team_id=arsenal_id, away_team_id=TEAM_IDS['Liverpool'])
    print(format_squad_report(news, "Arsenal", "Liverpool"))
