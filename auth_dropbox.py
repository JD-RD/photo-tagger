#!/usr/bin/env python3
"""
Authenticate Dropbox - Helper script to generate a long-lived Refresh Token.
Short-lived access tokens expire every 4 hours. By generating a Refresh Token
and saving it to your .env file, photo-dl.py can automatically renew its
access without any manual intervention.
"""

import os
import sys
try:
    import dropbox
    from dotenv import load_dotenv, set_key
except ImportError:
    print("❌ Required packages not found. Run: pip install dropbox python-dotenv")
    sys.exit(1)

from pathlib import Path

def main():
    print("=== Dropbox Offline Authentication ===\n")
    load_dotenv()
    
    app_key = os.environ.get("DROPBOX_APP_KEY")
    app_secret = os.environ.get("DROPBOX_APP_SECRET")
    
    if not app_key or not app_secret:
        print("❌ DROPBOX_APP_KEY and DROPBOX_APP_SECRET are missing from your .env file.")
        print("\nTo get them:")
        print("1. Go to https://www.dropbox.com/developers/apps")
        print("2. Create a new App (Scoped access, Full Dropbox or App Folder).")
        print("3. Add 'files.metadata.read' and 'files.content.read' to Permissions.")
        print("4. Copy the App Key and App Secret into your .env file like this:")
        print("   DROPBOX_APP_KEY=your_app_key_here")
        print("   DROPBOX_APP_SECRET=your_app_secret_here")
        sys.exit(1)
        
    auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
        app_key, app_secret, token_access_type='offline'
    )
    
    authorize_url = auth_flow.start()
    
    print("1. Go to this URL in your web browser:")
    print(f"   {authorize_url}")
    print("\n2. Click 'Allow' (you might need to log in first).")
    print("3. Copy the authorization code provided.")
    print("-" * 50)
    
    auth_code = input("Enter the authorization code here: ").strip()
    if not auth_code:
        print("❌ No authorization code provided. Exiting.")
        sys.exit(1)
        
    try:
        oauth_result = auth_flow.finish(auth_code)
    except Exception as e:
        print(f"\n❌ Error during authentication: {e}")
        sys.exit(1)
        
    refresh_token = oauth_result.refresh_token
    
    if refresh_token:
        print("\n✅ Successfully generated refresh token!")
        
        env_path = Path('.env')
        set_key(env_path, "DROPBOX_REFRESH_TOKEN", refresh_token)
        
        print("💾 Saved DROPBOX_REFRESH_TOKEN to your .env file.")
        print("You can now run photo-dl.py indefinitely without needing to regenerate tokens manually!")
    else:
        print("\n❌ Failed to get a refresh token. Make sure you selected 'offline' access type.")

if __name__ == "__main__":
    main()