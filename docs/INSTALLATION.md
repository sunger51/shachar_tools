# Installation Guide

## Prerequisites

### For Python Scripts

1. **Python 3.6 or higher**
   ```bash
   # Check Python version
   python3 --version
   ```

2. **pip (Python package manager)**
   ```bash
   # Check pip version
   pip3 --version
   ```

### For Shell Scripts

1. **Bash 4.0 or higher**
   ```bash
   # Check Bash version
   bash --version
   ```

2. **Git** (for git_workflow.sh)
   ```bash
   # Check Git version
   git --version
   ```

3. **curl** (for dev_setup.sh)
   ```bash
   # Check curl version
   curl --version
   ```

## Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/sunger51/shachar_tools.git
cd shachar_tools
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or for user installation:
```bash
pip install --user -r requirements.txt
```

### Step 3: Make Scripts Executable

```bash
chmod +x scripts/python/*.py
chmod +x scripts/shell/*.sh
```

### Step 4: (Optional) Add to PATH

#### Temporary (Current Session Only)
```bash
export PATH="$PATH:$(pwd)/scripts/python:$(pwd)/scripts/shell"
```

#### Permanent

For **Bash** users, add to `~/.bashrc`:
```bash
echo 'export PATH="$PATH:/path/to/shachar_tools/scripts/python:/path/to/shachar_tools/scripts/shell"' >> ~/.bashrc
source ~/.bashrc
```

For **Zsh** users, add to `~/.zshrc`:
```bash
echo 'export PATH="$PATH:/path/to/shachar_tools/scripts/python:/path/to/shachar_tools/scripts/shell"' >> ~/.zshrc
source ~/.zshrc
```

### Step 5: Verify Installation

Test Python scripts:
```bash
./scripts/python/system_info.py
```

Test shell scripts:
```bash
./scripts/shell/git_workflow.sh
```

## Platform-Specific Notes

### Linux (Ubuntu/Debian)

Install Python and dependencies:
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip git curl
```

### macOS

Install using Homebrew:
```bash
brew install python3 git curl
```

### Windows (WSL)

Follow Linux installation instructions within WSL environment.

## Troubleshooting

### Issue: Python script not found
**Solution**: Use `python3` instead of `python`:
```bash
python3 scripts/python/system_info.py
```

### Issue: Permission denied
**Solution**: Make scripts executable:
```bash
chmod +x scripts/python/*.py scripts/shell/*.sh
```

### Issue: Module 'psutil' not found
**Solution**: Install requirements:
```bash
pip install -r requirements.txt
```

### Issue: Command not found (after adding to PATH)
**Solution**: Restart your terminal or source your shell config:
```bash
source ~/.bashrc  # or ~/.zshrc
```

## Updating

To update to the latest version:
```bash
cd shachar_tools
git pull origin main
pip install -r requirements.txt
```

## Uninstallation

To remove shachar_tools:
```bash
rm -rf /path/to/shachar_tools
```

Remove from PATH by editing your `~/.bashrc` or `~/.zshrc` and removing the export line.
