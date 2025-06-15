#!/bin/bash
# ComfyUI Model Resolver Deployment Script

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default values
INSTALL_DIR="/workspace/comfyui-model-resolver"
SKIP_DEPS=false
UPDATE_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --update)
            UPDATE_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --install-dir DIR    Installation directory (default: $INSTALL_DIR)"
            echo "  --skip-deps          Skip dependency installation"
            echo "  --update             Update existing installation only"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}ComfyUI Model Resolver Deployment${NC}"
echo "=================================="

# Check if running on RunPod
if [ ! -d "/workspace" ]; then
    echo -e "${YELLOW}Warning: /workspace not found. This script is designed for RunPod environments.${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create installation directory
if [ ! "$UPDATE_ONLY" = true ]; then
    echo -e "${GREEN}Creating installation directory...${NC}"
    mkdir -p "$INSTALL_DIR"
fi

# Copy files
echo -e "${GREEN}Copying files...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Copy only necessary files
cp -r "$PROJECT_ROOT/src" "$INSTALL_DIR/"
cp -r "$PROJECT_ROOT/scripts" "$INSTALL_DIR/"
cp -r "$PROJECT_ROOT/config" "$INSTALL_DIR/"
cp "$PROJECT_ROOT/requirements.txt" "$INSTALL_DIR/"
cp "$PROJECT_ROOT/README.md" "$INSTALL_DIR/"

# Make scripts executable
chmod +x "$INSTALL_DIR/scripts/"*.py
chmod +x "$INSTALL_DIR/scripts/"*.sh

# Install dependencies
if [ "$SKIP_DEPS" = false ]; then
    echo -e "${GREEN}Installing Python dependencies...${NC}"
    
    # Check if in virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        echo -e "${YELLOW}Not in virtual environment. Installing to user directory...${NC}"
        pip install --user -r "$INSTALL_DIR/requirements.txt"
    else
        pip install -r "$INSTALL_DIR/requirements.txt"
    fi
else
    echo -e "${YELLOW}Skipping dependency installation${NC}"
fi

# Update configuration paths
echo -e "${GREEN}Updating configuration...${NC}"
CONFIG_FILE="$INSTALL_DIR/config/default_config.yaml"

# Update paths in config to use RunPod defaults
sed -i 's|comfyui_base:.*|comfyui_base: "/workspace/ComfyUI"|' "$CONFIG_FILE"
sed -i 's|models_base:.*|models_base: "/workspace/ComfyUI/models"|' "$CONFIG_FILE"

# Create convenience script
echo -e "${GREEN}Creating convenience script...${NC}"
cat > "$INSTALL_DIR/resolver" << 'EOF'
#!/bin/bash
# Convenience wrapper for ComfyUI Model Resolver

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$SCRIPT_DIR/scripts/model_resolver.py" "$@"
EOF

chmod +x "$INSTALL_DIR/resolver"

# Create symlink in /usr/local/bin if possible
if [ -w "/usr/local/bin" ]; then
    ln -sf "$INSTALL_DIR/resolver" /usr/local/bin/comfyui-resolver
    echo -e "${GREEN}Created global command: comfyui-resolver${NC}"
else
    echo -e "${YELLOW}Note: Could not create global command. Use: $INSTALL_DIR/resolver${NC}"
fi

# Test installation
echo -e "${GREEN}Testing installation...${NC}"
if python "$INSTALL_DIR/scripts/model_resolver.py" --help > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Installation successful!${NC}"
else
    echo -e "${RED}✗ Installation test failed${NC}"
    exit 1
fi

# Show usage
echo
echo -e "${GREEN}Installation completed!${NC}"
echo
echo "Usage examples:"
echo "  # Analyze workflow"
echo "  $INSTALL_DIR/resolver analyze /path/to/workflow.json"
echo
echo "  # Check and download missing models"
echo "  $INSTALL_DIR/resolver resolve /path/to/workflow.json"
echo
echo "  # Check models without downloading"
echo "  $INSTALL_DIR/resolver check /path/to/workflow.json"
echo
echo "For more commands, run:"
echo "  $INSTALL_DIR/resolver --help"

# Create uninstall script
cat > "$INSTALL_DIR/uninstall.sh" << EOF
#!/bin/bash
# Uninstall ComfyUI Model Resolver

echo "Removing ComfyUI Model Resolver..."
rm -rf "$INSTALL_DIR"
rm -f /usr/local/bin/comfyui-resolver
echo "Uninstall complete."
EOF

chmod +x "$INSTALL_DIR/uninstall.sh"

echo
echo -e "${YELLOW}To uninstall, run: $INSTALL_DIR/uninstall.sh${NC}"