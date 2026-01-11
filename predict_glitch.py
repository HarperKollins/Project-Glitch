"""
Predict Glitch - Multi-Market Match Predictor
==============================================
Uses 3 trained models to predict:
1. Match Result (Home/Draw/Away)
2. Over/Under 2.5 Goals
3. Both Teams to Score (BTTS)

Recommends the "Safest Glitch" - the bet with highest confidence.

Usage: python predict_glitch.py "Arsenal" "Liverpool"
"""

import sys
import json
import pickle
import pandas as pd
import numpy as np
from collections import defaultdict


def load_models():
    """
    Load all trained models and configuration.
    """
    try:
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        with open(os.path.join(script_dir, 'features.json'), 'r') as f:
            config = json.load(f)
        
        models = {}
        for name in ['win', 'goals', 'btts']:
            model_path = os.path.join(script_dir, f"model_{name}.pkl")
            with open(model_path, 'rb') as f:
                models[name] = pickle.load(f)
        
        return models, config
    except FileNotFoundError as e:
        return None, None


def get_best_prediction():
    """
    Get prediction for a featured match.
    Called by main.py for /glitch command.
    Returns prediction for Arsenal vs Liverpool as default demo.
    """
    try:
        return predict_all_markets("Arsenal", "Liverpool")
    except Exception as e:
        print(f"Prediction error: {e}")
        return None


def load_historical_data(data_path='master_data.csv'):
    """
    Load and prepare historical match data.
    """
    try:
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(script_dir, data_path)
        
        df = pd.read_csv(full_path)
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
        df = df.sort_values('Date').reset_index(drop=True)
        return df
    except FileNotFoundError:
        print(f"❌ Error: {data_path} not found!")
        return None


def get_team_stats(df: pd.DataFrame, team_name: str, is_home: bool, n_games: int = 5) -> dict:
    """
    Get comprehensive stats for a team from their last N games.
    """
    # Get venue-specific games
    if is_home:
        venue_games = df[df['HomeTeam'] == team_name].tail(n_games)
        if len(venue_games) < n_games:
            venue_games = df[(df['HomeTeam'] == team_name) | (df['AwayTeam'] == team_name)].tail(n_games)
    else:
        venue_games = df[df['AwayTeam'] == team_name].tail(n_games)
        if len(venue_games) < n_games:
            venue_games = df[(df['HomeTeam'] == team_name) | (df['AwayTeam'] == team_name)].tail(n_games)
    
    if len(venue_games) == 0:
        return {
            'form': 7,
            'avg_goals': 1.3,
            'avg_conceded': 1.2,
            'btts_rate': 50.0
        }
    
    # Calculate form
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
        'avg_goals': avg_goals,
        'avg_conceded': avg_conceded,
        'btts_rate': btts_rate
    }


def prepare_features(home_stats: dict, away_stats: dict, feature_cols: list) -> pd.DataFrame:
    """
    Prepare a single-row DataFrame with all required features.
    """
    features = {
        'HomeTeam_Form': home_stats['form'],
        'AwayTeam_Form': away_stats['form'],
        'Home_Avg_Goals': home_stats['avg_goals'],
        'Away_Avg_Goals': away_stats['avg_goals'],
        'Home_Avg_Conceded': home_stats['avg_conceded'],
        'Away_Avg_Conceded': away_stats['avg_conceded'],
        'Home_BTTS_Rate': home_stats['btts_rate'],
        'Away_BTTS_Rate': away_stats['btts_rate']
    }
    
    return pd.DataFrame([features])[feature_cols]


def predict_all_markets(home_team: str, away_team: str, check_squad: bool = True):
    """
    Run predictions on all 3 markets and find the best bet.
    Optionally checks squad news before predicting.
    """
    # Load models
    models, config = load_models()
    if models is None:
        return {'error': 'Models not loaded. Run train_glitch.py first.'}
    
    feature_cols = config['features']
    
    # Load data and get stats
    df = load_historical_data()
    if df is None:
        return {'error': 'Historical data not found.'}
    
    home_stats = get_team_stats(df, home_team, is_home=True)
    away_stats = get_team_stats(df, away_team, is_home=False)
    
    # Check squad intelligence (injuries/suspensions)
    squad_news = None
    if check_squad:
        try:
            from scout import get_team_news, get_team_id, format_squad_report
            
            home_id = get_team_id(home_team)
            away_id = get_team_id(away_team)
            
            if home_id or away_id:
                squad_news = get_team_news(home_team_id=home_id, away_team_id=away_id)
                
                # Check if match should be skipped
                if squad_news.get('should_skip'):
                    return {
                        'home_team': home_team,
                        'away_team': away_team,
                        'skipped': True,
                        'skip_reason': squad_news['skip_reason'],
                        'squad_news': squad_news,
                        'home_stats': home_stats,
                        'away_stats': away_stats
                    }
        except ImportError:
            # Scout module not available, proceed without squad check
            pass
        except Exception as e:
            print(f"Squad check failed: {e}")
    
    # Prepare features
    X = prepare_features(home_stats, away_stats, feature_cols)
    
    # Get predictions from all models
    predictions = {}
    
    # Model 1: Match Result
    win_proba = models['win'].predict_proba(X)[0]
    win_pred = models['win'].predict(X)[0]
    predictions['win'] = {
        'prediction': ['Home Win', 'Draw', 'Away Win'][win_pred],
        'probabilities': {
            'Home Win': win_proba[0] * 100,
            'Draw': win_proba[1] * 100,
            'Away Win': win_proba[2] * 100
        },
        'best_prob': max(win_proba) * 100,
        'best_bet': ['Home Win', 'Draw', 'Away Win'][np.argmax(win_proba)],
        'home': win_proba[0] * 100,
        'draw': win_proba[1] * 100,
        'away': win_proba[2] * 100
    }
    
    # Model 2: Over/Under 2.5 Goals
    goals_proba = models['goals'].predict_proba(X)[0]
    predictions['goals'] = {
        'probabilities': {
            'Under 2.5': goals_proba[0] * 100,
            'Over 2.5': goals_proba[1] * 100
        },
        'best_prob': max(goals_proba) * 100,
        'best_bet': 'Over 2.5' if goals_proba[1] > goals_proba[0] else 'Under 2.5',
        'over': goals_proba[1] * 100,
        'under': goals_proba[0] * 100
    }
    
    # Model 3: BTTS
    btts_proba = models['btts'].predict_proba(X)[0]
    predictions['btts'] = {
        'probabilities': {
            'No BTTS': btts_proba[0] * 100,
            'BTTS': btts_proba[1] * 100
        },
        'best_prob': max(btts_proba) * 100,
        'best_bet': 'BTTS' if btts_proba[1] > btts_proba[0] else 'No BTTS',
        'yes': btts_proba[1] * 100,
        'no': btts_proba[0] * 100
    }
    
    # Find the SAFEST GLITCH (highest probability across all markets)
    all_bets = [
        ('win', predictions['win']['best_bet'], predictions['win']['best_prob']),
        ('goals', predictions['goals']['best_bet'], predictions['goals']['best_prob']),
        ('btts', predictions['btts']['best_bet'], predictions['btts']['best_prob'])
    ]
    
    safest = max(all_bets, key=lambda x: x[2])
    
    result = {
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
        'skipped': False,
        'model_accuracies': {
            'win': config['models']['win']['accuracy'],
            'goals': config['models']['goals']['accuracy'],
            'btts': config['models']['btts']['accuracy']
        }
    }
    
    # Add squad news if available
    if squad_news:
        result['squad_news'] = squad_news
    
    return result


def print_prediction(result: dict):
    """
    Print beautiful multi-market prediction output.
    """
    home = result['home_team']
    away = result['away_team']
    preds = result['predictions']
    safest = result['safest_glitch']
    home_stats = result['home_stats']
    away_stats = result['away_stats']
    
    print()
    print("═" * 60)
    print("🔮 THE GLITCH - MULTI-MARKET PREDICTION")
    print("═" * 60)
    print()
    print(f"⚽ {home} vs {away}")
    print()
    
    # ═══════════════════════════════════════════════════════════
    # SAFEST GLITCH (Best Bet)
    # ═══════════════════════════════════════════════════════════
    print("─" * 60)
    print("🎯 THE SAFEST GLITCH")
    print("─" * 60)
    print()
    
    market_emoji = {'win': '🏆', 'goals': '⚽', 'btts': '🥅'}
    implied_odds = 100 / safest['confidence'] if safest['confidence'] > 0 else 0
    
    print(f"   {market_emoji.get(safest['market'], '🎯')} Recommended Bet: {safest['bet'].upper()}")
    print(f"   📊 Confidence: {safest['confidence']:.1f}%")
    print(f"   📉 Implied Odds: {implied_odds:.2f}")
    print()
    
    # ═══════════════════════════════════════════════════════════
    # MARKET 1: Match Result
    # ═══════════════════════════════════════════════════════════
    print("─" * 60)
    print("🏆 MARKET 1: Match Result")
    print("─" * 60)
    
    for bet, prob in sorted(preds['win']['probabilities'].items(), key=lambda x: -x[1]):
        bar_len = int(prob / 2.5)
        bar = '█' * bar_len + '░' * (40 - bar_len)
        odds = 100 / prob if prob > 0 else 0
        marker = " ◄" if bet == preds['win']['best_bet'] else ""
        print(f"   {bet:12} {bar} {prob:5.1f}% (@ {odds:.2f}){marker}")
    print()
    
    # ═══════════════════════════════════════════════════════════
    # MARKET 2: Over/Under 2.5 Goals
    # ═══════════════════════════════════════════════════════════
    print("─" * 60)
    print("⚽ MARKET 2: Over/Under 2.5 Goals")
    print("─" * 60)
    
    for bet, prob in sorted(preds['goals']['probabilities'].items(), key=lambda x: -x[1]):
        bar_len = int(prob / 2.5)
        bar = '█' * bar_len + '░' * (40 - bar_len)
        odds = 100 / prob if prob > 0 else 0
        marker = " ◄" if bet == preds['goals']['best_bet'] else ""
        print(f"   {bet:12} {bar} {prob:5.1f}% (@ {odds:.2f}){marker}")
    print()
    
    # ═══════════════════════════════════════════════════════════
    # MARKET 3: BTTS
    # ═══════════════════════════════════════════════════════════
    print("─" * 60)
    print("🥅 MARKET 3: Both Teams to Score")
    print("─" * 60)
    
    for bet, prob in sorted(preds['btts']['probabilities'].items(), key=lambda x: -x[1]):
        bar_len = int(prob / 2.5)
        bar = '█' * bar_len + '░' * (40 - bar_len)
        odds = 100 / prob if prob > 0 else 0
        marker = " ◄" if bet == preds['btts']['best_bet'] else ""
        print(f"   {bet:12} {bar} {prob:5.1f}% (@ {odds:.2f}){marker}")
    print()
    
    # ═══════════════════════════════════════════════════════════
    # STATS USED
    # ═══════════════════════════════════════════════════════════
    print("─" * 60)
    print("📋 Stats Used (Last 5 Games)")
    print("─" * 60)
    print()
    print(f"   {home} (Home):")
    print(f"      Form: {home_stats['form']} pts | Goals: {home_stats['avg_goals']:.1f}")
    print(f"      Conceded: {home_stats['avg_conceded']:.1f} | BTTS Rate: {home_stats['btts_rate']:.0f}%")
    print()
    print(f"   {away} (Away):")
    print(f"      Form: {away_stats['form']} pts | Goals: {away_stats['avg_goals']:.1f}")
    print(f"      Conceded: {away_stats['avg_conceded']:.1f} | BTTS Rate: {away_stats['btts_rate']:.0f}%")
    print()
    
    # Footer
    print("═" * 60)
    print("⚠️  Disclaimer: For entertainment purposes only.")
    print("═" * 60)
    print()


def list_teams(df: pd.DataFrame):
    """
    List all available teams.
    """
    teams = sorted(set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique()))
    print("\n📋 Available Teams:")
    print("─" * 50)
    for i, team in enumerate(teams, 1):
        print(f"   {i:2}. {team}")
    print()


def main():
    """
    Main entry point.
    """
    if len(sys.argv) < 3:
        print()
        print("🔮 THE GLITCH - Multi-Market Predictor")
        print("=" * 50)
        print()
        print("Usage: python predict_glitch.py \"HomeTeam\" \"AwayTeam\"")
        print()
        print("Example:")
        print("   python predict_glitch.py \"Arsenal\" \"Liverpool\"")
        print("   python predict_glitch.py \"Man City\" \"Chelsea\"")
        print()
        
        try:
            df = load_historical_data()
            list_teams(df)
        except:
            pass
        return
    
    home_team = sys.argv[1]
    away_team = sys.argv[2]
    
    # Validate teams
    df = load_historical_data()
    all_teams = set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())
    
    if home_team not in all_teams:
        print(f"❌ Error: Team '{home_team}' not found.")
        list_teams(df)
        return
    
    if away_team not in all_teams:
        print(f"❌ Error: Team '{away_team}' not found.")
        list_teams(df)
        return
    
    # Get predictions
    result = predict_all_markets(home_team, away_team)
    print_prediction(result)


if __name__ == "__main__":
    main()
