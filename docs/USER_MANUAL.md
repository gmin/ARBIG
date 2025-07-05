# ARBIG量化交易系统用户手册

## 📖 目录

1. [系统概述](#系统概述)
2. [快速开始](#快速开始)
3. [系统架构](#系统架构)
4. [安装部署](#安装部署)
5. [配置说明](#配置说明)
6. [功能模块](#功能模块)
7. [Web监控](#web监控)
8. [风控管理](#风控管理)
9. [故障排除](#故障排除)
10. [最佳实践](#最佳实践)

## 系统概述

ARBIG是一个专业的量化交易系统，专注于黄金期货的量化交易策略执行。系统采用模块化设计，提供完整的交易执行链路和风控管理功能。

### 核心特性

- **🔄 完整交易链路** - 行情订阅 → 策略决策 → 订单执行 → 风控监控
- **🛡️ 多层风控体系** - 交易前、交易中、交易后全方位风控
- **🌐 Web监控界面** - 实时监控和人工干预功能
- **⚡ 高性能架构** - 事件驱动，低延迟执行
- **🔧 灵活配置** - 支持多种配置方式和参数调整

### 技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   策略层        │    │   执行层        │    │   基础设施层     │
│                 │    │                 │    │                 │
│ - 量化策略      │    │ - 订单管理      │    │ - CTP接口       │
│ - 信号生成      │◄──►│ - 风控检查      │◄──►│ - 事件引擎      │
│ - 参数优化      │    │ - 执行路由      │    │ - 数据存储      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   监控层        │    │   数据层        │    │   配置层        │
│                 │    │                 │    │                 │
│ - Web界面       │    │ - 行情数据      │    │ - 系统配置      │
│ - 实时监控      │    │ - 账户数据      │    │ - 策略参数      │
│ - 人工干预      │    │ - 交易数据      │    │ - 风控参数      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 快速开始

### 1. 系统要求

- **操作系统**: Linux (推荐 Ubuntu 20.04+) 或 Windows 10+
- **Python**: 3.8+ 
- **内存**: 4GB+ RAM
- **磁盘**: 10GB+ 可用空间
- **网络**: 稳定的互联网连接

### 2. 快速安装

```bash
# 1. 克隆项目
git clone https://github.com/your-org/ARBIG.git
cd ARBIG

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置CTP账户
cp config/ctp_sim.json.template config/ctp_sim.json
# 编辑配置文件，填入您的CTP账户信息

# 4. 启动系统
python web_monitor/run_web_monitor.py --mode integrated
```

### 3. 访问Web界面

打开浏览器访问: http://localhost:8000

## 安装部署

### 开发环境部署

适用于开发和测试：

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行测试
python -m pytest tests/

# 4. 启动开发服务
python web_monitor/run_web_monitor.py --mode integrated
```

### 生产环境部署

使用自动化部署脚本：

```bash
# 1. 运行部署脚本
sudo python deploy/deploy_arbig.py --deployment-dir /opt/arbig

# 2. 配置CTP账户
sudo vi /opt/arbig/config/ctp_config.json

# 3. 启动系统服务
sudo systemctl start arbig
sudo systemctl enable arbig  # 开机自启

# 4. 检查服务状态
sudo systemctl status arbig
```

### Docker部署

```bash
# 1. 构建镜像
docker build -t arbig:latest .

# 2. 运行容器
docker run -d \
  --name arbig \
  -p 8000:8000 \
  -v /opt/arbig/config:/app/config \
  -v /opt/arbig/logs:/app/logs \
  arbig:latest
```

## 配置说明

### 主配置文件 (config.yaml)

```yaml
# 系统配置
system:
  name: "ARBIG"
  version: "1.0.0"
  environment: "production"  # development/production
  debug: false

# 日志配置
logging:
  level: "INFO"  # DEBUG/INFO/WARNING/ERROR
  file: "logs/arbig.log"
  max_size: "100MB"
  backup_count: 10

# 服务配置
services:
  market_data:
    enabled: true
    symbols: ["au2509", "au2512", "au2601"]
    cache_size: 1000
    
  account:
    enabled: true
    update_interval: 30  # 秒
    position_sync: true
    
  trading:
    enabled: true
    order_timeout: 30
    max_orders_per_second: 5
    
  risk:
    enabled: true
    max_position_ratio: 0.8
    max_daily_loss: 50000
    max_single_order_volume: 10

# Web监控配置
web_monitor:
  enabled: true
  host: "0.0.0.0"
  port: 8000
```

### CTP配置文件 (ctp_config.json)

```json
{
    "用户名": "您的CTP用户名",
    "密码": "您的CTP密码",
    "经纪商代码": "9999",
    "交易服务器": "180.168.146.187:10130",
    "行情服务器": "180.168.146.187:10131",
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000"
}
```

## 功能模块

### 1. 行情订阅服务

**功能**: 实时获取和管理期货行情数据

**特性**:
- 多合约同时订阅
- 实时数据缓存
- 事件驱动分发
- 连接状态监控

**使用示例**:
```python
from core.services.market_data_service import MarketDataService

# 订阅行情
market_service.subscribe_symbol('au2509', 'my_strategy')

# 获取最新行情
tick = market_service.get_latest_tick('au2509')
print(f"最新价: {tick.last_price}")
```

### 2. 账户信息服务

**功能**: 管理账户资金和持仓信息

**特性**:
- 混合模式（查询+推送）
- 定时自动更新
- 实时状态监控
- 数据缓存管理

**使用示例**:
```python
from core.services.account_service import AccountService

# 获取账户信息
account = account_service.get_account_info()
print(f"可用资金: {account.available}")

# 获取持仓信息
positions = account_service.get_positions()
for pos in positions:
    print(f"{pos.symbol}: {pos.volume} 手")
```

### 3. 交易执行服务

**功能**: 处理订单执行和策略信号

**特性**:
- 完整订单生命周期管理
- 策略信号自动处理
- 风控集成检查
- 实时状态跟踪

**使用示例**:
```python
from core.services.trading_service import TradingService
from core.types import OrderRequest, Direction, OrderType

# 发送订单
order_req = OrderRequest(
    symbol="au2509",
    direction=Direction.LONG,
    type=OrderType.LIMIT,
    volume=1.0,
    price=500.0
)

order_id = trading_service.send_order(order_req)
```

### 4. 风控服务

**功能**: 多层次风险控制和管理

**特性**:
- 交易前风控检查
- 实时风险监控
- 动态参数调整
- 风险事件处理

**使用示例**:
```python
from core.services.risk_service import RiskService

# 风控检查
risk_result = risk_service.check_pre_trade_risk(order_req)
if risk_result.passed:
    # 执行交易
    pass
else:
    print(f"风控拒绝: {risk_result.reason}")
```

## Web监控

### 访问界面

1. 启动系统后，打开浏览器
2. 访问: http://localhost:8000
3. 查看实时监控数据

### 主要功能

#### 1. 系统状态监控
- 各服务运行状态
- CTP连接状态
- 风险级别显示
- 实时数据更新

#### 2. 交易数据展示
- 活跃订单列表
- 当前持仓信息
- 最新成交记录
- 账户资金状况

#### 3. 人工风控操作
- 紧急暂停交易
- 紧急平仓操作
- 策略级别控制
- 参数实时调整

#### 4. 操作日志
- 完整操作记录
- 操作员信息
- 时间戳记录
- 操作结果状态

### 风控操作指南

#### 紧急暂停交易
1. 点击"紧急暂停交易"按钮
2. 输入暂停原因
3. 确认操作
4. 系统立即停止新订单

#### 紧急平仓
1. 点击"紧急平仓"按钮
2. 输入确认码: `EMERGENCY_CLOSE_123`
3. 输入平仓原因
4. 确认执行

#### 策略控制
1. 点击"暂停策略"
2. 输入策略名称
3. 输入暂停原因
4. 确认操作

## 风控管理

### 风控层次

#### 1. 交易前风控
- 订单数量检查
- 持仓限制检查
- 资金充足性检查
- 合约有效性检查

#### 2. 交易中风控
- 实时持仓监控
- 盈亏状况监控
- 风险级别评估
- 异常交易检测

#### 3. 交易后风控
- 成交后风险重评估
- 持仓风险分析
- 风险报告生成
- 风险事件记录

### 风控参数配置

```yaml
risk:
  # 基础限制
  max_position_ratio: 0.8        # 最大持仓比例
  max_daily_loss: 50000          # 最大日内亏损
  max_single_order_volume: 10    # 单笔订单最大数量
  
  # 动态风控
  volatility_threshold: 0.05     # 波动率阈值
  drawdown_threshold: 0.1        # 回撤阈值
  
  # 时间控制
  trading_hours:
    start: "09:00"
    end: "15:00"
    break_start: "11:30"
    break_end: "13:30"
```

### 风险级别

- **LOW**: 正常交易，无特殊限制
- **MEDIUM**: 加强监控，部分限制
- **HIGH**: 严格限制，减少交易
- **CRITICAL**: 暂停交易，人工干预

## 故障排除

### 常见问题

#### 1. CTP连接失败
**现象**: 无法连接到CTP服务器

**解决方案**:
```bash
# 检查网络连接
ping 180.168.146.187

# 检查配置文件
cat config/ctp_config.json

# 查看日志
tail -f logs/arbig.log | grep CTP
```

#### 2. 服务启动失败
**现象**: 服务无法正常启动

**解决方案**:
```bash
# 检查Python环境
python --version

# 检查依赖包
pip list | grep vnpy

# 查看详细错误
python web_monitor/run_web_monitor.py --mode integrated
```

#### 3. Web界面无法访问
**现象**: 浏览器无法打开监控界面

**解决方案**:
```bash
# 检查端口占用
netstat -tlnp | grep 8000

# 检查防火墙
sudo ufw status

# 检查服务状态
ps aux | grep python
```

### 日志分析

#### 查看系统日志
```bash
# 实时查看日志
tail -f logs/arbig.log

# 查看错误日志
grep ERROR logs/arbig.log

# 查看特定服务日志
grep "MarketDataService" logs/arbig.log
```

#### 日志级别说明
- **DEBUG**: 详细调试信息
- **INFO**: 一般信息记录
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

## 最佳实践

### 1. 系统运维

#### 定期维护
```bash
# 每日检查
./scripts/daily_check.sh

# 日志轮转
logrotate /etc/logrotate.d/arbig

# 数据备份
./scripts/backup_data.sh
```

#### 监控告警
```bash
# 设置监控脚本
crontab -e
# 添加: */5 * * * * /opt/arbig/scripts/health_check.sh
```

### 2. 风控管理

#### 参数调整原则
- 根据市场波动调整风控参数
- 定期回测风控效果
- 记录所有参数变更

#### 应急预案
- 制定详细的应急操作流程
- 定期演练应急操作
- 保持通讯畅通

### 3. 性能优化

#### 系统调优
```bash
# 调整系统参数
echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
sysctl -p
```

#### 监控指标
- CPU使用率 < 80%
- 内存使用率 < 80%
- 磁盘使用率 < 90%
- 网络延迟 < 50ms

### 4. 安全管理

#### 访问控制
- 设置强密码策略
- 限制Web访问IP
- 定期更新系统补丁

#### 数据保护
- 加密敏感配置
- 定期备份数据
- 监控异常访问

---

**文档版本**: v1.0  
**最后更新**: 2025-01-04  
**技术支持**: support@arbig.com
