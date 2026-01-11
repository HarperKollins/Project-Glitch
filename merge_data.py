"""
Merge CSV Files - Combines all league data into one master file.
Supports: EPL (E0, E1), La Liga (SP1, SP2), and more.
"""

import os
import glob
import pandas as pd
from pathlib import Path


# League ID mapping based on filename patterns
LEAGUE_MAP = {
    'E0': {'name': 'Premier League', 'id': 39, 'country': 'England'},
    'E1': {'name': 'Championship', 'id': 40, 'country': 'England'},
    'E2': {'name': 'League One', 'id': 41, 'country': 'England'},
    'E3': {'name': 'League Two', 'id': 42, 'country': 'England'},
    'SP1': {'name': 'La Liga', 'id': 140, 'country': 'Spain'},
    'SP2': {'name': 'La Liga 2', 'id': 141, 'country': 'Spain'},
    'D1': {'name': 'Bundesliga', 'id': 78, 'country': 'Germany'},
    'D2': {'name': 'Bundesliga 2', 'id': 79, 'country': 'Germany'},
    'I1': {'name': 'Serie A', 'id': 135, 'country': 'Italy'},
    'I2': {'name': 'Serie B', 'id': 136, 'country': 'Italy'},
    'F1': {'name': 'Ligue 1', 'id': 61, 'country': 'France'},
    'F2': {'name': 'Ligue 2', 'id': 62, 'country': 'France'},
    'N1': {'name': 'Eredivisie', 'id': 88, 'country': 'Netherlands'},
    'P1': {'name': 'Primeira Liga', 'id': 94, 'country': 'Portugal'},
}


def get_league_from_filename(filename: str) -> dict:
    """
    Extract league info from filename.
    """
    name = Path(filename).stem.upper()
    
    # Check for known patterns
    for pattern, info in LEAGUE_MAP.items():
        if pattern in name:
            return info
    
    # Default to unknown
    return {'name': 'Unknown', 'id': 0, 'country': 'Unknown'}


def normalize_date(date_str: str) -> str:
    """
    Normalize date format to DD/MM/YYYY.
    Handles both 2-digit years ('23') and 4-digit years ('2023').
    """
    if not isinstance(date_str, str):
        return date_str
    
    parts = date_str.split('/')
    if len(parts) != 3:
        return date_str
    
    day, month, year = parts
    
    # Convert 2-digit year to 4-digit
    if len(year) == 2:
        year = f"20{year}"
    
    return f"{day}/{month}/{year}"


def merge_csv_files(data_folder: str = "data", output_file: str = "master_data.csv"):
    """
    Merge all CSV files from data folder into one master file.
    Adds League_ID column to identify the source league.
    """
    data_path = Path(data_folder)
    
    if not data_path.exists():
        print(f"❌ Error: Folder '{data_folder}' not found!")
        return
    
    # Find all CSV files using glob
    csv_files = list(data_path.glob("*.csv"))
    
    if not csv_files:
        print(f"❌ Error: No CSV files found in '{data_folder}'!")
        return
    
    print("═" * 50)
    print("🔄 MERGE DATA - Multi-League Merger")
    print("═" * 50)
    print(f"\n📂 Found {len(csv_files)} CSV files to merge...\n")
    
    # Read and combine all CSVs
    all_dataframes = []
    league_counts = {}
    
    for csv_file in sorted(csv_files):
        try:
            df = pd.read_csv(csv_file, encoding='utf-8', low_memory=False)
            
            # Get league info from filename
            league_info = get_league_from_filename(csv_file.name)
            
            # Add league columns
            df['League'] = league_info['name']
            df['League_ID'] = league_info['id']
            df['Country'] = league_info['country']
            df['_source_file'] = csv_file.name
            
            all_dataframes.append(df)
            
            # Track counts
            league_name = league_info['name']
            if league_name not in league_counts:
                league_counts[league_name] = 0
            league_counts[league_name] += len(df)
            
            print(f"  ✅ {csv_file.name:20} | {len(df):4} rows | {league_name}")
            
        except Exception as e:
            print(f"  ⚠️ Failed to read {csv_file.name}: {e}")
    
    if not all_dataframes:
        print("❌ Error: No data could be loaded!")
        return
    
    # Show league summary
    print("\n" + "─" * 50)
    print("📊 League Summary:")
    for league, count in sorted(league_counts.items()):
        print(f"   {league:20} {count:6} matches")
    print("─" * 50)
    
    # Concatenate all dataframes
    print("\n🔄 Merging dataframes...")
    master_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Fix date format
    if 'Date' in master_df.columns:
        print("📅 Normalizing date formats...")
        master_df['Date'] = master_df['Date'].apply(normalize_date)
        
        # Convert to datetime for proper sorting
        master_df['_date_parsed'] = pd.to_datetime(
            master_df['Date'], 
            format='%d/%m/%Y', 
            errors='coerce'
        )
        
        # Sort by date
        print("📊 Sorting by date...")
        master_df = master_df.sort_values('_date_parsed', ascending=True)
        
        # Remove helper column
        master_df = master_df.drop(columns=['_date_parsed'])
    
    # Remove source file tracking column before saving
    if '_source_file' in master_df.columns:
        master_df = master_df.drop(columns=['_source_file'])
    
    # Remove duplicates
    initial_rows = len(master_df)
    if all(col in master_df.columns for col in ['Date', 'HomeTeam', 'AwayTeam', 'League_ID']):
        master_df = master_df.drop_duplicates(
            subset=['Date', 'HomeTeam', 'AwayTeam', 'League_ID'], 
            keep='first'
        )
        removed = initial_rows - len(master_df)
        if removed > 0:
            print(f"🗑️ Removed {removed} duplicate rows")
    
    # Save to file
    master_df.to_csv(output_file, index=False)
    
    print(f"\n{'═' * 50}")
    print(f"✨ Success! Merged {len(master_df)} rows of data.")
    print(f"📁 Saved to: {output_file}")
    print(f"{'═' * 50}")
    
    # Show final stats
    print(f"\n📈 Final Dataset Stats:")
    print(f"   Total Matches: {len(master_df)}")
    print(f"   Leagues: {master_df['League'].nunique()}")
    print(f"   Teams: {master_df['HomeTeam'].nunique()}")
    if 'FTHG' in master_df.columns:
        print(f"   Avg Goals/Match: {(master_df['FTHG'] + master_df['FTAG']).mean():.2f}")
    
    return master_df


if __name__ == "__main__":
    merge_csv_files()
