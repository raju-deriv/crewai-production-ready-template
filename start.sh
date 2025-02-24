#!/bin/bash

# Enable debug mode
set -x

# Function to check required environment variables
check_env_vars() {
    required_vars=(
        "SLACK_BOT_TOKEN"
        "SLACK_APP_TOKEN"
        "OPENAI_API_KEY"
        "OPENAI_MODEL"
        "ANTHROPIC_API_KEY"
        "ANTHROPIC_MODEL"
    )

    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        else
            echo "Found $var: ${!var:0:4}..."
        fi
    done

    if [[ ${#missing_vars[@]} -ne 0 ]]; then
        echo "Error: Missing required environment variables:"
        printf '%s\n' "${missing_vars[@]}"
        return 1
    fi

    # Check optional API base URLs
    if [[ -n "$OPENAI_API_BASE" ]]; then
        echo "Using custom OpenAI API base: $OPENAI_API_BASE"
    else
        echo "Using default OpenAI API base"
    fi

    if [[ -n "$ANTHROPIC_API_BASE" ]]; then
        echo "Using custom Anthropic API base: $ANTHROPIC_API_BASE"
    else
        echo "Using default Anthropic API base"
    fi

    return 0
}

# Print current working directory and files
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la

# Check if .env file exists
if [[ -f .env ]]; then
    echo ".env file exists"
    cat .env | grep -v "TOKEN\|KEY" # Print non-sensitive vars
else
    echo "Warning: .env file not found"
fi

# Check environment variables
echo "Validating environment variables..."
if ! check_env_vars; then
    echo "Environment validation failed. Exiting."
    exit 1
fi

# Start the application
echo "Starting CrewAI agent service..."
exec python -u main.py
