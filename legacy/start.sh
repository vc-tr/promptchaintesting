#!/bin/bash

echo "🚀 Starting n8n Prompt Chain Demo"
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating one from template..."
    cat > .env << 'EOF'
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Organization ID (only needed if you belong to multiple organizations)
OPENAI_ORG_ID=
EOF
    echo "📝 Please edit .env file and add your OpenAI API key:"
    echo "   OPENAI_API_KEY=your_actual_api_key_here"
    echo ""
    read -p "Press Enter after you've updated the .env file..."
fi

# Start n8n with Docker Compose
echo "🐳 Starting n8n with Docker Compose..."
docker-compose up -d

# Wait for n8n to be ready
echo "⏳ Waiting for n8n to start..."
sleep 10

# Check if n8n is running
if curl -f http://localhost:5678 > /dev/null 2>&1; then
    echo "✅ n8n is running!"
    echo ""
    echo "🌐 n8n Interface: http://localhost:5678"
    echo "👤 Username: admin"
    echo "🔑 Password: password"
    echo ""
    echo "📋 Next steps:"
    echo "1. Open http://localhost:5678 in your browser"
    echo "2. Login with admin/password"
    echo "3. Import the workflow from workflows/prompt_chain_demo.json"
    echo "4. If using environment variables, workflow should auto-configure"
    echo "   Otherwise, configure OpenAI credentials in the 'OpenAI Chat' node"
    echo "5. Activate the workflow"
    echo "6. Run: python test_client.py"
    echo ""
    echo "📖 See README.md for detailed instructions"
else
    echo "❌ n8n failed to start. Check the logs:"
    echo "   docker-compose logs -f n8n"
fi 