#!/bin/bash
# One-click stop for all EC2 instances in all regions

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color definitions
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3"
    exit 1
fi

# Check if boto3 is installed
if ! python3 -c "import boto3" &> /dev/null; then
    echo -e "${YELLOW}Warning: boto3 module is not installed${NC}"
    echo -e "Attempting to install boto3..."
    pip3 install boto3
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to install boto3${NC}"
        echo "Please install manually: pip3 install boto3"
        exit 1
    fi
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${YELLOW}Warning: AWS CLI is not installed${NC}"
    echo "Some features may not be available"
    echo "Please consider installing AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
fi

# Ensure stop script has execution permissions
chmod +x "$SCRIPT_DIR/stop_all_instances.py"

# Run Python script
echo -e "${YELLOW}Starting to stop all EC2 instances in all regions...${NC}"
python3 "$SCRIPT_DIR/stop_all_instances.py"

exit $?