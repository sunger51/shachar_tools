#!/bin/bash
# Log Analyzer - Analyze and search through log files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_usage() {
    echo "Log Analyzer - Analyze and search through log files"
    echo ""
    echo "Usage: $0 <command> <logfile> [options]"
    echo ""
    echo "Commands:"
    echo "  errors <logfile>              Find all error messages"
    echo "  warnings <logfile>            Find all warning messages"
    echo "  search <logfile> <pattern>    Search for specific pattern"
    echo "  tail <logfile> [lines]        Show last N lines (default: 50)"
    echo "  stats <logfile>               Show log statistics"
    echo "  filter <logfile> <start> <end>  Filter logs by time range"
    echo ""
    echo "Examples:"
    echo "  $0 errors /var/log/syslog"
    echo "  $0 search /var/log/app.log 'connection timeout'"
    echo "  $0 tail /var/log/app.log 100"
    echo "  $0 stats /var/log/app.log"
}

function check_file() {
    if [ ! -f "$1" ]; then
        echo -e "${RED}Error: File '$1' not found${NC}"
        exit 1
    fi
}

function find_errors() {
    local logfile=$1
    check_file "$logfile"
    
    echo -e "${BLUE}=== Errors in $logfile ===${NC}"
    echo ""
    
    # Search for common error patterns
    grep -i -E '(error|exception|fail|fatal|critical)' "$logfile" | \
        grep -v -i 'warning' | \
        tail -50
    
    local count=$(grep -i -c -E '(error|exception|fail|fatal|critical)' "$logfile" | grep -v -i 'warning' || echo "0")
    echo ""
    echo -e "${YELLOW}Total errors found: $count${NC}"
}

function find_warnings() {
    local logfile=$1
    check_file "$logfile"
    
    echo -e "${BLUE}=== Warnings in $logfile ===${NC}"
    echo ""
    
    grep -i 'warn' "$logfile" | tail -50
    
    local count=$(grep -i -c 'warn' "$logfile" || echo "0")
    echo ""
    echo -e "${YELLOW}Total warnings found: $count${NC}"
}

function search_pattern() {
    local logfile=$1
    local pattern=$2
    
    check_file "$logfile"
    
    if [ -z "$pattern" ]; then
        echo -e "${RED}Error: Search pattern required${NC}"
        print_usage
        exit 1
    fi
    
    echo -e "${BLUE}=== Searching for '$pattern' in $logfile ===${NC}"
    echo ""
    
    grep -i "$pattern" "$logfile" | tail -100
    
    local count=$(grep -i -c "$pattern" "$logfile" || echo "0")
    echo ""
    echo -e "${YELLOW}Total matches found: $count${NC}"
}

function tail_log() {
    local logfile=$1
    local lines=${2:-50}
    
    check_file "$logfile"
    
    echo -e "${BLUE}=== Last $lines lines of $logfile ===${NC}"
    echo ""
    
    tail -n "$lines" "$logfile"
}

function show_stats() {
    local logfile=$1
    
    check_file "$logfile"
    
    echo -e "${BLUE}=== Statistics for $logfile ===${NC}"
    echo ""
    
    # File size
    local size=$(du -h "$logfile" | cut -f1)
    echo -e "File size: ${GREEN}$size${NC}"
    
    # Line count
    local lines=$(wc -l < "$logfile")
    echo -e "Total lines: ${GREEN}$lines${NC}"
    
    # Error count
    local errors=$(grep -i -c -E '(error|exception|fail|fatal|critical)' "$logfile" | grep -v -i 'warning' || echo "0")
    echo -e "Errors: ${RED}$errors${NC}"
    
    # Warning count
    local warnings=$(grep -i -c 'warn' "$logfile" || echo "0")
    echo -e "Warnings: ${YELLOW}$warnings${NC}"
    
    # Date range (first and last entries - assumes timestamp at start of line)
    echo ""
    echo -e "${BLUE}Date Range:${NC}"
    echo -n "First entry: "
    head -1 "$logfile" | cut -d' ' -f1-3
    echo -n "Last entry:  "
    tail -1 "$logfile" | cut -d' ' -f1-3
    
    # Top error messages (if any)
    echo ""
    echo -e "${BLUE}Top Error Patterns:${NC}"
    grep -i -E '(error|exception|fail|fatal|critical)' "$logfile" 2>/dev/null | \
        sed 's/.*\(error\|exception\|fail\|fatal\|critical\)[: ]*/\1: /' | \
        cut -d':' -f2 | \
        sort | uniq -c | sort -rn | head -5 || echo "No errors found"
}

function filter_by_time() {
    local logfile=$1
    local start_time=$2
    local end_time=$3
    
    check_file "$logfile"
    
    if [ -z "$start_time" ] || [ -z "$end_time" ]; then
        echo -e "${RED}Error: Start and end time required${NC}"
        echo "Format: YYYY-MM-DD HH:MM:SS"
        exit 1
    fi
    
    echo -e "${BLUE}=== Logs between $start_time and $end_time ===${NC}"
    echo ""
    
    # This is a simple filter - may need adjustment based on log format
    awk -v start="$start_time" -v end="$end_time" \
        '$0 >= start && $0 <= end' "$logfile"
}

# Main script logic
if [ $# -eq 0 ]; then
    print_usage
    exit 1
fi

command=$1
shift

case $command in
    errors)
        find_errors "$@"
        ;;
    warnings)
        find_warnings "$@"
        ;;
    search)
        search_pattern "$@"
        ;;
    tail)
        tail_log "$@"
        ;;
    stats)
        show_stats "$@"
        ;;
    filter)
        filter_by_time "$@"
        ;;
    *)
        echo -e "${RED}Unknown command: $command${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac
