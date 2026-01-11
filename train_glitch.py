"""
Train The Glitch - Multi-Market ML Model Training
==================================================
Trains 3 separate models for:
1. Match Result (Win/Draw/Loss)
2. Over/Under 2.5 Goals
3. Both Teams to Score (BTTS)
"""

import pandas as pd
import numpy as np
import json
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from collections import defaultdict


def calculate_rolling_stats(df: pd.DataFrame, n_games: int = 5) -> pd.DataFrame:
    """
    Calculate rolling statistics for each match based on previous N games.
    
    Features calculated:
    - HomeTeam_Form / AwayTeam_Form: Points from last 5 games
    - Home_Avg_Goals / Away_Avg_Goals: Avg goals scored
    - Home_Avg_Conceded / Away_Avg_Conceded: Avg goals conceded
    - Home_BTTS_Rate / Away_BTTS_Rate: % of games with BTTS
    """
    print(f"📊 Calculating rolling stats (last {n_games} games)...")
    
    # Sort by date
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Tracking dictionaries
    team_results = defaultdict(list)       # Form points
    home_goals = defaultdict(list)          # Goals at home
    home_conceded = defaultdict(list)       # Conceded at home
    away_goals = defaultdict(list)          # Goals away
    away_conceded = defaultdict(list)       # Conceded away
    home_btts = defaultdict(list)           # BTTS at home (0 or 1)
    away_btts = defaultdict(list)           # BTTS away (0 or 1)
    
    # Initialize columns
    new_cols = [
        'HomeTeam_Form', 'AwayTeam_Form',
        'Home_Avg_Goals', 'Away_Avg_Goals',
        'Home_Avg_Conceded', 'Away_Avg_Conceded',
        'Home_BTTS_Rate', 'Away_BTTS_Rate'
    ]
    for col in new_cols:
        df[col] = np.nan
    
    for idx, row in df.iterrows():
        home_team = row['HomeTeam']
        away_team = row['AwayTeam']
        
        # Calculate current stats BEFORE this match
        if len(team_results[home_team]) >= n_games:
            df.at[idx, 'HomeTeam_Form'] = sum(team_results[home_team][-n_games:])
        
        if len(team_results[away_team]) >= n_games:
            df.at[idx, 'AwayTeam_Form'] = sum(team_results[away_team][-n_games:])
        
        if len(home_goals[home_team]) >= n_games:
            df.at[idx, 'Home_Avg_Goals'] = np.mean(home_goals[home_team][-n_games:])
            df.at[idx, 'Home_Avg_Conceded'] = np.mean(home_conceded[home_team][-n_games:])
            df.at[idx, 'Home_BTTS_Rate'] = np.mean(home_btts[home_team][-n_games:]) * 100
        
        if len(away_goals[away_team]) >= n_games:
            df.at[idx, 'Away_Avg_Goals'] = np.mean(away_goals[away_team][-n_games:])
            df.at[idx, 'Away_Avg_Conceded'] = np.mean(away_conceded[away_team][-n_games:])
            df.at[idx, 'Away_BTTS_Rate'] = np.mean(away_btts[away_team][-n_games:]) * 100
        
        # NOW update tracking with this match's results
        ftr = row['FTR']
        fthg = row['FTHG']
        ftag = row['FTAG']
        
        # Form points
        if ftr == 'H':
            team_results[home_team].append(3)
            team_results[away_team].append(0)
        elif ftr == 'D':
            team_results[home_team].append(1)
            team_results[away_team].append(1)
        else:
            team_results[home_team].append(0)
            team_results[away_team].append(3)
        
        # Goals tracking
        home_goals[home_team].append(fthg)
        home_conceded[home_team].append(ftag)
        away_goals[away_team].append(ftag)
        away_conceded[away_team].append(fthg)
        
        # BTTS tracking
        btts_occurred = 1 if (fthg > 0 and ftag > 0) else 0
        home_btts[home_team].append(btts_occurred)
        away_btts[away_team].append(btts_occurred)
    
    return df


def create_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create target columns for all 3 markets.
    """
    print("🎯 Creating target columns...")
    
    df = df.copy()
    
    # Target 1: Match Result (0=Home, 1=Draw, 2=Away)
    df['Target_Win'] = df['FTR'].map({'H': 0, 'D': 1, 'A': 2})
    
    # Target 2: Over 2.5 Goals (1 if total > 2.5, else 0)
    df['Target_Goals'] = ((df['FTHG'] + df['FTAG']) > 2.5).astype(int)
    
    # Target 3: BTTS (1 if both teams scored, else 0)
    df['Target_BTTS'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)
    
    print(f"   Target_Win distribution:   {df['Target_Win'].value_counts().to_dict()}")
    print(f"   Target_Goals (Over 2.5):   {df['Target_Goals'].value_counts().to_dict()}")
    print(f"   Target_BTTS:               {df['Target_BTTS'].value_counts().to_dict()}")
    
    return df


def prepare_data(df: pd.DataFrame, feature_cols: list, target_col: str):
    """
    Prepare features and target for training.
    """
    df_clean = df.dropna(subset=feature_cols + [target_col])
    X = df_clean[feature_cols]
    y = df_clean[target_col]
    return X, y, df_clean


def train_single_model(X, y, model_name: str, test_size: float = 0.2):
    """
    Train a single Random Forest model with time-based split.
    """
    split_idx = int(len(X) * (1 - test_size))
    
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"\n   Training {model_name}...")
    print(f"   Train: {len(X_train)} | Test: {len(X_test)}")
    
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"   ✅ Accuracy: {accuracy * 100:.1f}%")
    
    return model, accuracy


def save_models(models: dict, feature_cols: list, accuracies: dict):
    """
    Save all trained models and configuration.
    """
    print("\n💾 Saving models...")
    
    for name, model in models.items():
        path = f"model_{name}.pkl"
        with open(path, 'wb') as f:
            pickle.dump(model, f)
        print(f"   Saved: {path}")
    
    # Save config
    config = {
        'features': feature_cols,
        'models': {
            'win': {
                'file': 'model_win.pkl',
                'type': 'classifier',
                'classes': ['Home', 'Draw', 'Away'],
                'accuracy': accuracies.get('win', 0)
            },
            'goals': {
                'file': 'model_goals.pkl',
                'type': 'binary',
                'classes': ['Under 2.5', 'Over 2.5'],
                'accuracy': accuracies.get('goals', 0)
            },
            'btts': {
                'file': 'model_btts.pkl',
                'type': 'binary',
                'classes': ['No BTTS', 'BTTS'],
                'accuracy': accuracies.get('btts', 0)
            }
        }
    }
    
    with open('features.json', 'w') as f:
        json.dump(config, f, indent=2)
    print("   Saved: features.json")


def main():
    """
    Main training pipeline for all 3 models.
    """
    print("=" * 60)
    print("🧠 THE GLITCH - Multi-Market Model Training")
    print("=" * 60)
    
    # Load data
    print("\n📂 Loading master_data.csv...")
    try:
        df = pd.read_csv('master_data.csv')
        print(f"   Loaded {len(df)} matches")
    except FileNotFoundError:
        print("❌ Error: master_data.csv not found!")
        return
    
    # Feature engineering
    df = calculate_rolling_stats(df, n_games=5)
    
    # Create targets
    df = create_targets(df)
    
    # Define feature columns
    feature_cols = [
        'HomeTeam_Form', 'AwayTeam_Form',
        'Home_Avg_Goals', 'Away_Avg_Goals',
        'Home_Avg_Conceded', 'Away_Avg_Conceded',
        'Home_BTTS_Rate', 'Away_BTTS_Rate'
    ]
    
    print(f"\n📋 Features: {feature_cols}")
    
    # Train 3 models
    print("\n" + "=" * 60)
    print("🌲 TRAINING MODELS")
    print("=" * 60)
    
    models = {}
    accuracies = {}
    
    # Model 1: Match Result
    print("\n📊 Model 1: Match Result (Win/Draw/Loss)")
    X, y, _ = prepare_data(df, feature_cols, 'Target_Win')
    models['win'], accuracies['win'] = train_single_model(X, y, "Match Result")
    
    # Model 2: Over/Under 2.5 Goals
    print("\n📊 Model 2: Over/Under 2.5 Goals")
    X, y, _ = prepare_data(df, feature_cols, 'Target_Goals')
    models['goals'], accuracies['goals'] = train_single_model(X, y, "Goals O/U 2.5")
    
    # Model 3: BTTS
    print("\n📊 Model 3: Both Teams to Score")
    X, y, _ = prepare_data(df, feature_cols, 'Target_BTTS')
    models['btts'], accuracies['btts'] = train_single_model(X, y, "BTTS")
    
    # Save all models
    save_models(models, feature_cols, accuracies)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ TRAINING COMPLETE")
    print("=" * 60)
    print(f"\n📈 Model Accuracies:")
    print(f"   Match Result:    {accuracies['win'] * 100:.1f}%")
    print(f"   Over/Under 2.5:  {accuracies['goals'] * 100:.1f}%")
    print(f"   BTTS:            {accuracies['btts'] * 100:.1f}%")
    print()


if __name__ == "__main__":
    main()
