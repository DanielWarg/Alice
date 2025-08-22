# 🌐 Alice Web Interface

Modern, futuristic HUD-style web interface for the Alice AI Assistant Platform built with Next.js 13+.

## ✨ Key Features

### 🎨 HUD-Style Interface
- **Futuristic Design** - Cyan/blue theme with holographic effects
- **Real-time Metrics** - CPU, memory, network monitoring
- **Modular Panels** - Calendar, email, finance, reminders
- **Responsive Layout** - Works on desktop, tablet, mobile

### 🤖 AI Integration
- **Real-time Chat** - ChatGPT-style interface with Alice
- **Voice Control** - Dual voice system (VoiceBox + VoiceClient)
- **Tool Execution** - Visual feedback for tool actions
- **Swedish Support** - Native Swedish language interface

### 🎤 Advanced Voice Pipeline
- **VoiceBox Component** - Browser-based speech recognition
- **VoiceClient Component** - OpenAI Realtime API integration
- **Audio Visualization** - Real-time audio bars and animations
- **Swedish STT/TTS** - Optimized for Swedish pronunciation

## 🏗️ Architecture

### Component Structure
```
web/
├── app/                    # Next.js 13+ App Router
│   ├── globals.css        # Global styles and HUD theme
│   ├── layout.tsx         # Root layout with HUD structure
│   ├── page.tsx           # Main Alice HUD page
│   ├── api/               # API routes (proxy to backend)
│   │   ├── chat/          # Chat API endpoints
│   │   ├── tts/           # Text-to-Speech endpoints
│   │   ├── realtime/      # OpenAI Realtime integration
│   │   └── agent/         # Agent streaming bridge
│   └── voice/             # Voice demo page
├── components/             # React components
│   ├── AliceHUD.tsx       # Main HUD container
│   ├── VoiceBox.tsx       # Basic voice component
│   ├── VoiceClient.tsx    # Advanced voice component
│   ├── ChatInterface.tsx  # Chat messaging interface
│   ├── SystemMetrics.tsx  # Real-time system monitoring
│   ├── Calendar.tsx       # Calendar integration panel
│   ├── EmailPanel.tsx     # Email management panel
│   └── ToolExecutor.tsx   # Tool execution feedback
├── lib/                   # Utility libraries
│   ├── api.ts            # API client functions
│   ├── audio.ts          # Audio processing utilities
│   ├── voice.ts          # Voice pipeline management
│   └── websocket.ts      # WebSocket connection handling
├── hooks/                 # Custom React hooks
│   ├── useVoice.ts       # Voice component logic
│   ├── useWebSocket.ts   # WebSocket state management
│   └── useAlice.ts       # Main Alice API integration
└── types/                 # TypeScript type definitions
    ├── api.ts            # API response types
    ├── voice.ts          # Voice system types
    └── components.ts     # Component prop types
```

### Key Components

#### AliceHUD.tsx
Main container component that orchestrates the entire HUD interface:
```typescript
interface AliceHUDProps {
  initialMode: 'voice' | 'chat' | 'dual';
  showMetrics: boolean;
  theme: 'dark' | 'light' | 'auto';
}
```

#### VoiceBox.tsx  
Browser-based voice component with audio visualization:
```typescript
interface VoiceBoxProps {
  bars?: number;                    // Number of audio bars (default: 7)
  smoothing?: number;              // Audio smoothing factor
  onVoiceInput?: (text: string) => void;
  personality?: 'alice' | 'formal' | 'casual';
  emotion?: 'neutral' | 'happy' | 'calm' | 'confident' | 'friendly';
}
```

#### VoiceClient.tsx
Advanced OpenAI Realtime API voice component:
```typescript
interface VoiceClientProps {
  apiKey?: string;                 // OpenAI API key
  model?: string;                  // AI model (gpt-4o-realtime-preview)
  voice?: string;                  // Voice model (alloy, nova, etc.)
  onTranscript?: (text: string, isFinal: boolean) => void;
  onError?: (error: Error) => void;
}
```

## 🚀 Getting Started

### Prerequisites
- **Node.js 18+** with npm or yarn
- **TypeScript 5+** for type safety  
- **Next.js 13+** with App Router
- **OpenAI API Key** (for advanced voice features)

### Installation
```bash
# Install dependencies
npm install

# Setup environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development server
npm run dev

# Build for production
npm run build
npm run start
```

### Environment Configuration

Create `.env.local` with the following variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-key-here

# Alice Backend
NEXT_PUBLIC_ALICE_BACKEND_URL=http://localhost:8000

# Voice System
NEXT_PUBLIC_VOICE_MODE=dual                    # dual | voicebox | voiceclient
NEXT_PUBLIC_DEFAULT_PERSONALITY=alice          # alice | formal | casual
NEXT_PUBLIC_DEFAULT_EMOTION=friendly           # neutral | happy | calm | confident | friendly

# Development
NEXT_PUBLIC_DEVELOPMENT_MODE=true
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=false

# Production (uncomment for production)
# HTTPS=true
# NEXT_PUBLIC_VOICE_MODE=voiceclient
# NEXT_PUBLIC_ALICE_BACKEND_URL=https://api.alice.domain.com
```

## 🎯 Core Functionality

### Voice Pipeline Integration

Alice Web supports a sophisticated dual voice system:

**1. VoiceBox Mode (Basic)**
- Uses browser Speech Recognition API
- Real-time audio visualization
- Swedish post-processing
- Fallback to demo mode if microphone unavailable

**2. VoiceClient Mode (Advanced)**  
- OpenAI Realtime API with WebRTC
- Professional audio streaming
- Low-latency voice interaction
- Agent bridge for streaming responses

**3. Dual Mode (Recommended)**
- Automatic selection based on capabilities
- Fallback between modes as needed
- Runtime configuration switching

### API Integration

All API calls to Alice backend are proxied through Next.js API routes:

```typescript
// Example: Chat with Alice
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: 'spela musik',
    provider: 'auto',
    context: 'living_room'
  })
});
```

### Real-time Features

WebSocket connections provide real-time updates:

```typescript
// WebSocket integration
const ws = useWebSocket('/ws/alice');

ws.onMessage((event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'system_metrics':
      updateMetrics(data.data);
      break;
    case 'tool_update':
      showToolFeedback(data.data);
      break;
    case 'chat_response':
      addChatMessage(data.data);
      break;
  }
});
```

## 🎨 Styling & Theme

### HUD Design System
Alice Web uses a custom HUD-style design system with:

- **Primary Colors**: Cyan (#00FFFF), Blue (#0099FF)
- **Background**: Dark gradients with transparency
- **Typography**: Monospace fonts for technical feel
- **Effects**: Glow, shadows, animated borders
- **Components**: Modular panels with consistent styling

### CSS Architecture
```scss
// Global theme variables
:root {
  --alice-primary: #00FFFF;
  --alice-secondary: #0099FF;
  --alice-background: rgba(0, 0, 0, 0.9);
  --alice-panel: rgba(0, 255, 255, 0.1);
  --alice-glow: 0 0 20px rgba(0, 255, 255, 0.3);
}

// HUD panel styling
.alice-panel {
  background: var(--alice-panel);
  border: 1px solid var(--alice-primary);
  border-radius: 8px;
  box-shadow: var(--alice-glow);
  backdrop-filter: blur(10px);
}
```

## 🔧 Development

### Available Scripts

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # TypeScript type checking

# Testing
npm run test         # Run tests
npm run test:watch   # Run tests in watch mode
npm run test:coverage # Generate coverage report

# Voice System
npm run voice:test   # Test voice components
npm run voice:debug  # Debug voice pipeline
```

### Component Development

#### Creating New Components

```typescript
// components/NewComponent.tsx
import { FC } from 'react';

interface NewComponentProps {
  title: string;
  children?: React.ReactNode;
}

const NewComponent: FC<NewComponentProps> = ({ title, children }) => {
  return (
    <div className="alice-panel">
      <h2 className="alice-title">{title}</h2>
      {children}
    </div>
  );
};

export default NewComponent;
```

#### Voice Component Integration

```typescript
// Example: Using VoiceBox
import VoiceBox from '@/components/VoiceBox';

const MyComponent = () => {
  const handleVoiceInput = (text: string) => {
    // Send to Alice backend
    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: text })
    });
  };

  return (
    <VoiceBox
      bars={7}
      personality="alice"
      emotion="friendly"
      onVoiceInput={handleVoiceInput}
      allowDemo={true}
    />
  );
};
```

### API Routes

Custom API routes proxy requests to Alice backend:

```typescript
// app/api/chat/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const body = await request.json();
  
  const response = await fetch(`${process.env.ALICE_BACKEND_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  
  const data = await response.json();
  return NextResponse.json(data);
}
```

## 🚀 Deployment

### Production Build

```bash
# Create optimized production build
npm run build

# Start production server
npm run start
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
```

### Environment-specific Configurations

**Development:**
```bash
NEXT_PUBLIC_VOICE_MODE=dual
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=true
HTTPS=false
```

**Production:**
```bash
NEXT_PUBLIC_VOICE_MODE=voiceclient
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=false
HTTPS=true
NEXT_PUBLIC_ALICE_BACKEND_URL=https://api.alice.domain.com
```

## 🔍 Testing

### Component Testing
```typescript
// __tests__/components/VoiceBox.test.tsx
import { render, screen } from '@testing-library/react';
import VoiceBox from '@/components/VoiceBox';

describe('VoiceBox', () => {
  it('renders with correct number of bars', () => {
    render(<VoiceBox bars={5} />);
    const bars = screen.getAllByTestId('audio-bar');
    expect(bars).toHaveLength(5);
  });
  
  it('handles voice input correctly', () => {
    const mockHandler = jest.fn();
    render(<VoiceBox onVoiceInput={mockHandler} />);
    // Test voice input handling
  });
});
```

### Integration Testing
```typescript
// __tests__/api/chat.test.ts
import { POST } from '@/app/api/chat/route';
import { NextRequest } from 'next/server';

describe('/api/chat', () => {
  it('proxies requests to Alice backend', async () => {
    const request = new NextRequest('http://localhost:3000/api/chat', {
      method: 'POST',
      body: JSON.stringify({ prompt: 'test' })
    });
    
    const response = await POST(request);
    expect(response.status).toBe(200);
  });
});
```

## 🐛 Troubleshooting

### Common Issues

**1. Microphone Access Denied**
- Ensure HTTPS in production
- Check browser permissions
- Use `allowDemo={true}` for fallback

**2. Voice Recognition Not Working**
- Verify Speech API support
- Check network connectivity
- Enable voice debugging

**3. Backend Connection Failed**  
- Verify ALICE_BACKEND_URL configuration
- Check CORS settings
- Confirm backend is running

**4. Build Errors**
- Check TypeScript types
- Verify environment variables
- Clear .next cache: `rm -rf .next`

### Debug Mode

Enable comprehensive debugging:

```bash
# Environment variables
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=true
NEXT_PUBLIC_DEVELOPMENT_MODE=true

# Browser console
localStorage.setItem('alice_debug', 'true');
localStorage.setItem('voice_debug', 'true');
```

## 📚 Additional Resources

- **[Alice Backend API](../server/README.md)** - Backend documentation
- **[Voice Setup Guide](../VOICE_SETUP.md)** - Detailed voice configuration
- **[Agent Core](../AGENT_CORE.md)** - AI system documentation
- **[Development Guide](../DEVELOPMENT.md)** - Full development setup

---

**Alice Web Interface** - The future of AI assistance is here! 🚀

*Built with Next.js, TypeScript, and Swedish AI innovation.*