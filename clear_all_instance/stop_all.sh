#!/bin/bash
# 一键停止所有区域的EC2实例

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: Python 3未安装${NC}"
    echo "请安装Python 3"
    exit 1
fi

# 检查boto3是否安装
if ! python3 -c "import boto3" &> /dev/null; then
    echo -e "${YELLOW}警告: boto3 模块未安装${NC}"
    echo -e "正在尝试安装boto3..."
    pip3 install boto3
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}错误: 安装boto3失败${NC}"
        echo "请手动安装: pip3 install boto3"
        exit 1
    fi
fi

# 检查AWS CLI是否安装
if ! command -v aws &> /dev/null; then
    echo -e "${YELLOW}警告: AWS CLI未安装${NC}"
    echo "某些功能可能不可用"
    echo "请考虑安装AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
fi

# 确保停止脚本有执行权限
chmod +x "$SCRIPT_DIR/stop_all_instances.py"

# 运行Python脚本
echo -e "${YELLOW}开始停止所有区域的EC2实例...${NC}"
python3 "$SCRIPT_DIR/stop_all_instances.py"

exit $? 