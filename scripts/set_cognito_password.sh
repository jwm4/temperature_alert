#!/bin/bash
# Set a permanent password for a Cognito user
#
# Usage: ./scripts/set_cognito_password.sh <email> <new_password>
#
# Password requirements:
# - At least 8 characters
# - At least one uppercase letter
# - At least one lowercase letter  
# - At least one number

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <email> <new_password>"
    echo "Example: $0 bill@example.com MySecurePass123"
    echo ""
    echo "Password requirements:"
    echo "  - At least 8 characters"
    echo "  - At least one uppercase letter"
    echo "  - At least one lowercase letter"
    echo "  - At least one number"
    exit 1
fi

EMAIL="$1"
PASSWORD="$2"
POOL_ID="us-east-1_jGdk3Eacq"
REGION="us-east-1"

echo "Setting permanent password for: $EMAIL"

aws cognito-idp admin-set-user-password \
    --user-pool-id "$POOL_ID" \
    --username "$EMAIL" \
    --password "$PASSWORD" \
    --permanent \
    --region "$REGION"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Password set successfully!"
    echo ""
    echo "You can now get an access token with:"
    echo "  python scripts/get_cognito_token.py $EMAIL '$PASSWORD'"
else
    echo ""
    echo "❌ Failed to set password"
fi
