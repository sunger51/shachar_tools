#!/bin/bash
# Git Workflow Helper - Automate common git operations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_usage() {
    echo "Git Workflow Helper"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  sync          Pull latest changes and rebase current branch"
    echo "  cleanup       Delete merged branches (local and remote)"
    echo "  status        Show enhanced git status with branch info"
    echo "  commit        Interactive commit with conventional commit format"
    echo "  branch        Create and checkout new branch from main/master"
    echo ""
    echo "Examples:"
    echo "  $0 sync"
    echo "  $0 cleanup"
    echo "  $0 branch feature/new-feature"
    echo "  $0 commit"
}

function get_default_branch() {
    # Try to determine the default branch (main or master)
    if git show-ref --verify --quiet refs/heads/main; then
        echo "main"
    elif git show-ref --verify --quiet refs/heads/master; then
        echo "master"
    else
        echo "main"  # Default to main
    fi
}

function sync_branch() {
    echo -e "${YELLOW}Syncing with remote...${NC}"
    
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    default_branch=$(get_default_branch)
    
    # Fetch latest changes
    git fetch --all --prune
    
    # Stash any local changes
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}Stashing local changes...${NC}"
        git stash save "Auto-stash by git_workflow helper"
        stashed=true
    else
        stashed=false
    fi
    
    # If on default branch, pull, otherwise rebase
    if [ "$current_branch" = "$default_branch" ]; then
        git pull origin "$default_branch"
    else
        git pull --rebase origin "$current_branch" || true
    fi
    
    # Pop stash if we stashed
    if [ "$stashed" = true ]; then
        echo -e "${YELLOW}Restoring stashed changes...${NC}"
        git stash pop
    fi
    
    echo -e "${GREEN}Sync complete!${NC}"
}

function cleanup_branches() {
    echo -e "${YELLOW}Cleaning up merged branches...${NC}"
    
    default_branch=$(get_default_branch)
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    
    # Switch to default branch if not already there
    if [ "$current_branch" != "$default_branch" ]; then
        git checkout "$default_branch"
    fi
    
    # Pull latest changes
    git pull origin "$default_branch"
    
    # Delete local branches that have been merged
    merged_branches=$(git branch --merged | grep -v "\*\|$default_branch\|main\|master\|develop" || true)
    
    if [ -n "$merged_branches" ]; then
        echo "$merged_branches" | xargs -n 1 git branch -d
        echo -e "${GREEN}Deleted local merged branches${NC}"
    else
        echo -e "${YELLOW}No local branches to delete${NC}"
    fi
    
    # Prune remote branches
    git remote prune origin
    
    echo -e "${GREEN}Cleanup complete!${NC}"
}

function enhanced_status() {
    echo -e "${YELLOW}=== Git Status ===${NC}"
    
    # Current branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    echo -e "Branch: ${GREEN}$current_branch${NC}"
    
    # Remote tracking
    upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "No upstream")
    echo -e "Upstream: $upstream"
    
    # Commits ahead/behind
    if [ "$upstream" != "No upstream" ]; then
        ahead=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "0")
        behind=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo "0")
        echo -e "Ahead: $ahead | Behind: $behind"
    fi
    
    echo ""
    
    # Standard git status
    git status
}

function interactive_commit() {
    echo -e "${YELLOW}=== Interactive Commit ===${NC}"
    echo ""
    echo "Select commit type:"
    echo "1. feat     - New feature"
    echo "2. fix      - Bug fix"
    echo "3. docs     - Documentation changes"
    echo "4. style    - Code style changes (formatting, etc.)"
    echo "5. refactor - Code refactoring"
    echo "6. test     - Adding or updating tests"
    echo "7. chore    - Maintenance tasks"
    echo ""
    read -p "Enter choice (1-7): " choice
    
    case $choice in
        1) type="feat" ;;
        2) type="fix" ;;
        3) type="docs" ;;
        4) type="style" ;;
        5) type="refactor" ;;
        6) type="test" ;;
        7) type="chore" ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac
    
    read -p "Enter commit scope (optional, press enter to skip): " scope
    read -p "Enter commit message: " message
    
    if [ -n "$scope" ]; then
        commit_msg="$type($scope): $message"
    else
        commit_msg="$type: $message"
    fi
    
    echo ""
    echo -e "Commit message: ${GREEN}$commit_msg${NC}"
    read -p "Proceed with commit? (y/n): " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        git commit -m "$commit_msg"
        echo -e "${GREEN}Committed!${NC}"
    else
        echo -e "${RED}Commit cancelled${NC}"
        exit 1
    fi
}

function create_branch() {
    if [ -z "$1" ]; then
        echo -e "${RED}Error: Branch name required${NC}"
        echo "Usage: $0 branch <branch-name>"
        exit 1
    fi
    
    branch_name=$1
    default_branch=$(get_default_branch)
    
    echo -e "${YELLOW}Creating branch '$branch_name' from '$default_branch'...${NC}"
    
    # Ensure we're on default branch and up to date
    git checkout "$default_branch"
    git pull origin "$default_branch"
    
    # Create and checkout new branch
    git checkout -b "$branch_name"
    
    echo -e "${GREEN}Branch '$branch_name' created and checked out!${NC}"
}

# Main script logic
if [ $# -eq 0 ]; then
    print_usage
    exit 1
fi

command=$1
shift

case $command in
    sync)
        sync_branch
        ;;
    cleanup)
        cleanup_branches
        ;;
    status)
        enhanced_status
        ;;
    commit)
        interactive_commit
        ;;
    branch)
        create_branch "$@"
        ;;
    *)
        echo -e "${RED}Unknown command: $command${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac
