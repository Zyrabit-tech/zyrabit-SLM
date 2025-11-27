#!/bin/bash

# Script to set up Ollama and download necessary models for Zyrabit LLM Secure Suite

echo "Starting Ollama setup..."

# Function to check if Ollama server is running
check_ollama_running() {
    if pgrep -x "ollama" > /dev/null; then
        echo "Ollama server is already running."
        return 0
    else
        echo "Ollama server is not running. Attempting to start it..."
        # Try to start Ollama in the background. This might vary based on installation.
        # For macOS, it's often an application, or can be run from terminal if installed via brew.
        # For Linux, it might be a systemd service or a direct executable.
        # This is a generic attempt; users might need to adjust based on their Ollama installation.
        ollama serve &>/dev/null &
        OLLAMA_PID=$!
        sleep 5 # Give Ollama some time to start
        if pgrep -x "ollama" > /dev/null; then
            echo "Ollama server started successfully (PID: $OLLAMA_PID)."
            return 0
        else
            echo "Failed to start Ollama server. Please ensure Ollama is installed and runnable."
            echo "You might need to start Ollama manually (e.g., 'ollama serve' or launch the desktop app)."
            return 1
        fi
    fi
}

# Function to check if a model exists
check_model_exists() {
    local model_name=$1
    echo "Checking for model: $model_name..."
    if ollama list | grep -q "$model_name"; then
        echo "Model '$model_name' already exists."
        return 0
    else
        echo "Model '$model_name' not found."
        return 1
    fi
}

# Ensure Ollama is running
if ! check_ollama_running; then
    echo "Ollama is not running. Please start Ollama and re-run this script."
    exit 1
fi

# Define models to download
MODELS_TO_PULL=("phi3" "mxbai-embed-large")

# Pull models if they don't exist
for model in "${MODELS_TO_PULL[@]}"; do
    if ! check_model_exists "$model"; then
        echo "Pulling model: $model..."
        ollama pull "$model"
        if [ $? -eq 0 ]; then
            echo "Successfully pulled '$model'."
        else
            echo "Failed to pull '$model'. Please check your internet connection and Ollama installation."
            exit 1
        fi
    fi
done

echo "Ollama setup complete. All required models are available."
