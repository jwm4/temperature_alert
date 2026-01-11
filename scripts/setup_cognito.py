#!/usr/bin/env python3
"""
Set up Amazon Cognito User Pool for Temperature Agent authentication.

This script creates:
1. A Cognito User Pool (where users are stored)
2. An App Client (how our frontend connects)
3. A test user (you!)

Run with:
    cd /Users/bmurdock/git/temperature_alert
    source venv/bin/activate
    python scripts/setup_cognito.py

After running, update config.json with the output values.
"""

import boto3
import json
import secrets
import string
from pathlib import Path


def generate_temp_password(length=12):
    """Generate a temporary password that meets Cognito requirements."""
    # Must have uppercase, lowercase, number, special char
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(chars) for _ in range(length))
        # Verify it has all required character types
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*" for c in password)
        if has_upper and has_lower and has_digit and has_special:
            return password


def main():
    print("🔐 Setting up Amazon Cognito for Temperature Agent\n")
    
    # Use us-east-1 to match our Bedrock region
    region = "us-east-1"
    cognito = boto3.client("cognito-idp", region_name=region)
    
    pool_name = "temperature-agent-users"
    client_name = "temperature-agent-web"
    
    # Check if pool already exists
    print("Checking for existing user pool...")
    existing_pools = cognito.list_user_pools(MaxResults=60)
    for pool in existing_pools.get("UserPools", []):
        if pool["Name"] == pool_name:
            print(f"⚠️  User pool '{pool_name}' already exists!")
            print(f"   Pool ID: {pool['Id']}")
            
            # Get the app client
            clients = cognito.list_user_pool_clients(
                UserPoolId=pool["Id"],
                MaxResults=10
            )
            for client in clients.get("UserPoolClients", []):
                if client["ClientName"] == client_name:
                    # Get full client details
                    client_details = cognito.describe_user_pool_client(
                        UserPoolId=pool["Id"],
                        ClientId=client["ClientId"]
                    )["UserPoolClient"]
                    
                    print(f"   Client ID: {client['ClientId']}")
                    print(f"\n✅ Cognito is already set up!")
                    print_config_instructions(region, pool["Id"], client["ClientId"])
                    return
            
            print("   But no app client found. Creating one...")
            client_id = create_app_client(cognito, pool["Id"], client_name)
            print_config_instructions(region, pool["Id"], client_id)
            return
    
    # Create User Pool
    print(f"Creating user pool: {pool_name}")
    pool_response = cognito.create_user_pool(
        PoolName=pool_name,
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 8,
                "RequireUppercase": True,
                "RequireLowercase": True,
                "RequireNumbers": True,
                "RequireSymbols": False,  # Keep it simple
                "TemporaryPasswordValidityDays": 7
            }
        },
        AutoVerifiedAttributes=["email"],
        UsernameAttributes=["email"],  # Users sign in with email
        MfaConfiguration="OFF",  # Keep it simple for personal use
        UserAttributeUpdateSettings={
            "AttributesRequireVerificationBeforeUpdate": []
        },
        Schema=[
            {
                "Name": "email",
                "Required": True,
                "Mutable": True,
                "AttributeDataType": "String"
            }
        ],
        AdminCreateUserConfig={
            "AllowAdminCreateUserOnly": True  # Only admin can create users
        }
    )
    
    pool_id = pool_response["UserPool"]["Id"]
    print(f"✅ Created user pool: {pool_id}")
    
    # Create App Client
    client_id = create_app_client(cognito, pool_id, client_name)
    
    # Create a test user
    print("\nCreating test user...")
    temp_password = generate_temp_password()
    
    try:
        # Get user's email for the test user
        email = input("Enter your email address for the test user: ").strip()
        if not email or "@" not in email:
            print("Invalid email. Skipping user creation.")
        else:
            cognito.admin_create_user(
                UserPoolId=pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"}
                ],
                TemporaryPassword=temp_password,
                MessageAction="SUPPRESS"  # Don't send email, we'll show password here
            )
            print(f"✅ Created user: {email}")
            print(f"   Temporary password: {temp_password}")
            print("   (You'll be asked to change this on first login)")
    except Exception as e:
        print(f"⚠️  Could not create user: {e}")
    
    print_config_instructions(region, pool_id, client_id)


def create_app_client(cognito, pool_id, client_name):
    """Create an app client for the user pool."""
    print(f"Creating app client: {client_name}")
    
    client_response = cognito.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName=client_name,
        GenerateSecret=False,  # No secret for public clients (web apps)
        ExplicitAuthFlows=[
            "ALLOW_USER_PASSWORD_AUTH",  # Username/password login
            "ALLOW_REFRESH_TOKEN_AUTH",  # Token refresh
            "ALLOW_USER_SRP_AUTH",  # Secure Remote Password (recommended)
        ],
        SupportedIdentityProviders=["COGNITO"],
        PreventUserExistenceErrors="ENABLED",
        # Token validity
        AccessTokenValidity=1,  # 1 hour
        IdTokenValidity=1,  # 1 hour  
        RefreshTokenValidity=30,  # 30 days
        TokenValidityUnits={
            "AccessToken": "hours",
            "IdToken": "hours",
            "RefreshToken": "days"
        }
    )
    
    client_id = client_response["UserPoolClient"]["ClientId"]
    print(f"✅ Created app client: {client_id}")
    return client_id


def print_config_instructions(region, pool_id, client_id):
    """Print instructions for updating config."""
    # Construct the issuer URL (OIDC discovery endpoint)
    issuer_url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"
    
    print("\n" + "="*60)
    print("📋 CONFIGURATION VALUES")
    print("="*60)
    print(f"""
Add these to your config.json:

    "cognito_region": "{region}",
    "cognito_user_pool_id": "{pool_id}",
    "cognito_client_id": "{client_id}",
    "cognito_issuer_url": "{issuer_url}"

For AgentCore Runtime OAuth configuration:
    Discovery URL: {issuer_url}/.well-known/openid-configuration
    
""")
    
    # Also save to a file for easy reference
    config_values = {
        "cognito_region": region,
        "cognito_user_pool_id": pool_id,
        "cognito_client_id": client_id,
        "cognito_issuer_url": issuer_url,
        "cognito_discovery_url": f"{issuer_url}/.well-known/openid-configuration"
    }
    
    output_file = Path(__file__).parent.parent / ".local_docs" / "cognito_config.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(config_values, f, indent=2)
    
    print(f"💾 Config values also saved to: {output_file}")


if __name__ == "__main__":
    main()
