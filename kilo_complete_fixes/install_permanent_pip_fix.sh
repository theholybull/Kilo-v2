#!/bin/bash

# PERMANENT FIX for Debian Trixie pip issues
# Creates wrappers that enforce virtual environment usage

set -e

echo "🔧 Installing PERMANENT fix for Debian Trixie pip issues..."

# Create pip wrapper that ONLY works in venv
echo "📦 Creating kilo-pip wrapper..."
sudo tee /usr/local/bin/kilo-pip > /dev/null <<'EOF'
#!/bin/bash
# Kilo Truck pip wrapper - enforces virtual environment usage

if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ ERROR: Must be in virtual environment to use kilo-pip"
    echo ""
    echo "Activate venv first:"
    echo "  source /opt/kilo/venv/bin/activate"
    echo ""
    echo "Or use venv pip directly:"
    echo "  /opt/kilo/venv/bin/pip $*"
    exit 1
fi

# Use venv pip
/opt/kilo/venv/bin/pip "$@"
EOF

sudo chmod +x /usr/local/bin/kilo-pip

# Create python wrapper that defaults to venv
echo "🐍 Creating kilo-python wrapper..."
sudo tee /usr/local/bin/kilo-python > /dev/null <<'EOF'
#!/bin/bash
# Kilo Truck python wrapper - defaults to venv python

# If venv exists, use it
if [[ -x "/opt/kilo/venv/bin/python" ]]; then
    /opt/kilo/venv/bin/python "$@"
else
    # Fall back to system python with warning
    echo "⚠️  WARNING: Using system python - venv not found"
    /usr/bin/python3 "$@"
fi
EOF

sudo chmod +x /usr/local/bin/kilo-python

# Ensure venv exists with correct setup
echo "🏗️ Setting up virtual environment..."
if [ ! -d "/opt/kilo/venv" ]; then
    sudo mkdir -p /opt/kilo
    cd /opt/kilo
    python3-full -m venv venv 2>/dev/null || python3 -m venv venv
fi

# Activate and upgrade pip
echo "📦 Upgrading pip in venv..."
/opt/kilo/venv/bin/pip install --upgrade pip setuptools wheel

echo ""
echo "✅ PERMANENT fix installed!"
echo ""
echo "Usage examples:"
echo "  kilo-pip install requests    # Only works in venv"
echo "  kilo-python script.py        # Uses venv python"
echo "  source /opt/kilo/venv/bin/activate  # Activate venv"
echo ""
echo "Testing:"
echo "  kilo-pip list  # Should fail (not in venv)"
echo "  source /opt/kilo/venv/bin/activate"
echo "  kilo-pip list  # Should work (in venv)"
echo ""
echo "This fix prevents all future pip installation errors on Trixie!"