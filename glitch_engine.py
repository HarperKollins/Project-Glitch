"""
The Glitch Engine - ML-Powered Prediction Logic
================================================
Uses trained Random Forest models for multi-market predictions.
"""

import os
import pickle
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from collections import defaultdict


# Global cache for models
_models_cache = None
_config_cache = None
_data_cache = None


def load_models():
    """
    Load all trained models and configuration.
    """
    global _models_cache, _config_cache
    
    if _models_cache is not None:
        return _models_cache, _config_cache
    
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        with open(os.path.join(script_dir, 'features.json'), 'r') as f:
            _config_cache = json.load(f)
        
        _models_cache = {}
        for name in ['win', 'goals', 'btts']:
            model_path = os.path.join(script_dir, f"model_{name}.pkl")
            with open(model_path, 'rb') as f:
                _models_cache[name] = pickle.load(f)
        
        return _models_cache, _config_cache
    except FileNotFoundError as e:
        print(f"Warning: Models not found ({e}). Using fallback heuristics.")
        return None, None


def load_historical_data():
    """
    Load historical match data for stats calculation.
    """
    global _data_cache
    
    if _data_cache is not None:
        return _data_cache
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(script_dir, 'master_data.csv')
        
        df = pd.read_csv(data_path)
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
        df = df.sort_values('Date').reset_index(drop=True)
        _data_cache = df
        return df
    except FileNotFoundError:
        return None


def get_team_stats(df: pd.DataFrame, team_name: str, is_home: bool, n_games: int = 5) -> dict:
    """
    Get comprehensive stats for a team from their last N games.
    """
    if df is None:
        return {
            'form': 7,
            'avg_goals': 1.3,
            'avg_conceded': 1.2,
            'btts_rate': 50.0
        }
    
    # Get venue-specific games
    if is_home:
        venue_games = df[df['HomeTeam'] == team_name].tail(n_games)
    else:
        venue_games = df[df['AwayTeam'] == team_name].tail(n_games)
    
    # Fallback to all games if not enough venue-specific
    if len(venue_games) < 3:
        venue_games = df[(df['HomeTeam'] == team_name) | (df['AwayTeam'] == team_name)].tail(n_games)
    
    if len(venue_games) == 0:
        return {
            'form': 7,
            'avg_goals': 1.3,
            'avg_conceded': 1.2,
            'btts_rate': 50.0
        }
    
    # Calculate form points
    form = 0
    for _, row in venue_games.iterrows():
        is_home_game = row['HomeTeam'] == team_name
        result = row['FTR']
        if is_home_game:
            if result == 'H': form += 3
            elif result == 'D': form += 1
        else:
            if result == 'A': form += 3
            elif result == 'D': form += 1
    
    # Calculate venue-specific goals
    if is_home:
        home_games = df[df['HomeTeam'] == team_name].tail(n_games)
        if len(home_games) > 0:
            avg_goals = home_games['FTHG'].mean()
            avg_conceded = home_games['FTAG'].mean()
            btts_count = ((home_games['FTHG'] > 0) & (home_games['FTAG'] > 0)).sum()
            btts_rate = (btts_count / len(home_games)) * 100
        else:
            avg_goals, avg_conceded, btts_rate = 1.3, 1.2, 50.0
    else:
        away_games = df[df['AwayTeam'] == team_name].tail(n_games)
        if len(away_games) > 0:
            avg_goals = away_games['FTAG'].mean()
            avg_conceded = away_games['FTHG'].mean()
            btts_count = ((away_games['FTHG'] > 0) & (away_games['FTAG'] > 0)).sum()
            btts_rate = (btts_count / len(away_games)) * 100
        else:
            avg_goals, avg_conceded, btts_rate = 1.1, 1.4, 50.0
    
    return {
        'form': form,
        'avg_goals': float(avg_goals),
        'avg_conceded': float(avg_conceded),
        'btts_rate': float(btts_rate)
    }


def predict_match_ml(home_team: str, away_team: str) -> Dict[str, Any]:
    """
    Predict match using trained ML models.
    Returns predictions for all 3 markets.
    """
    models, config = load_models()
    df = load_historical_data()
    
    # If models not available, use fallback
    if models is None:
        return predict_match_heuristic(home_team, away_team)
    
    # Get team stats
    home_stats = get_team_stats(df, home_team, is_home=True)
    away_stats = get_team_stats(df, away_team, is_home=False)
    
    # Prepare features for the model
    # Matches the columns used during training (train_glitch.py)
    feature_cols = config['features']
    features = {
        'HomeTeam_Form': home_stats['form'],          # Points from last 5 games (max 15)
        'AwayTeam_Form': away_stats['form'],          # Points from last 5 games (max 15)
        'Home_Avg_Goals': home_stats['avg_goals'],    # Attack strength
        'Away_Avg_Goals': away_stats['avg_goals'],    # Attack strength
        'Home_Avg_Conceded': home_stats['avg_conceded'], # Defense weakness
        'Away_Avg_Conceded': away_stats['avg_conceded'], # Defense weakness
        'Home_BTTS_Rate': home_stats['btts_rate'],    # % of recent games with BTTS
        'Away_BTTS_Rate': away_stats['btts_rate']     # % of recent games with BTTS
    }
    
    # Convert to DataFrame for sklearn compatibility
    X = pd.DataFrame([features])[feature_cols]
    
    # Get predictions from all models
    predictions = {}
    
    # Model 1: Match Result
    win_proba = models['win'].predict_proba(X)[0]
    predictions['win'] = {
        'home': win_proba[0] * 100,
        'draw': win_proba[1] * 100,
        'away': win_proba[2] * 100,
        'best': ['Home Win', 'Draw', 'Away Win'][np.argmax(win_proba)],
        'confidence': max(win_proba) * 100
    }
    
    # Model 2: Over/Under 2.5 Goals
    goals_proba = models['goals'].predict_proba(X)[0]
    predictions['goals'] = {
        'under': goals_proba[0] * 100,
        'over': goals_proba[1] * 100,
        'best': 'Over 2.5' if goals_proba[1] > goals_proba[0] else 'Under 2.5',
        'confidence': max(goals_proba) * 100
    }
    
    # Model 3: BTTS
    btts_proba = models['btts'].predict_proba(X)[0]
    predictions['btts'] = {
        'no': btts_proba[0] * 100,
        'yes': btts_proba[1] * 100,
        'best': 'BTTS Yes' if btts_proba[1] > btts_proba[0] else 'BTTS No',
        'confidence': max(btts_proba) * 100
    }
    
    # Find safest glitch
    all_bets = [
        ('Match Result', predictions['win']['best'], predictions['win']['confidence']),
        ('Goals', predictions['goals']['best'], predictions['goals']['confidence']),
        ('BTTS', predictions['btts']['best'], predictions['btts']['confidence'])
    ]
    safest = max(all_bets, key=lambda x: x[2])
    
    return {
        'match': f"{home_team} vs {away_team}",
        'home_team': home_team,
        'away_team': away_team,
        'predictions': predictions,
        'safest_glitch': {
            'market': safest[0],
            'bet': safest[1],
            'confidence': safest[2]
        },
        'home_stats': home_stats,
        'away_stats': away_stats,
        'using_ml': True
    }


def predict_match_heuristic(home_team: str, away_team: str) -> Dict[str, Any]:
    """
    Fallback heuristic-based prediction when ML models aren't available.
    """
    df = load_historical_data()
    
    home_stats = get_team_stats(df, home_team, is_home=True) if df is not None else {
        'form': 7, 'avg_goals': 1.3, 'avg_conceded': 1.2, 'btts_rate': 50
    }
    away_stats = get_team_stats(df, away_team, is_home=False) if df is not None else {
        'form': 7, 'avg_goals': 1.1, 'avg_conceded': 1.4, 'btts_rate': 50
    }
    
    # Simple heuristic based on form
    total_form = home_stats['form'] + away_stats['form']
    if total_form == 0:
        total_form = 1
    
    home_strength = home_stats['form'] / total_form
    away_strength = away_stats['form'] / total_form
    
    # Predictions
    predictions = {
        'win': {
            'home': home_strength * 100 * 1.1,  # Home advantage
            'draw': 25,
            'away': away_strength * 100 * 0.9,
            'best': 'Home Win' if home_strength > away_strength else 'Away Win',
            'confidence': max(home_strength, away_strength) * 100
        },
        'goals': {
            'over': 50,
            'under': 50,
            'best': 'Over 2.5' if (home_stats['avg_goals'] + away_stats['avg_goals']) > 2.5 else 'Under 2.5',
            'confidence': 52
        },
        'btts': {
            'yes': (home_stats['btts_rate'] + away_stats['btts_rate']) / 2,
            'no': 100 - (home_stats['btts_rate'] + away_stats['btts_rate']) / 2,
            'best': 'BTTS Yes' if home_stats['btts_rate'] > 50 else 'BTTS No',
            'confidence': 55
        }
    }
    
    return {
        'match': f"{home_team} vs {away_team}",
        'home_team': home_team,
        'away_team': away_team,
        'predictions': predictions,
        'safest_glitch': {
            'market': 'Match Result',
            'bet': predictions['win']['best'],
            'confidence': predictions['win']['confidence']
        },
        'home_stats': home_stats,
        'away_stats': away_stats,
        'using_ml': False
    }


def predict_match(home_stats: Dict, away_stats: Dict) -> Dict[str, Any]:
    """
    Legacy function for compatibility with old code.
    Now uses ML models when team names are provided in stats.
    """
    home_team = home_stats.get('team_name', 'Home Team')
    away_team = away_stats.get('team_name', 'Away Team')
    
    return predict_match_ml(home_team, away_team)


def get_available_teams() -> List[str]:
    """
    Get list of available teams from historical data.
    """
    df = load_historical_data()
    if df is None:
        return []
    
    teams = set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())
    return sorted(teams)


if __name__ == "__main__":
    # Test
    result = predict_match_ml("Arsenal", "Liverpool")
    print(f"Match: {result['match']}")
    print(f"Safest Glitch: {result['safest_glitch']['bet']} ({result['safest_glitch']['confidence']:.1f}%)")
    print(f"Using ML: {result['using_ml']}")
