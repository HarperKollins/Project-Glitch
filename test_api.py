"""
Test API Connection - Verify RapidAPI Football connection
==========================================================
Run: python test_api.py
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_connection():
    """
    Test connection to API-Football via RapidAPI.
    """
    print("=" * 50)
    print("🔍 THE GLITCH - API Connection Test")
    print("=" * 50)
    print()
    
    # Get API key
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        print("❌ ERROR: RAPIDAPI_KEY not found in .env file!")
        print("   Please add your key to .env:")
        print("   RAPIDAPI_KEY=your_key_here")
        return False
    
    print(f"🔑 API Key: {api_key[:8]}...{api_key[-4:]}")
    print()
    
    # Test endpoint
    url = "https://v3.football.api-sports.io/status"
    
    headers = {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": api_key
    }
    
    print("📡 Sending request to API-Football...")
    print(f"   URL: {url}")
    print()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"📥 Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            print("✅ CONNECTION SUCCESS!")
            print()
            print("─" * 50)
            print("📊 API Response:")
            print("─" * 50)
            
            data = response.json()
            
            # Pretty print important info
            if 'response' in data:
                resp = data['response']
                account = resp.get('account', {})
                subscription = resp.get('subscription', {})
                requests_info = resp.get('requests', {})
                
                print(f"\n👤 Account:")
                print(f"   Name: {account.get('firstname', 'N/A')} {account.get('lastname', '')}")
                print(f"   Email: {account.get('email', 'N/A')}")
                
                print(f"\n📦 Subscription:")
                print(f"   Plan: {subscription.get('plan', 'N/A')}")
                print(f"   End Date: {subscription.get('end', 'N/A')}")
                print(f"   Active: {subscription.get('active', False)}")
                
                print(f"\n📈 Requests:")
                print(f"   Used Today: {requests_info.get('current', 0)}")
                print(f"   Daily Limit: {requests_info.get('limit_day', 0)}")
                remaining = requests_info.get('limit_day', 0) - requests_info.get('current', 0)
                print(f"   Remaining: {remaining}")
            else:
                # Print raw response
                import json
                print(json.dumps(data, indent=2))
            
            print()
            print("=" * 50)
            print("🎉 API is ready to use!")
            print("=" * 50)
            return True
        
        else:
            print("❌ CONNECTION FAILED!")
            print()
            print(f"Error Response: {response.text}")
            return False
    
    except requests.Timeout:
        print("❌ CONNECTION FAILED!")
        print("   Error: Request timed out (10 seconds)")
        return False
    
    except requests.RequestException as e:
        print("❌ CONNECTION FAILED!")
        print(f"   Error: {e}")
        return False


if __name__ == "__main__":
    test_connection()
