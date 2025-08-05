#!/bin/bash

# ARBIG前端开发服务器启动脚本

echo "🎨 启动ARBIG前端开发服务器"
echo "================================"

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "❌ Node.js未安装，请先安装Node.js"
    exit 1
fi

# 检查npm是否安装
if ! command -v npm &> /dev/null; then
    echo "❌ npm未安装，请先安装npm"
    exit 1
fi

# 进入前端目录
cd "$(dirname "$0")"

# 检查package.json是否存在
if [ ! -f "package.json" ]; then
    echo "❌ package.json不存在"
    exit 1
fi

# 安装依赖
echo "📦 安装依赖包..."
npm install

# 启动开发服务器
echo "🚀 启动开发服务器..."
echo "前端地址: http://localhost:3000"
echo "API代理: http://localhost:80"
echo "按 Ctrl+C 停止服务器"
echo "================================"

npm run dev
