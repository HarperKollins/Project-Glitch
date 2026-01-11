"""
The Glitch - Interactive Telegram Bot
======================================
Premium EPL/La Liga Prediction Bot with Button Navigation.

Run: python main.py
"""

import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Import modules
import predict_glitch
from data_manager import get_headers, API_FOOTBALL_BASE, fetch_fixtures_with_cache
import requests
from keep_alive import keep_alive

# Load environment variables
load_dotenv()

# League configuration
LEAGUES = {
    39: {'name': 'Premier League', 'flag': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'country': 'England'},
    140: {'name': 'La Liga', 'flag': '🇪🇸', 'country': 'Spain'},
}

# (get_current_season removal)
# (fetch_fixtures removal)



def format_fixture_button(fixture: dict) -> str:
    """
    Format fixture for button text.
    Shows: "Arsenal vs Chelsea (Sat 11/01 15:00)"
    """
    home = fixture['home_team']
    away = fixture['away_team']
    time = fixture['time']
    
    # Shorten long team names
    home = shorten_team_name(home)
    away = shorten_team_name(away)
    
    # Get day and date
    try:
        date_obj = datetime.strptime(fixture['date'], '%Y-%m-%d')
        day_date = date_obj.strftime('%a %d/%m')
    except:
        day_date = ""
    
    return f"{home} vs {away} ({day_date} {time})"


def shorten_team_name(name: str) -> str:
    """Shorten long team names for buttons."""
    replacements = {
        'Manchester United': 'Man Utd',
        'Manchester City': 'Man City',
        'Nottingham Forest': "Nott'm Forest",
        'Brighton and Hove Albion': 'Brighton',
        'Wolverhampton Wanderers': 'Wolves',
        'West Ham United': 'West Ham',
        'Newcastle United': 'Newcastle',
        'Tottenham Hotspur': 'Tottenham',
        'Athletic Club': 'Athletic',
        'Atletico Madrid': 'Atlético',
        'Real Sociedad': 'Real Sociedad',
        'Deportivo Alavés': 'Alavés',
    }
    return replacements.get(name, name)


# =============================================================================
# PIDGIN COMMENTARY
# =============================================================================

def generate_pidgin_commentary(result: dict) -> str:
    """
    Generate Pidgin English commentary based on prediction.
    """
    if result.get('skipped'):
        return "⚠️ Omo, too many players dey injured. Make we skip this one. E risky!"
    
    safest = result.get('safest_glitch', {})
    preds = result.get('predictions', {})
    confidence = safest.get('confidence', 0)
    bet = safest.get('bet', '')
    
    # High confidence home win
    if 'Home' in bet and confidence >= 60:
        return "🔥 Omo! This one na SURE BANKER for Home. Dem go chop dem!"
    
    # High confidence away win
    if 'Away' in bet and confidence >= 60:
        return "✈️ Away team go commot with the 3 points. Na dem get am!"
    
    # Draw smell
    if 'Draw' in bet or (preds.get('win', {}).get('draw', 0) > 28):
        return "🤝 Omo, fear this match. Draw dey smell here. Tread softly!"
    
    # High goals expected
    if 'Over' in bet and confidence >= 55:
        return "⚽ Expect plenty goals! Net go shake today. Over gang!"
    
    # Under goals
    if 'Under' in bet and confidence >= 55:
        return "🧱 This match go dey boring. Defense go lock up. Under 2.5!"
    
    # BTTS
    if 'BTTS' in bet and 'No' not in bet and confidence >= 55:
        return "🥅 Both teams go score! Goalkeepers no go rest today!"
    
    # Low confidence / volatile
    if confidence < 52:
        return "⚠️ This match get k-leg. Market too volatile. Bet small or skip!"
    
    # Default moderate confidence
    return "📊 Odds dey favor this pick, but football na football. Manage am!"


# =============================================================================
# BOT HANDLERS
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start and /glitch - Show league selection menu.
    """
    keyboard = []
    for league_id, info in LEAGUES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{info['flag']} {info['name']}", 
                callback_data=f"league_{league_id}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = """
👋 *Welcome to PROJECT GLITCH*
_Your AI-Powered Betting Intelligence_

🧠 Trained on 4,500+ matches
📊 Multi-market predictions
🔮 Real-time squad analysis

*Select your league to scan:*
"""
    
    await update.message.reply_text(
        message, 
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle all button callbacks.
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # League selection
    if data.startswith('league_'):
        league_id = int(data.split('_')[1])
        await show_fixtures(query, league_id)
    
    # Match prediction (p_HomeTeam_AwayTeam)
    elif data.startswith('p_'):
        parts = data.split('_')
        if len(parts) >= 3:
            home_team = parts[1]
            away_team = parts[2]
            await show_prediction(query, home_team, away_team)
    
    # Legacy predict_ format
    elif data.startswith('predict_'):
        parts = data.split('_', 2)
        if len(parts) >= 3:
            home_team = parts[1]
            away_team = parts[2]
            await show_prediction(query, home_team, away_team)
    
    # Back to menu
    elif data == 'back_menu':
        await show_main_menu(query)


async def show_main_menu(query) -> None:
    """Show main league menu."""
    keyboard = []
    for league_id, info in LEAGUES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{info['flag']} {info['name']}", 
                callback_data=f"league_{league_id}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔮 *PROJECT GLITCH*\n\n*Select your league:*",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


async def show_fixtures(query, league_id: int) -> None:
    """Show upcoming fixtures for a league."""
    league_info = LEAGUES.get(league_id, {'name': 'Unknown', 'flag': '⚽'})
    
    await query.edit_message_text(
        f"🔄 Loading {league_info['flag']} {league_info['name']} fixtures..."
    )
    
    # Fetch next 10 matches (with caching + fallback)
    fixtures = fetch_fixtures_with_cache(league_id, count=10)
    
    if not fixtures:
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]]
        await query.edit_message_text(
            f"{league_info['flag']} *{league_info['name']}*\n\n❌ No upcoming fixtures found.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Create buttons for each fixture
    keyboard = []
    for fixture in fixtures[:12]:  # Limit to 12 matches
        # Create callback data - use team names directly
        home_clean = re.sub(r'[^a-zA-Z]', '', fixture['home_team'])[:12]
        away_clean = re.sub(r'[^a-zA-Z]', '', fixture['away_team'])[:12]
        callback = f"p_{home_clean}_{away_clean}"
        
        button_text = format_fixture_button(fixture)
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Leagues", callback_data="back_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"{league_info['flag']} *{league_info['name']}*\n"
        f"📅 Next {len(fixtures)} matches\n\n"
        f"*Tap a match to get prediction:*",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


async def show_prediction(query, home_team: str, away_team: str) -> None:
    """Show prediction for a match."""
    
    # Show loading
    await query.edit_message_text(
        f"🔄 Scanning *{home_team}* vs *{away_team}*...\n\n"
        f"_Running ML models..._",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Get prediction
        result = predict_glitch.predict_all_markets(home_team, away_team)
        
        # Format output
        output = format_prediction_output(result, home_team, away_team)
        
        # Back button
        keyboard = [[InlineKeyboardButton("⬅️ Back to Matches", callback_data="back_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            output,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    except Exception as e:
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]]
        await query.edit_message_text(
            f"❌ Error getting prediction: {e}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


def format_prediction_output(result: dict, home: str, away: str) -> str:
    """Format the final prediction output with Pidgin commentary."""
    
    # Check if skipped
    if result.get('skipped'):
        return f"""
⚠️ *MATCH SKIPPED*
━━━━━━━━━━━━━━━━━━━━━━
⚽ *{home} vs {away}*

🚫 *HIGH VARIANCE ALERT*
{result.get('skip_reason', 'Too many key players missing')}

━━━━━━━━━━━━━━━━━━━━━━
🗣 *GLITCH SAYS:*
_{generate_pidgin_commentary(result)}_
"""
    
    safest = result.get('safest_glitch', {})
    preds = result.get('predictions', {})
    
    confidence = safest.get('confidence', 0)
    implied_odds = 100 / confidence if confidence > 0 else 0
    
    # Get current time
    now = datetime.now().strftime("%d %b %Y | %H:%M")
    
    # Build output
    output = f"""
📅 *{now}*
⚽ *{home} vs {away}*
━━━━━━━━━━━━━━━━━━━━━━

🎯 *SIGNAL:* {safest.get('bet', 'N/A')}
📊 *CONFIDENCE:* {confidence:.0f}%
📉 *IMPLIED ODDS:* {implied_odds:.2f}

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # Market breakdown
    if 'win' in preds:
        win = preds['win']
        output += f"""
🏆 *Result:* H {win.get('home', 0):.0f}% | D {win.get('draw', 0):.0f}% | A {win.get('away', 0):.0f}%"""
    
    if 'goals' in preds:
        goals = preds['goals']
        output += f"""
⚽ *Goals:* Over {goals.get('over', 0):.0f}% | Under {goals.get('under', 0):.0f}%"""
    
    if 'btts' in preds:
        btts = preds['btts']
        output += f"""
🥅 *BTTS:* Yes {btts.get('yes', 0):.0f}% | No {btts.get('no', 0):.0f}%"""
    
    # Pidgin commentary
    commentary = generate_pidgin_commentary(result)
    
    output += f"""

━━━━━━━━━━━━━━━━━━━━━━
🗣 *GLITCH SAYS:*
_{commentary}_
━━━━━━━━━━━━━━━━━━━━━━
_For entertainment only_ 🎰
"""
    
    return output


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main() -> None:
    """Main entry point."""
    token = os.getenv("TELEGRAM_TOKEN")
    
    if not token:
        print("❌ Error: No Token Found.")
        print("   Please add TELEGRAM_TOKEN to your .env file.")
        return
    
    print("🟢 Starting The Glitch Bot (Interactive Mode)...")
    
    # Build application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("glitch", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Handle any text message (Hi, Abeg, Update, etc.) - shows main menu
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    
    # Run
    print("🤖 Bot is running with BUTTON UI. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    print("🚀 STARTING BOT... PLEASE STOP ANY LOCAL INSTANCES TO AVOID CONFLICTS.")
    keep_alive()
    main()
