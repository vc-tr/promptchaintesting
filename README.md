# n8n OpenAI Prompt Chain Demo

This demo shows how to create an interactive prompt chain using n8n and OpenAI API. You can have a continuous conversation with the AI where each response builds on the previous context.

## Features

-  **Prompt Chaining**: Maintain conversation context across multiple exchanges
-  **OpenAI Integration**: Uses your own OpenAI model's API key for intelligent responses
-  **Webhook API**: RESTful interface for easy integration
-  **Interactive Client**: Python client for testing and demonstration
-  **Docker Setup**: Easy deployment with Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- OpenAI API key
- Python 3.7+ (for the test client)

### 1. Setup

Clone and navigate to the project directory:

```bash
git clone <repository-url>
cd promptchaintesting
```

### 2. Configure OpenAI API

You have two options for configuring your OpenAI API key:

**Option A: Environment Variables (Recommended for automation)**
```bash
# Create .env file (or it will be created automatically)
echo "OPENAI_API_KEY=your_actual_api_key_here" > .env
```

**Option B: Manual Configuration in n8n UI**
- You can configure credentials directly in the n8n interface after startup

### 3. Start n8n

```bash
docker-compose up -d
```

This will start n8n on `http://localhost:5678`

### 4. Setup n8n Workflow

1. Open n8n in your browser: `http://localhost:5678`
2. Login with username: `admin`, password: `password`
3. Import the workflow:
   - Go to "Workflows" → "Import from File"
   - Select `workflows/prompt_chain_demo.json`
4. Configure OpenAI credentials (if not using environment variables):
   - **If you used Option A (environment variables)**: The workflow should automatically use your API key
   - **If you used Option B (manual)**: Click on the "OpenAI Chat" node and add your credentials manually
5. Save and activate the workflow

### 5. Test the Demo

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Start the interactive chat:

```bash
python test_client.py
```

Or send a single message:

```bash
python test_client.py "Hello, can you help me understand how this prompt chain works?"
```

## Environment Variables vs Manual Configuration

### Why Use Environment Variables?

**Environment Variables (Option A) Benefits:**
- ✅ **Automation-friendly**: Perfect for CI/CD, deployments, and scaling
- ✅ **Version control safe**: Keep secrets out of your workflow files
- ✅ **Team collaboration**: Each developer can use their own API key
- ✅ **Docker-native**: Follows container best practices
- ✅ **No manual setup**: Credentials auto-populate in n8n

**Manual Configuration (Option B) Benefits:**
- ✅ **Quick testing**: Good for one-off experiments
- ✅ **Visual confirmation**: See credentials directly in the UI
- ✅ **Fine-grained control**: Set different credentials per workflow

### How Environment Variables Work

When you set `OPENAI_API_KEY` in your `.env` file:
1. Docker Compose loads it into the n8n container
2. n8n can automatically use it for OpenAI nodes
3. No manual credential configuration needed in the UI
4. API key stays secure and separate from workflow configuration

## How It Works

### Workflow Overview

The n8n workflow consists of these nodes:

1. **Webhook** - Receives HTTP POST requests with user messages
2. **Parse Input** - Extracts message and conversation context
3. **Build Context** - Constructs the full conversation history
4. **OpenAI Chat** - Sends the conversation to OpenAI API
5. **Format Response** - Processes the AI response
6. **Respond** - Returns formatted response with continuation instructions

### API Usage

Send POST requests to `http://localhost:5678/webhook/chat` with:

```json
{
  "message": "Your message here",
  "conversation_history": "Previous conversation context (optional)"
}
```

Response format:

```json
{
  "success": true,
  "conversation_id": "conversation_identifier",
  "response": "AI response text",
  "conversation_history": "Full updated conversation",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "tokens_used": 150,
  "continue_url": "http://localhost:5678/webhook/chat",
  "instructions": "How to continue the conversation"
}
```

### Example Conversation Flow

1. **First message**:
   ```bash
   curl -X POST http://localhost:5678/webhook/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello, what can you help me with?"}'
   ```

2. **Continue conversation**:
   ```bash
   curl -X POST http://localhost:5678/webhook/chat \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Can you explain quantum computing?",
       "conversation_history": "User: Hello, what can you help me with?\n\nAssistant: Hello! I can help you with..."
     }'
   ```

## Customization

### Modify the AI Behavior

Edit the system prompt in the workflow:

1. Open the workflow in n8n
2. Click on the "OpenAI Chat" node
3. Modify the system message content
4. Save the workflow

### Change the Model

In the "OpenAI Chat" node, you can change:
- Model (e.g., `gpt-4`, `gpt-3.5-turbo`)
- Temperature (0.0 to 1.0)
- Max tokens
- Other OpenAI parameters

### Add Memory/Persistence

To add persistent conversation storage:

1. Add a database node (MongoDB, PostgreSQL, etc.)
2. Store conversation history with unique IDs
3. Retrieve context before sending to OpenAI
4. Update the stored conversation after each response

## Troubleshooting

### Common Issues

1. **n8n not accessible**: Check if Docker is running and port 5678 is available
2. **OpenAI API errors**: Verify your API key is correct and has sufficient credits
3. **Webhook not responding**: Ensure the workflow is active and saved
4. **Python client errors**: Install dependencies with `pip install -r requirements.txt`

### Debug Mode

To see detailed logs:

```bash
docker-compose logs -f n8n
```

### Reset Everything

To start fresh:

```bash
docker-compose down -v
docker-compose up -d
```

## Advanced Usage

### Integration Examples

**Use with Slack**:
- Add Slack nodes to receive/send messages
- Replace webhook with Slack trigger

**Use with Discord**:
- Add Discord webhook integration
- Build a Discord bot interface

**Use with Web Interface**:
- Create a simple web form
- Send AJAX requests to the webhook

### Environment Variables Best Practices

**For Development:**
```bash
# Copy the example and customize
cp .env.example .env
# Edit .env with your actual API key
vim .env
```

**For Production:**
```bash
# Set environment variables directly
export OPENAI_API_KEY="your-production-key"
docker-compose up -d
```

**For CI/CD:**
```bash
# Use secrets management
echo "$OPENAI_API_KEY_SECRET" > .env
docker-compose up -d
```

### Scaling Considerations

- Use n8n cloud for production
- Implement rate limiting
- Add conversation cleanup
- Use vector databases for long-term memory
- Store API keys in proper secret management systems

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License. 