#!/bin/bash

# D&D Module Generator - Setup Script
# This script sets up the development environment using uv

set -e  # Exit on error

echo "🚀 Setting up D&D Module Generator environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed."
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"

    # Verify installation
    if ! command -v uv &> /dev/null; then
        echo "❌ Failed to install uv. Please install manually:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
fi

echo "✓ uv is installed ($(uv --version))"

# Create virtual environment
echo "📦 Creating virtual environment..."
uv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
uv pip sync

# Verify installation
echo "🔍 Verifying installation..."
if python -c "import google.genai; import fitz; import pytesseract; from dotenv import load_dotenv" 2>/dev/null; then
    echo "✓ All dependencies installed successfully"
else
    echo "⚠️  Some imports failed. Please check the installation."
fi

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo "📝 Please create a .env file with your Gemini API key:"
    echo "   echo 'GeminiImageAPI=your_api_key_here' > .env"
else
    echo "✓ .env file found"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the environment in the future, run:"
echo "   source .venv/bin/activate"
echo ""
echo "To run the pipeline:"
echo "   1. python src/split_pdf.py"
echo "   2. python src/pdf_to_xml.py"
echo "   3. python src/xml_to_html.py"
