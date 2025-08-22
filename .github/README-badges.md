# GitHub Actions Badges for Alice AI Assistant

Copy and paste these badges into your main README.md file to display CI/CD status:

## CI/CD Status Badges

```markdown
<!-- Main CI Pipeline -->
[![CI Pipeline](https://github.com/evil/Alice/actions/workflows/ci.yml/badge.svg)](https://github.com/evil/Alice/actions/workflows/ci.yml)

<!-- Release Pipeline -->
[![Release](https://github.com/evil/Alice/actions/workflows/release.yml/badge.svg)](https://github.com/evil/Alice/actions/workflows/release.yml)

<!-- Security Analysis -->
[![CodeQL](https://github.com/evil/Alice/actions/workflows/codeql.yml/badge.svg)](https://github.com/evil/Alice/actions/workflows/codeql.yml)

<!-- Version Badge -->
![Version](https://img.shields.io/github/v/release/evil/Alice)

<!-- License -->
![License](https://img.shields.io/github/license/evil/Alice)
```

## Detailed Status Badges

```markdown
<!-- Python CI -->
[![Python CI](https://github.com/evil/Alice/actions/workflows/ci.yml/badge.svg?event=push)](https://github.com/evil/Alice/actions/workflows/ci.yml)

<!-- Web Frontend CI -->
[![Web CI](https://github.com/evil/Alice/actions/workflows/ci.yml/badge.svg?event=push)](https://github.com/evil/Alice/actions/workflows/ci.yml)

<!-- Code Coverage -->
[![codecov](https://codecov.io/gh/evil/Alice/branch/main/graph/badge.svg)](https://codecov.io/gh/evil/Alice)

<!-- Dependabot -->
[![Dependabot Status](https://api.dependabot.com/badges/status?host=github&repo=evil/Alice)](https://dependabot.com)
```

## Technology Stack Badges

```markdown
<!-- Tech Stack -->
![Python](https://img.shields.io/badge/python-v3.9+-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-v18+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-black?style=flat&logo=next.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=flat&logo=typescript&logoColor=white)
![React](https://img.shields.io/badge/react-%2320232a.svg?style=flat&logo=react&logoColor=%2361DAFB)
```

## Docker and Deployment

```markdown
<!-- Docker Images -->
![Docker Backend](https://img.shields.io/badge/docker-backend-blue?logo=docker)
![Docker Frontend](https://img.shields.io/badge/docker-frontend-blue?logo=docker)

<!-- Last Release -->
![GitHub Release Date](https://img.shields.io/github/release-date/evil/Alice)

<!-- Downloads -->
![GitHub Downloads](https://img.shields.io/github/downloads/evil/Alice/total)
```

## Quality and Security

```markdown
<!-- Code Quality -->
![Code Quality](https://img.shields.io/codacy/grade/[CODACY_PROJECT_ID])

<!-- Security Score -->
![Security Score](https://img.shields.io/snyk/vulnerabilities/github/evil/Alice)

<!-- Maintainability -->
![Maintainability](https://api.codeclimate.com/v1/badges/[CODECLIMATE_ID]/maintainability)
```

## Example README Section

Here's how to integrate these badges into your README:

```markdown
# Alice AI Assistant

[![CI Pipeline](https://github.com/evil/Alice/actions/workflows/ci.yml/badge.svg)](https://github.com/evil/Alice/actions/workflows/ci.yml)
[![Release](https://github.com/evil/Alice/actions/workflows/release.yml/badge.svg)](https://github.com/evil/Alice/actions/workflows/release.yml)
[![CodeQL](https://github.com/evil/Alice/actions/workflows/codeql.yml/badge.svg)](https://github.com/evil/Alice/actions/workflows/codeql.yml)
![Version](https://img.shields.io/github/v/release/evil/Alice)
![Python](https://img.shields.io/badge/python-v3.9+-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-v18+-green.svg)

A Swedish AI voice assistant powered by advanced NLP and voice processing.

## Features

- 🎤 Swedish voice recognition and synthesis
- 🤖 AI-powered conversation with Ollama/OpenAI
- 📅 Calendar and Gmail integration
- 🌐 Modern web interface with Next.js
- 🔒 Secure API handling and authentication

## Quick Start

...rest of your README...
```

## Workflow Notifications

The CI/CD pipeline includes:

- ✅ **Matrix Testing**: Python 3.9-3.11, Node.js 18-20
- 🔍 **Code Quality**: Linting, formatting, type checking
- 🛡️ **Security**: Bandit, npm audit, CodeQL analysis
- 📦 **Build**: All components with artifact uploads
- 🚀 **Auto-deployment**: Docker images on release
- 🔄 **Dependency Management**: Automated updates with Dependabot

Replace `evil/Alice` with your actual GitHub repository path when copying these badges.