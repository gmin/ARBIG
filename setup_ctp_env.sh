#!/bin/bash
# CTP环境设置脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 设置CTP库路径
export LD_LIBRARY_PATH="$PROJECT_ROOT/libs/ctp_sim:$LD_LIBRARY_PATH"
export PYTHONPATH="$PROJECT_ROOT/libs/ctp_sim:$PYTHONPATH"

# 设置locale
export LC_ALL=C.utf8

echo "CTP环境设置完成"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
echo "PYTHONPATH: $PYTHONPATH"
echo "LC_ALL: $LC_ALL"
