"""
Utils - Output Formatting for Telegram
======================================
Creates beautiful, stylized output for multi-market predictions.
"""

from typing import Dict, Any, List


def format_prediction(prediction: Dict[str, Any]) -> str:
    """
    Format a single match prediction with multi-market output.
    """
    match_name = prediction.get('match', 'Unknown Match')
    preds = prediction.get('predictions', {})
    safest = prediction.get('safest_glitch', {})
    home_stats = prediction.get('home_stats', {})
    away_stats = prediction.get('away_stats', {})
    
    lines = [
        f"⚽ *{match_name}*",
        ""
    ]
    
    # Safest Glitch
    if safest:
        implied_odds = 100 / safest['confidence'] if safest['confidence'] > 0 else 0
        lines.extend([
            "🎯 *THE SAFEST GLITCH*",
            f"   Bet: *{safest['bet']}*",
            f"   Confidence: {safest['confidence']:.0f}%",
            f"   Implied Odds: {implied_odds:.2f}",
            ""
        ])
    
    # Market summaries
    if 'win' in preds:
        win = preds['win']
        lines.extend([
            "─────────────────────────",
            "🏆 *Match Result*",
            f"   Home: {win.get('home', 0):.0f}% | Draw: {win.get('draw', 0):.0f}% | Away: {win.get('away', 0):.0f}%",
            ""
        ])
    
    if 'goals' in preds:
        goals = preds['goals']
        lines.extend([
            "⚽ *Goals O/U 2.5*",
            f"   Over: {goals.get('over', 0):.0f}% | Under: {goals.get('under', 0):.0f}%",
            ""
        ])
    
    if 'btts' in preds:
        btts = preds['btts']
        lines.extend([
            "🥅 *BTTS*",
            f"   Yes: {btts.get('yes', 0):.0f}% | No: {btts.get('no', 0):.0f}%",
            ""
        ])
    
    # Stats used
    lines.extend([
        "─────────────────────────",
        f"📊 Form: Home {home_stats.get('form', 0)} pts | Away {away_stats.get('form', 0)} pts",
    ])
    
    return "\n".join(lines)


def format_all_predictions(predictions: List[Dict[str, Any]]) -> str:
    """
    Format multiple match predictions into a single message.
    """
    if not predictions:
        return "❌ No predictions available."
    
    sections = [
        "🧠 *PROJECT GLITCH - PREDICTIONS*",
        "═" * 25,
        ""
    ]
    
    for pred in predictions:
        sections.append(format_prediction(pred))
        sections.append("")
        sections.append("═" * 25)
        sections.append("")
    
    sections.extend([
        "⚠️ _Disclaimer: For entertainment only._",
        "🤖 Powered by The Glitch Engine v2.0"
    ])
    
    return "\n".join(sections)


def format_welcome_message() -> str:
    """
    Format the welcome message for /start command.
    """
    return """
🔮 *INITIALIZING PROJECT GLITCH...*

```
[████████████████████] 100%
[System Online] 🟢
```

Welcome to *The Glitch* - Your EPL Prediction Engine.

🧠 _"We see patterns where others see chaos."_

*Commands:*
├─ `/start` - Initialize system
├─ `/glitch` - Get ML predictions (using trained models)
├─ `/predict Home vs Away` - Predict specific match
└─ `/teams` - List available teams

⚡ Ready to predict. Send `/glitch` to begin.
"""


def format_loading_message() -> str:
    """
    Format a loading message.
    """
    return """
🔄 *ANALYZING DATA...*

```
[██████░░░░░░░░░░░░░░] 35%
Running ML models...
```

Please wait...
"""


def format_error_message(error: str = None) -> str:
    """
    Format an error message.
    """
    msg = """
❌ *SYSTEM ERROR*

```
[ERROR] Prediction failed
```
"""
    if error:
        msg += f"\n_Details:_ {error}"
    
    msg += "\n\n🔧 Try again in a few moments."
    return msg


def format_no_matches_message() -> str:
    """
    Format message when no matches are scheduled.
    """
    return """
📅 *NO MATCHES TODAY*

```
[STATUS] Standby Mode
```

No EPL fixtures scheduled today.
Use `/predict TeamA vs TeamB` for custom predictions!

🤖 _The Glitch is always watching..._
"""


def format_teams_list(teams: List[str]) -> str:
    """
    Format the list of available teams.
    """
    lines = [
        "📋 *AVAILABLE TEAMS*",
        "═" * 25,
        ""
    ]
    
    # Split into columns
    for i, team in enumerate(teams, 1):
        lines.append(f"{i:2}. {team}")
    
    lines.extend([
        "",
        "─────────────────────────",
        "Use: `/predict Arsenal vs Chelsea`"
    ])
    
    return "\n".join(lines)


def format_single_prediction(result: Dict[str, Any]) -> str:
    """
    Format a single prediction with full details.
    """
    home = result.get('home_team', 'Home')
    away = result.get('away_team', 'Away')
    preds = result.get('predictions', {})
    safest = result.get('safest_glitch', {})
    home_stats = result.get('home_stats', {})
    away_stats = result.get('away_stats', {})
    using_ml = result.get('using_ml', False)
    
    lines = [
        "═" * 30,
        "🔮 *THE GLITCH - PREDICTION*",
        "═" * 30,
        "",
        f"⚽ *{home} vs {away}*",
        "",
    ]
    
    # Safest Glitch
    if safest:
        implied_odds = 100 / safest['confidence'] if safest['confidence'] > 0 else 0
        emoji = "🏆" if "Win" in safest['bet'] else ("⚽" if "2.5" in safest['bet'] else "🥅")
        lines.extend([
            "─" * 30,
            "🎯 *THE SAFEST GLITCH*",
            "",
            f"   {emoji} *{safest['bet']}*",
            f"   📊 Confidence: *{safest['confidence']:.0f}%*",
            f"   📉 Implied Odds: {implied_odds:.2f}",
            ""
        ])
    
    # All markets
    if 'win' in preds:
        win = preds['win']
        lines.extend([
            "─" * 30,
            "🏆 *Match Result*",
            f"   🏠 Home: {win.get('home', 0):.0f}%",
            f"   🤝 Draw: {win.get('draw', 0):.0f}%",
            f"   ✈️ Away: {win.get('away', 0):.0f}%",
            ""
        ])
    
    if 'goals' in preds:
        goals = preds['goals']
        lines.extend([
            "─" * 30,
            "⚽ *Over/Under 2.5 Goals*",
            f"   📈 Over 2.5: {goals.get('over', 0):.0f}%",
            f"   📉 Under 2.5: {goals.get('under', 0):.0f}%",
            ""
        ])
    
    if 'btts' in preds:
        btts = preds['btts']
        lines.extend([
            "─" * 30,
            "🥅 *Both Teams to Score*",
            f"   ✅ BTTS Yes: {btts.get('yes', 0):.0f}%",
            f"   ❌ BTTS No: {btts.get('no', 0):.0f}%",
            ""
        ])
    
    # Stats
    lines.extend([
        "─" * 30,
        "📋 *Stats (Last 5 Games)*",
        "",
        f"   *{home}* (Home):",
        f"   Form: {home_stats.get('form', 0)} pts | Goals: {home_stats.get('avg_goals', 0):.1f}",
        "",
        f"   *{away}* (Away):",
        f"   Form: {away_stats.get('form', 0)} pts | Goals: {away_stats.get('avg_goals', 0):.1f}",
        ""
    ])
    
    # Footer
    ml_indicator = "🤖 ML Model" if using_ml else "📊 Heuristic"
    lines.extend([
        "═" * 30,
        f"_{ml_indicator} | For entertainment only_"
    ])
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    test = {
        'match': 'Arsenal vs Liverpool',
        'home_team': 'Arsenal',
        'away_team': 'Liverpool',
        'predictions': {
            'win': {'home': 54, 'draw': 26, 'away': 20},
            'goals': {'over': 62, 'under': 38},
            'btts': {'yes': 58, 'no': 42}
        },
        'safest_glitch': {'bet': 'Over 2.5', 'confidence': 62},
        'home_stats': {'form': 13, 'avg_goals': 2.0},
        'away_stats': {'form': 9, 'avg_goals': 1.8},
        'using_ml': True
    }
    
    print(format_single_prediction(test))
