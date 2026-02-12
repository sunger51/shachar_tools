# shachar_tools

A collection of useful scripts and tools for daily work, including file management, system monitoring, git workflow automation, and development environment setup.

## 📋 Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Python Scripts](#python-scripts)
- [Shell Scripts](#shell-scripts)
- [Usage Examples](#usage-examples)
- [Requirements](#requirements)

## 🎯 Overview

This repository contains practical tools to automate and simplify common daily tasks:

- **File Management**: Organize and backup files efficiently
- **System Monitoring**: Get quick system information and resource usage
- **Git Workflow**: Automate common git operations
- **Development Setup**: Quick environment setup for various languages
- **Log Analysis**: Search and analyze log files

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/sunger51/shachar_tools.git
cd shachar_tools
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Make scripts executable (if not already):
```bash
chmod +x scripts/python/*.py
chmod +x scripts/shell/*.sh
```

4. Optionally, add scripts to your PATH:
```bash
export PATH="$PATH:$(pwd)/scripts/python:$(pwd)/scripts/shell"
# Add to your ~/.bashrc or ~/.zshrc to make it permanent
```

## 🐍 Python Scripts

### file_organizer.py

Organize cluttered directories by grouping files based on extension or modification date.

**Features:**
- Organize by file extension (default)
- Organize by modification date (year/month)
- Automatic conflict resolution
- Skip hidden files

**Usage:**
```bash
# Organize by extension
./scripts/python/file_organizer.py /path/to/directory

# Organize by date
./scripts/python/file_organizer.py /path/to/directory --mode date
```

### backup_utility.py

Create compressed backups with automatic rotation.

**Features:**
- Multiple compression formats (tar.gz, zip)
- Timestamped backups
- Automatic backup rotation
- Progress reporting

**Usage:**
```bash
# Create tar.gz backup
./scripts/python/backup_utility.py /source/path /backup/destination

# Create zip backup with custom rotation
./scripts/python/backup_utility.py /source/path /backup/destination --format zip --max-backups 10
```

### system_info.py

Display comprehensive system information and resource usage.

**Features:**
- System and hardware info
- CPU usage and frequency
- Memory and swap usage
- Disk space information
- Network interfaces

**Usage:**
```bash
./scripts/python/system_info.py
```

## 🐚 Shell Scripts

### git_workflow.sh

Automate common git operations with best practices.

**Features:**
- Sync branches with automatic stashing
- Clean up merged branches
- Enhanced status display
- Interactive conventional commits
- Branch creation from default branch

**Usage:**
```bash
# Sync current branch
./scripts/shell/git_workflow.sh sync

# Clean up merged branches
./scripts/shell/git_workflow.sh cleanup

# Enhanced status
./scripts/shell/git_workflow.sh status

# Interactive commit
./scripts/shell/git_workflow.sh commit

# Create new branch
./scripts/shell/git_workflow.sh branch feature/new-feature
```

### dev_setup.sh

Setup development environments with common tools.

**Features:**
- Node.js setup (nvm, node, npm, yarn)
- Python setup (pyenv, pip, virtualenv)
- Docker and Docker Compose installation
- Git configuration with aliases
- OS-aware installation (Linux/macOS)

**Usage:**
```bash
# Setup Node.js environment
./scripts/shell/dev_setup.sh node

# Setup Python environment
./scripts/shell/dev_setup.sh python

# Setup Docker
./scripts/shell/dev_setup.sh docker

# Configure git
./scripts/shell/dev_setup.sh git

# Setup everything
./scripts/shell/dev_setup.sh all
```

### log_analyzer.sh

Search and analyze log files efficiently.

**Features:**
- Find errors and warnings
- Pattern search
- Log statistics
- Time-based filtering
- Tail with custom line count

**Usage:**
```bash
# Find all errors
./scripts/shell/log_analyzer.sh errors /var/log/app.log

# Find warnings
./scripts/shell/log_analyzer.sh warnings /var/log/app.log

# Search for pattern
./scripts/shell/log_analyzer.sh search /var/log/app.log "connection timeout"

# Show last 100 lines
./scripts/shell/log_analyzer.sh tail /var/log/app.log 100

# Show statistics
./scripts/shell/log_analyzer.sh stats /var/log/app.log
```

## 💡 Usage Examples

### Example 1: Organize Downloads Folder
```bash
./scripts/python/file_organizer.py ~/Downloads --mode extension
```

### Example 2: Daily Project Backup
```bash
./scripts/python/backup_utility.py ~/projects ~/backups --max-backups 7
```

### Example 3: Quick System Check
```bash
./scripts/python/system_info.py
```

### Example 4: Git Workflow
```bash
# Start new feature
./scripts/shell/git_workflow.sh branch feature/awesome-feature

# Make changes, then commit
./scripts/shell/git_workflow.sh commit

# Sync with remote
./scripts/shell/git_workflow.sh sync
```

### Example 5: Setup New Development Machine
```bash
./scripts/shell/dev_setup.sh all
```

### Example 6: Analyze Application Logs
```bash
./scripts/shell/log_analyzer.sh stats /var/log/app.log
./scripts/shell/log_analyzer.sh errors /var/log/app.log
```

## 📋 Requirements

### Python Scripts
- Python 3.6+
- psutil (for system_info.py)

Install Python dependencies:
```bash
pip install -r requirements.txt
```

### Shell Scripts
- Bash 4.0+
- Git (for git_workflow.sh)
- curl (for dev_setup.sh)
- Standard Unix utilities (grep, awk, etc.)

## 🤝 Contributing

Feel free to open issues or submit pull requests with improvements!

## 📄 License

This project is open source and available for personal and commercial use.

## 🔧 Troubleshooting

### Permission Denied
If you get permission denied errors, make sure scripts are executable:
```bash
chmod +x scripts/python/*.py scripts/shell/*.sh
```

### Python Module Not Found
Install required Python packages:
```bash
pip install -r requirements.txt
```

### Command Not Found
Either use the full path to scripts or add them to your PATH:
```bash
export PATH="$PATH:$(pwd)/scripts/python:$(pwd)/scripts/shell"
```

## 📞 Support

For issues, questions, or suggestions, please open an issue on GitHub.