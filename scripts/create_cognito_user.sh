#!/bin/bash
# Create a user in the Temperature Agent Cognito User Pool
#
# Usage: ./scripts/create_cognito_user.sh your@email.com

if [ -z "$1" ]; then
    echo "Usage: $0 <email>"
    echo "Example: $0 bill@example.com"
    exit 1
fi

EMAIL="$1"
POOL_ID="us-east-1_jGdk3Eacq"
REGION="us-east-1"

# Generate a temporary password
TEMP_PASSWORD=$(openssl rand -base64 12 | tr -dc 'A-Za-z0-9!@#$%' | head -c12)
# Ensure it has required characters
TEMP_PASSWORD="${TEMP_PASSWORD}Aa1!"

echo "Creating user: $EMAIL"
echo ""

aws cognito-idp admin-create-user \
    --user-pool-id "$POOL_ID" \
    --username "$EMAIL" \
    --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
    --temporary-password "$TEMP_PASSWORD" \
    --message-action SUPPRESS \
    --region "$REGION"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ User created successfully!"
    echo ""
    echo "📧 Email: $EMAIL"
    echo "🔑 Temporary Password: $TEMP_PASSWORD"
    echo ""
    echo "⚠️  On first login, you'll be asked to set a new password."
    echo ""
else
    echo ""
    echo "❌ Failed to create user"
fi
