#!/bin/bash

# ARBIG实时日志监控脚本

LOG_DIR="/root/ARBIG/logs"
LATEST_LOG=$(ls -t $LOG_DIR/*.log 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "❌ 没有找到日志文件"
    exit 1
fi

echo "📊 监控日志文件: $LATEST_LOG"
echo "🚀 开始实时监控日志 (按Ctrl+C停止)..."
echo "================================================================================"

# 根据参数决定是否过滤
if [ $# -eq 0 ]; then
    # 没有参数，显示所有日志
    tail -f "$LATEST_LOG"
else
    # 有参数，过滤显示
    echo "🔍 过滤关键词: $*"
    echo "-------------------------------------------------------------------------------"
    tail -f "$LATEST_LOG" | grep -E "$*"
fi
