# CTP仿真环境配置指南

## 概述

本文档说明如何在ARBIG项目中配置和使用CTP仿真交易环境。

## 文件结构

```
ARBIG/
├── libs/
│   └── ctp_sim/
│       ├── thosttraderapi_se.so    # CTP仿真交易API库
│       └── thostmduserapi_se.so    # CTP仿真行情API库
├── config/
│   └── ctp_sim.json               # CTP仿真环境配置文件
├── core/
│   └── ctp_sim/
│       ├── __init__.py
│       ├── config.py              # 配置管理类
│       └── gateway.py             # CTP仿真网关
└── test_ctp_sim.py               # 测试脚本
```

## 配置步骤

### 1. 放置API库文件

将CTP仿真API库文件放到正确位置：

```bash
# 创建目录
mkdir -p libs/ctp_sim

# 将API库文件复制到目录中
cp thosttraderapi_se.so libs/ctp_sim/
cp thostmduserapi_se.so libs/ctp_sim/
```

### 2. 配置连接参数

编辑 `config/ctp_sim.json` 文件，设置正确的连接参数：

```json
{
    "用户名": "242407",
    "密码": "1234%^&*QWE",
    "经纪商代码": "9999",
    "交易服务器": "180.168.146.187:10101",
    "行情服务器": "180.168.146.187:10102",
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000",
    "产品信息": "simnow_client_test"
}
```

### 3. 验证配置

运行测试脚本验证配置是否正确：

```bash
python test_ctp_sim.py
```

## 使用方法

### 基本使用

```python
from core.ctp_sim import CtpSimGateway, CtpSimConfig

# 创建配置对象
config = CtpSimConfig()

# 创建网关
gateway = CtpSimGateway(config)

# 连接仿真环境
if gateway.connect():
    print("连接成功")
    
    # 订阅合约
    gateway.subscribe(["AU2406", "AU2412"])
    
    # 获取行情
    tick = gateway.get_tick("AU2406")
    if tick:
        print(f"最新价: {tick.last_price}")
    
    # 发送订单
    order_id = gateway.send_order(
        symbol="AU2406",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        volume=1,
        price=500.0
    )
    
    # 断开连接
    gateway.disconnect()
```

### 在策略中使用

```python
from core.ctp_sim import CtpSimGateway
from core.strategy_base import StrategyBase

class MyStrategy(StrategyBase):
    def __init__(self):
        super().__init__()
        self.ctp_gateway = CtpSimGateway()
        
    def on_init(self):
        """策略初始化"""
        # 连接CTP仿真环境
        if self.ctp_gateway.connect():
            # 订阅合约
            self.ctp_gateway.subscribe(["AU2406"])
            
            # 设置回调函数
            self.ctp_gateway.on_tick = self.on_tick
            self.ctp_gateway.on_trade = self.on_trade
            
    def on_tick(self, tick):
        """行情数据回调"""
        # 处理行情数据
        pass
        
    def on_trade(self, trade):
        """成交数据回调"""
        # 处理成交数据
        pass
```

## 注意事项

### 1. 库文件权限

确保API库文件有执行权限：

```bash
chmod +x libs/ctp_sim/*.so
```

### 2. 网络连接

确保服务器能够访问CTP仿真服务器：
- 交易服务器：180.168.146.187:10101
- 行情服务器：180.168.146.187:10102

### 3. 账户信息

使用正确的仿真账户信息：
- 用户名：242407
- 密码：1234%^&*QWE
- 经纪商代码：9999

### 4. 交易时间

CTP仿真环境的交易时间：
- 上午：09:00-11:30
- 下午：13:30-15:00
- 夜盘：21:00-02:30（次日）

## 故障排除

### 1. 连接失败

- 检查网络连接
- 验证服务器地址和端口
- 确认账户信息正确

### 2. 库文件加载失败

- 检查库文件是否存在
- 确认文件权限
- 验证库文件版本兼容性

### 3. 行情数据异常

- 检查合约代码是否正确
- 确认是否在交易时间内
- 验证订阅是否成功

## 开发建议

1. **测试优先**：在实盘交易前，充分测试仿真环境
2. **错误处理**：添加完善的错误处理机制
3. **日志记录**：记录关键操作和异常情况
4. **风控措施**：在仿真环境中测试风控逻辑

## 相关文档

- [CTP API文档](http://www.sfit.com.cn/)
- [SimNow仿真环境](http://www.simnow.com.cn/)
- [vnpy-ctp文档](https://www.vnpy.com/docs/cn/gateway/ctp.html)

## vnpy-ctp 安装问题解决方案

### 问题描述

在安装 `vnpy-ctp` 时，可能会遇到以下错误：
```
ImportError: /tmp/pip-install-xxxx/vnpy_ctp/api/libthostmduserapi_se.so: cannot open shared object file: No such file or directory
```

### 根本原因

`vnpy-ctp` 的 wheel 包在编译时，将临时目录的路径硬编码到了 Python 扩展模块中，导致运行时找不到依赖的 CTP 动态库文件。

### 解决方案

#### 方法1：软链接法（推荐）

1. **查找依赖路径**：
   ```bash
   ldd /path/to/venv/lib/python3.x/site-packages/vnpy_ctp/api/vnctpmd.cpython-xxx.so
   ```

2. **创建软链接**：
   ```bash
   # 创建临时目录
   mkdir -p /tmp/pip-install-xxxx/vnpy_ctp/api/
   
   # 创建软链接
   ln -sf /path/to/venv/lib/python3.x/site-packages/vnpy_ctp/api/libthostmduserapi_se.so /tmp/pip-install-xxxx/vnpy_ctp/api/libthostmduserapi_se.so
   ln -sf /path/to/venv/lib/python3.x/site-packages/vnpy_ctp/api/libthosttraderapi_se.so /tmp/pip-install-xxxx/vnpy_ctp/api/libthosttraderapi_se.so
   ```

#### 方法2：重新编译安装

1. **清理缓存**：
   ```bash
   pip uninstall vnpy-ctp -y
   pip cache purge
   ```

2. **重新安装**：
   ```bash
   pip install vnpy-ctp --no-cache-dir
   ```

#### 方法3：设置环境变量

```bash
export LD_LIBRARY_PATH=/path/to/venv/lib/python3.x/site-packages/vnpy_ctp/api:$LD_LIBRARY_PATH
```

### 验证安装

```python
from vnpy_ctp import CtpGateway
from vnpy.event import EventEngine

# 创建测试实例
event_engine = EventEngine()
gateway = CtpGateway(event_engine, "test")
print("vnpy-ctp 安装成功！")
```

### 注意事项

1. **路径问题**：每次重新安装时，临时目录路径可能不同，需要重新创建软链接
2. **权限问题**：确保 CTP 动态库文件有执行权限
3. **版本兼容**：确保 `vnpy-ctp` 版本与 Python 版本兼容

### 环境要求

- **Python**: 3.8+
- **操作系统**: Linux (推荐 Ubuntu/CentOS)
- **依赖包**: vnpy, numpy, pandas

### 推荐环境

建议使用标准的 Python 虚拟环境，而不是 Anaconda 环境：
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install vnpy vnpy-ctp ta-lib
```

这样可以避免 Anaconda 环境的复杂性，提高系统的稳定性和性能。 