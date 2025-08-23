#!/bin/bash
# Alice AI Assistant - Development Environment Setup Script
# Installs and configures pre-commit hooks and development dependencies

set -e

echo "🚀 Setting up Alice AI development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "Makefile" ] || [ ! -f ".pre-commit-config.yaml" ]; then
    print_error "Please run this script from the Alice AI project root directory"
    exit 1
fi

print_status "Installing Python development dependencies..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment and install dependencies
source .venv/bin/activate
pip install --upgrade pip

# Install development requirements
if [ -f "server/requirements-dev.txt" ]; then
    pip install -r server/requirements-dev.txt
else
    print_warning "server/requirements-dev.txt not found, installing basic dev tools..."
    pip install -r server/requirements.txt
    pip install ruff black mypy pytest-cov pytest-xdist pre-commit
fi

print_success "Python dependencies installed"

print_status "Installing Node.js dependencies..."

# Install web dependencies
if [ -d "web" ]; then
    print_status "Installing web frontend dependencies..."
    cd web && npm install && cd ..
    print_success "Web dependencies installed"
fi

# Install alice-tools dependencies
if [ -d "alice-tools" ]; then
    print_status "Installing alice-tools dependencies..."
    cd alice-tools && npm install && cd ..
    print_success "Alice-tools dependencies installed"
fi

# Install nlu-agent dependencies
if [ -d "nlu-agent" ]; then
    print_status "Installing nlu-agent dependencies..."
    cd nlu-agent && npm install && cd ..
    print_success "NLU-agent dependencies installed"
fi

print_status "Setting up pre-commit hooks..."

# Install pre-commit hooks
pre-commit install
pre-commit install --hook-type pre-push

print_success "Pre-commit hooks installed"

print_status "Running initial code quality checks..."

# Run pre-commit on all files to catch any existing issues
print_status "Running pre-commit on all files (this may take a moment)..."
if pre-commit run --all-files; then
    print_success "All code quality checks passed!"
else
    print_warning "Some code quality issues found. Please review and fix them."
    print_status "You can run 'make format' to auto-fix many issues."
fi

print_success "✅ Development environment setup complete!"

echo ""
echo "🎯 Next steps:"
echo "   1. Run 'make dev' to start development servers"
echo "   2. Run 'make test' to run all tests"
echo "   3. Run 'make lint' to check code quality"
echo "   4. Run 'make format' to auto-format code"
echo ""
echo "📚 Useful commands:"
echo "   - make help        # Show all available commands"
echo "   - make check       # Run comprehensive quality checks"
echo "   - make clean       # Clean build artifacts"
echo ""
echo "🔧 Pre-commit hooks are now active and will run automatically on git commit!"