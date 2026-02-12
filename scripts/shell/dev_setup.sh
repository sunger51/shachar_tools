#!/bin/bash
# Development Environment Setup - Setup common development tools and environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_usage() {
    echo "Development Environment Setup"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  node          Setup Node.js environment (nvm, node, npm, yarn)"
    echo "  python        Setup Python environment (pyenv, pip, virtualenv)"
    echo "  docker        Setup Docker and Docker Compose"
    echo "  git           Configure git with best practices"
    echo "  all           Setup everything"
    echo ""
    echo "Examples:"
    echo "  $0 node"
    echo "  $0 python"
    echo "  $0 all"
}

function check_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

function setup_node() {
    echo -e "${BLUE}=== Setting up Node.js environment ===${NC}"
    
    # Check if nvm is installed
    if [ ! -d "$HOME/.nvm" ]; then
        echo -e "${YELLOW}Installing nvm...${NC}"
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    else
        echo -e "${GREEN}nvm already installed${NC}"
    fi
    
    # Install latest LTS Node.js
    if command -v nvm &> /dev/null; then
        echo -e "${YELLOW}Installing Node.js LTS...${NC}"
        nvm install --lts
        nvm use --lts
    fi
    
    # Install global packages
    if command -v npm &> /dev/null; then
        echo -e "${YELLOW}Installing global npm packages...${NC}"
        npm install -g yarn pnpm typescript ts-node eslint prettier
    fi
    
    echo -e "${GREEN}Node.js setup complete!${NC}"
}

function setup_python() {
    echo -e "${BLUE}=== Setting up Python environment ===${NC}"
    
    os=$(check_os)
    
    # Install pyenv
    if [ ! -d "$HOME/.pyenv" ]; then
        echo -e "${YELLOW}Installing pyenv...${NC}"
        curl https://pyenv.run | bash
        
        # Add to shell configuration
        echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
        echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
        echo 'eval "$(pyenv init -)"' >> ~/.bashrc
        
        export PYENV_ROOT="$HOME/.pyenv"
        export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)"
    else
        echo -e "${GREEN}pyenv already installed${NC}"
    fi
    
    # Install Python dependencies
    if [ "$os" = "linux" ]; then
        echo -e "${YELLOW}Installing Python build dependencies...${NC}"
        sudo apt-get update
        sudo apt-get install -y build-essential libssl-dev zlib1g-dev \
            libbz2-dev libreadline-dev libsqlite3-dev curl \
            libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
            libffi-dev liblzma-dev
    fi
    
    # Install pip packages
    if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
        echo -e "${YELLOW}Installing common Python packages...${NC}"
        pip3 install --user virtualenv pipenv black pylint flake8 pytest ipython || \
        pip install --user virtualenv pipenv black pylint flake8 pytest ipython
    fi
    
    echo -e "${GREEN}Python setup complete!${NC}"
}

function setup_docker() {
    echo -e "${BLUE}=== Setting up Docker ===${NC}"
    
    os=$(check_os)
    
    if [ "$os" = "linux" ]; then
        # Check if docker is installed
        if ! command -v docker &> /dev/null; then
            echo -e "${YELLOW}Installing Docker...${NC}"
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            rm get-docker.sh
        else
            echo -e "${GREEN}Docker already installed${NC}"
        fi
        
        # Install docker-compose
        if ! command -v docker-compose &> /dev/null; then
            echo -e "${YELLOW}Installing Docker Compose...${NC}"
            sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
        else
            echo -e "${GREEN}Docker Compose already installed${NC}"
        fi
    elif [ "$os" = "macos" ]; then
        echo -e "${YELLOW}Please install Docker Desktop for Mac from: https://www.docker.com/products/docker-desktop${NC}"
    fi
    
    echo -e "${GREEN}Docker setup complete!${NC}"
    echo -e "${YELLOW}Note: You may need to log out and back in for group changes to take effect${NC}"
}

function setup_git() {
    echo -e "${BLUE}=== Configuring Git ===${NC}"
    
    # Set up git config
    read -p "Enter your Git name: " git_name
    read -p "Enter your Git email: " git_email
    
    git config --global user.name "$git_name"
    git config --global user.email "$git_email"
    
    # Set up useful aliases
    echo -e "${YELLOW}Setting up Git aliases...${NC}"
    git config --global alias.co checkout
    git config --global alias.br branch
    git config --global alias.ci commit
    git config --global alias.st status
    git config --global alias.unstage 'reset HEAD --'
    git config --global alias.last 'log -1 HEAD'
    git config --global alias.lg "log --color --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit"
    
    # Set default branch name
    git config --global init.defaultBranch main
    
    # Set pull strategy
    git config --global pull.rebase false
    
    # Set up diff and merge tools
    git config --global merge.conflictstyle diff3
    
    echo -e "${GREEN}Git configuration complete!${NC}"
}

function setup_all() {
    echo -e "${BLUE}=== Setting up complete development environment ===${NC}"
    echo ""
    
    setup_git
    echo ""
    setup_node
    echo ""
    setup_python
    echo ""
    setup_docker
    echo ""
    
    echo -e "${GREEN}=== Complete environment setup finished! ===${NC}"
}

# Main script logic
if [ $# -eq 0 ]; then
    print_usage
    exit 1
fi

command=$1
shift

case $command in
    node)
        setup_node
        ;;
    python)
        setup_python
        ;;
    docker)
        setup_docker
        ;;
    git)
        setup_git
        ;;
    all)
        setup_all
        ;;
    *)
        echo -e "${RED}Unknown command: $command${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac
