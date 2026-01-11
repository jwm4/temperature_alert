#!/usr/bin/env python3
"""
Get a Cognito access token for testing the Temperature Agent API.

This script authenticates with Cognito and returns an access token
that can be used to call the AgentCore Runtime API.

Usage:
    python scripts/get_cognito_token.py <email> <password>
    
    # Or set environment variables:
    export COGNITO_USERNAME=your@email.com
    export COGNITO_PASSWORD=yourpassword
    python scripts/get_cognito_token.py
"""

import boto3
import sys
import os
import json
from pathlib import Path


def get_config():
    """Load Cognito config from config.json or .local_docs/cognito_config.json"""
    # Try config.json first
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            if "cognito_client_id" in config:
                return {
                    "region": config.get("cognito_region", "us-east-1"),
                    "client_id": config["cognito_client_id"],
                    "user_pool_id": config["cognito_user_pool_id"],
                }
    
    # Fall back to cognito_config.json
    cognito_config_path = Path(__file__).parent.parent / ".local_docs" / "cognito_config.json"
    if cognito_config_path.exists():
        with open(cognito_config_path) as f:
            config = json.load(f)
            return {
                "region": config.get("cognito_region", "us-east-1"),
                "client_id": config["cognito_client_id"],
                "user_pool_id": config["cognito_user_pool_id"],
            }
    
    raise FileNotFoundError("No Cognito configuration found")


def authenticate(username: str, password: str, config: dict) -> dict:
    """
    Authenticate with Cognito and return tokens.
    
    Returns:
        dict with access_token, id_token, refresh_token
    """
    client = boto3.client("cognito-idp", region_name=config["region"])
    
    try:
        response = client.initiate_auth(
            ClientId=config["client_id"],
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            }
        )
        
        # Check if we need to respond to a challenge (like NEW_PASSWORD_REQUIRED)
        if "ChallengeName" in response:
            challenge = response["ChallengeName"]
            if challenge == "NEW_PASSWORD_REQUIRED":
                print(f"\n⚠️  Your account requires a new password.")
                print("Please set a new password using the AWS Console or run:")
                print(f"  aws cognito-idp admin-set-user-password \\")
                print(f"    --user-pool-id {config['user_pool_id']} \\")
                print(f"    --username {username} \\")
                print(f"    --password 'YourNewPassword123!' \\")
                print(f"    --permanent")
                return None
            else:
                print(f"Unknown challenge: {challenge}")
                return None
        
        result = response["AuthenticationResult"]
        return {
            "access_token": result["AccessToken"],
            "id_token": result["IdToken"],
            "refresh_token": result.get("RefreshToken"),
            "expires_in": result["ExpiresIn"],
        }
        
    except client.exceptions.NotAuthorizedException as e:
        print(f"❌ Authentication failed: {e}")
        return None
    except client.exceptions.UserNotFoundException as e:
        print(f"❌ User not found: {username}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    # Get credentials from args or environment
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        username = os.environ.get("COGNITO_USERNAME")
        password = os.environ.get("COGNITO_PASSWORD")
    
    if not username or not password:
        print("Usage: python scripts/get_cognito_token.py <email> <password>")
        print("   Or: export COGNITO_USERNAME=... COGNITO_PASSWORD=... && python scripts/get_cognito_token.py")
        sys.exit(1)
    
    # Load config
    try:
        config = get_config()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    print(f"🔐 Authenticating as: {username}")
    print(f"   User Pool: {config['user_pool_id']}")
    print(f"   Client ID: {config['client_id']}")
    print()
    
    # Authenticate
    tokens = authenticate(username, password, config)
    
    if tokens:
        print("✅ Authentication successful!")
        print()
        print("Access Token (use this for API calls):")
        print("-" * 60)
        print(tokens["access_token"])
        print("-" * 60)
        print()
        print(f"Token expires in: {tokens['expires_in']} seconds")
        print()
        print("To test the API:")
        print(f'  curl -X POST http://localhost:8080/invocations \\')
        print(f'    -H "Content-Type: application/json" \\')
        print(f'    -H "Authorization: Bearer {tokens["access_token"][:50]}..." \\')
        print(f'    -d \'{{"prompt": "Hello!"}}\'' )
        
        # Also save to a file for easy use
        token_file = Path(__file__).parent.parent / ".local_docs" / "current_token.txt"
        token_file.parent.mkdir(exist_ok=True)
        with open(token_file, "w") as f:
            f.write(tokens["access_token"])
        print(f"\n💾 Token also saved to: {token_file}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
