# 🤝 Contributing to Alice

Welcome to the Alice AI Assistant community! We're thrilled that you're interested in contributing to the world's first production-ready Swedish AI assistant platform. This guide will help you get started and ensure your contributions align with our community standards.

## 🎯 How to Contribute

Alice welcomes contributions from developers, linguists, designers, testers, and AI enthusiasts worldwide. Whether you're fixing a bug, implementing a new feature, improving Swedish language processing, or enhancing documentation, your contribution matters.

### 🌟 Types of Contributions

| 🔧 Contribution Type | 🎯 Skill Level | 📈 Impact | 🚀 Getting Started |
|---------------------|----------------|-----------|-------------------|
| **🐛 Bug Reports** | Beginner | High | [Report Issues](https://github.com/DanielWarg/Alice/issues/new?template=bug_report.md) |
| **💡 Feature Requests** | Beginner | Medium | [Start Discussion](https://github.com/DanielWarg/Alice/discussions/new) |
| **🔧 Code Contributions** | Intermediate+ | High | [Development Guide](#-development-workflow) |
| **🇸🇪 Swedish Language** | Native Speaker | Critical | [Language Issues](https://github.com/DanielWarg/Alice/labels/swedish) |
| **📚 Documentation** | Beginner+ | Medium | [Docs Issues](https://github.com/DanielWarg/Alice/labels/documentation) |
| **🧪 Testing & QA** | Intermediate | High | [Testing Guide](#-testing-requirements) |
| **🎨 Design & UX** | Designer | Medium | [Design Issues](https://github.com/DanielWarg/Alice/labels/design) |
| **🔒 Security** | Advanced | Critical | [Security Policy](SECURITY.md) |

## 🚀 Getting Started

### Prerequisites

Before contributing to Alice, ensure you have:

- **Python 3.9+** with pip (for backend development)
- **Node.js 18+** with npm (for frontend development)
- **Git** for version control
- **Ollama** with `gpt-oss:20B` model (for AI features)
- Basic understanding of Alice's architecture ([DEVELOPMENT.md](DEVELOPMENT.md))

### Quick Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/yourusername/Alice.git
cd Alice

# 2. Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install backend dependencies
pip install -r server/requirements.txt

# 4. Install frontend dependencies
cd web && npm install && cd ..

# 5. Set up Ollama (if needed)
ollama pull gpt-oss:20b
ollama serve &

# 6. Create feature branch
git checkout -b feature/your-amazing-feature
```

## 🔄 Development Workflow

### 1. Fork & Branch Strategy

1. **Fork** the Alice repository to your GitHub account
2. **Clone** your fork locally
3. **Create a feature branch** with a descriptive name:
   ```bash
   git checkout -b feature/swedish-voice-commands
   git checkout -b fix/calendar-timezone-bug
   git checkout -b docs/contributing-guide-update
   ```

### 2. Development Process

**For Backend Development (FastAPI):**
```bash
# Start backend with hot-reload
cd server
source ../.venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

**For Frontend Development (Next.js):**
```bash
# Start development server
cd web
npm run dev
```

**For Full-Stack Development:**
```bash
# Terminal 1: Backend
cd server && source ../.venv/bin/activate && uvicorn app:app --reload

# Terminal 2: Frontend
cd web && npm run dev

# Terminal 3: Ollama
ollama serve
```

### 3. Making Changes

- **Follow our [Code Standards](#-code-standards)**
- **Write or update tests** for your changes
- **Update documentation** as needed
- **Test thoroughly** before submitting

### 4. Pull Request Process

1. **Push your changes** to your fork
2. **Create a Pull Request** with:
   - Clear, descriptive title
   - Detailed description of changes
   - Link to related issues
   - Screenshots (for UI changes)
   - Test results

3. **Respond to feedback** promptly and professionally
4. **Update your PR** based on review comments

## 📋 Code Standards

### Python (Backend)

We follow **PEP 8** with these specific guidelines:

```python
from typing import Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

class ToolResponse(BaseModel):
    """Response model för verktygsexekvering.
    
    Attributes:
        success: Om verktyget kördes framgångsrikt
        message: Beskrivande meddelande på svenska
        data: Valfri data från verktyget
    """
    
    success: bool
    message: str
    data: Optional[Dict] = None
    
    def __str__(self) -> str:
        return f"ToolResponse(success={self.success}, message='{self.message}')"

@router.post("/api/tools/execute")
async def execute_tool(request: ToolRequest) -> ToolResponse:
    """Exekverar specificerat verktyg med valideringskontrollen."""
    try:
        result = await tool_registry.execute(request.tool_name, request.args)
        return ToolResponse(success=True, message="Verktyg exekverat", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verktygsfel: {str(e)}")
```

**Key Requirements:**
- **Type hints** for all function parameters and return values
- **Docstrings** in Swedish using Google style
- **Error handling** with descriptive Swedish messages
- **Pydantic models** for API request/response validation

### TypeScript/JavaScript (Frontend)

We use **ESLint** and **Prettier** with these standards:

```typescript
interface VoiceCommandResponse {
  intent: string;
  confidence: number;
  slots: Record<string, any>;
  processed_at: string;
}

export function classifySwedishIntent(text: string): VoiceCommandResponse | null {
  /**
   * Klassificerar svensk röstinput till intent och slots.
   * 
   * @param text - Svensk text från röstinput
   * @returns Klassificerat intent eller null om okänt
   */
  const cleanText = text.toLowerCase().trim();
  
  // Svenska kalendermönster
  const calendarPatterns = [
    /boka (möte|träff) (.+)/,
    /visa (kalender|schemat)/,
    /vad har jag (.+)/
  ];
  
  for (const [index, pattern] of calendarPatterns.entries()) {
    const match = pattern.exec(cleanText);
    if (match) {
      return {
        intent: "CALENDAR_COMMAND",
        confidence: 0.95,
        slots: { action: match[1], details: match[2] || "" },
        processed_at: new Date().toISOString()
      };
    }
  }
  
  return null;
}
```

**Key Requirements:**
- **TypeScript** for type safety
- **Descriptive interfaces** for all data structures
- **JSDoc comments** in Swedish for complex functions
- **Error boundaries** for React components
- **Responsive design** with mobile-first approach

### Git Commit Messages

We follow **Conventional Commits** with Swedish context:

```bash
# Feature additions
feat: lägg till svensk röstnavigering för kalender
feat(voice): implementera wake-word detektion "Hej Alice"

# Bug fixes  
fix: åtgärda timezone-problem i svenska kalendern
fix(api): korrigera svenska teckenkonvertering

# Documentation
docs: uppdatera CONTRIBUTING.md med svenska exempel
docs(api): förbättra Swedish NLU dokumentation

# Refactoring
refactor: omstrukturera voice pipeline för bättre prestanda
refactor(core): förenkla svensk intent-klassificering

# Tests
test: lägg till tester för svenska datum-parsing
test(e2e): implementera voice command integration tests

# Chores
chore: uppdatera dependencies till senaste versioner
chore(deps): bump ollama version för bättre svenska support
```

## 🧪 Testing Requirements

### Running Tests

```bash
# Backend tests
cd server
python -m pytest tests/ -v --cov=. --cov-report=html

# Specific test categories
python -m pytest tests/test_agent_core_integration.py    # Agent workflows
python -m pytest tests/test_voice_system.py              # Voice pipeline  
python -m pytest tests/test_harmony_adapter.py           # AI integration
python -m pytest tests/test_router_commands.py           # NLU accuracy

# Frontend tests
cd web
npm test
npm run test:e2e
```

### Test Coverage Requirements

- **New features**: Must include comprehensive unit tests
- **Bug fixes**: Must include regression tests
- **API endpoints**: Must include integration tests
- **Swedish language features**: Must include language-specific tests
- **Voice features**: Must include audio processing tests

### Writing Tests

**Backend Test Example:**
```python
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_swedish_calendar_voice_command():
    """Testar svensk kalender röstkommando med NLU."""
    response = client.post("/api/voice/process", json={
        "text": "boka möte imorgon klockan tretton",
        "language": "sv-SE"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "CALENDAR_CREATE"
    assert "imorgon" in data["slots"]["date"]
    assert "13:00" in data["slots"]["time"]
```

**Frontend Test Example:**
```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { VoiceBox } from '@/components/VoiceBox';

describe('VoiceBox Component', () => {
  test('renders with Swedish voice prompt', () => {
    render(<VoiceBox allowDemo={true} />);
    
    expect(screen.getByText(/Tryck för att börja prata/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Starta mic/i })).toBeInTheDocument();
  });

  test('processes Swedish voice input correctly', async () => {
    const mockCallback = jest.fn();
    render(<VoiceBox onVoiceInput={mockCallback} />);
    
    // Simulate voice input
    const micButton = screen.getByRole('button', { name: /Starta mic/i });
    fireEvent.click(micButton);
    
    // Verify Swedish processing
    expect(mockCallback).toHaveBeenCalledWith(
      expect.stringContaining('svenska')
    );
  });
});
```

## 🐛 Issue Reporting Guidelines

### Before Reporting

1. **Search existing issues** to avoid duplicates
2. **Test with latest version** of Alice
3. **Check documentation** ([DEVELOPMENT.md](DEVELOPMENT.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md))
4. **Try reproducing** in different environments

### Bug Report Template

```markdown
**🐛 Bug Description**
Clear description of what went wrong

**🔄 Steps to Reproduce**
1. Go to '...'
2. Click on '...'
3. Enter svenska text '...'
4. See error

**✅ Expected Behavior**
What should happen

**❌ Actual Behavior**
What actually happened

**🖥️ Environment**
- OS: [e.g., macOS 14.0]
- Browser: [e.g., Chrome 120]
- Alice Version: [e.g., v1.2.0]
- Python Version: [e.g., 3.11]
- Node.js Version: [e.g., 18.17]

**📸 Screenshots**
If applicable, add screenshots

**📋 Additional Context**
- Swedish language specific issues
- Voice processing problems
- Calendar/Gmail integration issues
- Console errors or logs
```

### Feature Request Process

1. **Start a Discussion** in [GitHub Discussions](https://github.com/DanielWarg/Alice/discussions)
2. **Explain the use case** clearly
3. **Consider Swedish language implications**
4. **Provide implementation ideas** if possible
5. **Wait for community feedback** before creating formal issue

## 🇸🇪 Swedish Language Contributions

Alice's Swedish language processing is critical to its success. We especially welcome contributions from native Swedish speakers.

### Language Areas Needing Help

- **Intent Classification**: Improving accuracy for Swedish commands
- **Voice Commands**: Adding natural Swedish expressions
- **Regional Dialects**: Supporting different Swedish regions
- **Cultural Context**: Understanding Swedish communication patterns
- **Error Messages**: Natural Swedish error handling
- **Documentation**: Swedish user guides and tutorials

### Swedish Language Guidelines

- **Natural Expressions**: Use everyday Swedish, not translations
- **Regional Awareness**: Consider Stockholm, Göteborg, and Malmö variants
- **Cultural Context**: Understand "lagom", "fika", and Swedish workplace culture
- **Grammar Accuracy**: Proper Swedish grammar and syntax
- **Voice Patterns**: Swedish intonation and speech patterns

Example of good Swedish language contribution:
```python
# Good: Natural Swedish expressions
calendar_patterns = [
    r"boka (möte|träff) (.+)",
    r"visa (mitt schema|min kalender)",
    r"vad har jag på gång (.+)",
    r"har jag något (.+)",
    r"är jag ledig (.+)"
]

# Avoid: Direct translations from English
# calendar_patterns = [
#     r"schemalägg möte (.+)",  # Too formal
#     r"visa kalender"          # Too literal
# ]
```

## 🎨 Design & UX Contributions

### Design Philosophy

Alice follows a **futuristic glassmorphism** aesthetic with:
- **Cyan/blue color palette** (#00d4ff primary)
- **Transparent backgrounds** with blur effects
- **Subtle animations** and micro-interactions
- **Mobile-first responsive design**
- **Accessibility compliance** (WCAG 2.1 AA)

### UI/UX Guidelines

- **Swedish User Experience**: Design for Swedish users and workflows
- **Voice-First Interface**: Prioritize voice interaction design
- **Real-time Feedback**: Immediate visual feedback for voice commands
- **Dark Mode Support**: Professional dark interface
- **Progressive Web App**: Mobile app-like experience

## 🏆 Recognition & Rewards

We believe in recognizing our contributors! Outstanding contributions receive:

### 🌟 Contributor Levels

**🥉 Bronze Contributors**
- First merged PR
- GitHub profile badge
- Welcome package with Alice stickers

**🥈 Silver Contributors**  
- 5+ merged PRs or significant feature
- Priority support channel access
- Featured in release notes
- Alice t-shirt

**🥇 Gold Contributors**
- 10+ merged PRs or major feature
- Direct access to maintainer team
- Alice hoodie and exclusive merchandise
- Annual contributor video call

**💎 Diamond Contributors**
- Sustained contributions over 6+ months
- Core team consideration
- Conference speaking opportunities
- Custom Alice swag

### 🎯 Special Recognition

- **🇸🇪 Swedish Language Champion**: Outstanding Swedish language contributions
- **🎤 Voice Pioneer**: Advancing Alice's voice capabilities  
- **🔒 Security Guardian**: Significant security improvements
- **📚 Documentation Hero**: Exceptional documentation contributions
- **🧪 Test Master**: Comprehensive testing contributions

## 📞 Getting Help

### Community Support Channels

| 💬 Channel | 🎯 Best For | ⚡ Response Time |
|-----------|-------------|-----------------|
| **[GitHub Issues](https://github.com/DanielWarg/Alice/issues)** | Bug reports, feature requests | 24-48 hours |
| **[GitHub Discussions](https://github.com/DanielWarg/Alice/discussions)** | General questions, ideas | 12-24 hours |
| **[Discord Community](https://discord.gg/alice-ai)** | Real-time help, chat | Minutes to hours |
| **[Documentation](DEVELOPMENT.md)** | Setup guides, API docs | Instant |

### Mentor Program

New contributors can request a mentor for:
- **Code Review Support**: Detailed feedback on your contributions
- **Architecture Guidance**: Understanding Alice's design patterns
- **Swedish Language Help**: Native speaker guidance
- **Career Development**: Open source contribution strategies

## 📜 Code of Conduct

This project adheres to our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to maintain a welcoming, inclusive, and professional environment for all community members.

## 🔒 Security

For security-related contributions, please review our [Security Policy](SECURITY.md). Never discuss security vulnerabilities in public issues or discussions.

## 📄 License

By contributing to Alice, you agree that your contributions will be licensed under the [MIT License](LICENSE) that covers the project.

---

## 🚀 Ready to Contribute?

1. **⭐ Star the repository** to show your support
2. **🍴 Fork the project** to your GitHub account  
3. **📖 Read the [Development Guide](DEVELOPMENT.md)** for technical details
4. **💬 Join our [Discord](https://discord.gg/alice-ai)** to connect with the community
5. **🔧 Pick an issue** from our [Good First Issues](https://github.com/DanielWarg/Alice/labels/good%20first%20issue)

**Tack så mycket for helping build the future of Swedish AI! 🇸🇪**

---

*Together, we're creating something revolutionary. Your contribution, no matter how small, helps make Alice better for Swedish users worldwide.*

**Built with ❤️ by developers worldwide, optimized for Swedish users.**