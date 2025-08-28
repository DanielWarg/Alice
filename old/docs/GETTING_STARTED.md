# 🚀 Getting Started with Alice

Alice is your Swedish AI assistant. This guide helps you install and use Alice for the first time.

## 📋 System Requirements

### Minimum
- **Python 3.9** or later
- **Node.js 18** or later  
- **4GB RAM** (8GB recommended)
- **10GB disk space** for AI models
- **Internet connection** for installation

### Recommended
- **macOS, Windows, or Linux**
- **8GB RAM or more** for best performance
- **SSD drive** for faster AI model loading

## ⚡ Installation (10 minutes)

### Step 1: Install Ollama (AI Engine)

**On macOS:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**On Windows:**
1. Download from [ollama.ai](https://ollama.ai)
2. Run the installer
3. Open command prompt

**On Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Step 2: Download AI Model
```bash
ollama pull gpt-oss:20b
```
*This can take 10-15 minutes depending on internet connection*

### Step 3: Start Ollama
```bash
ollama serve
```
*Let this run in the background*

### Step 4: Install Alice
```bash
# Clone Alice from GitHub
git clone https://github.com/DanielWarg/Alice.git
cd Alice

# Start Alice (does everything automatically)
./start_alice.sh
```

## 🎉 First Use

1. **Open your browser** and go to `http://localhost:3000`
2. **Wait for loading** - first time can take 30-60 seconds
3. **Say "Hello Alice"** or type a question in the text field

### 💬 First Conversation

Try these examples to test Alice:

```
You: Hello Alice, who are you?
Alice: Hello! I'm Alice, your Swedish AI assistant...

You: What can you help me with?
Alice: I can help you with many things...

You: What is the capital of Sweden?
Alice: The capital of Sweden is Stockholm...
```

## 🔧 Configuration (Optional)

### Add your integrations

Create a `.env` file in the project folder:

```bash
# Spotify (for music control)
SPOTIFY_CLIENT_ID=your_spotify_id
SPOTIFY_CLIENT_SECRET=your_spotify_secret

# Gmail (for email management)
GMAIL_CREDENTIALS=path/to/credentials.json

# OpenAI (for faster voice response, optional)
OPENAI_API_KEY=sk-...
```

### How to get API keys:

**Spotify:**
1. Go to [developer.spotify.com](https://developer.spotify.com)
2. Create an app
3. Copy Client ID and Client Secret

**Gmail:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Enable Gmail API
3. Download credentials.json

## ⚠️ Troubleshooting

### Alice won't start
```bash
# Check that Ollama is running
curl http://localhost:11434/api/tags

# Check that Python works
python3 --version

# Check that Node.js works  
node --version
```

### "Model not found"
```bash
# Download the model again
ollama pull gpt-oss:20b

# List installed models
ollama list
```

### Slow response
- **Check RAM** - Alice needs at least 4GB
- **Close other programs** that use a lot of memory
- **Wait** - the first question can take longer

### Port already in use
```bash
# Stop existing processes
pkill -f 'python.*run.py'
pkill -f 'npm run dev'

# Start Alice again
./start_alice.sh
```

## 🎯 Next Steps

Now that Alice is working, explore what you can do:

- **[What Alice Can Do](CAPABILITIES.md)** - All features and examples
- **[Voice Guide](VOICE_GUIDE.md)** - How to talk with Alice
- **[Integrations](INTEGRATIONS.md)** - Spotify, Gmail, calendar

## 🆘 Need Help?

- **[Common Issues](TROUBLESHOOTING.md)** - Solutions to common problems
- **[GitHub Issues](https://github.com/DanielWarg/Alice/issues)** - Report bugs
- **[Discord](https://discord.gg/alice-ai)** - Chat with other users

---

**Congratulations! 🎉 Alice is now ready to help you.**