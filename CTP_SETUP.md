# CTP环境配置指南

## 概述

本文档说明如何在ARBIG项目中配置和使用CTP环境。

## ⚠️ 重要提醒

**vnpy-ctp安装问题**：由于NumPy版本兼容性问题，预编译的vnpy-ctp包通常无法正常工作。**强烈建议直接跳转到文档末尾的"vnpy-ctp 安装问题解决方案"部分，使用从源码编译的方法安装vnpy-ctp**。

## 文件结构

```
ARBIG/
├── libs/
│   └── ctp/
│       ├── thosttraderapi_se.so    # CTP交易API库
│       └── thostmduserapi_se.so    # CTP行情API库
├── config/
│   └── ctp.json                   # CTP环境配置文件
├── core/
│   └── ctp/
│       ├── __init__.py
│       ├── config.py              # 配置管理类
│       └── gateway.py             # CTP网关
└── test_ctp.py                   # 测试脚本
```

## 配置步骤

### 1. 放置API库文件

将CTP API库文件放到正确位置：

```bash
# 创建目录
mkdir -p libs/ctp

# 将API库文件复制到目录中
cp thosttraderapi_se.so libs/ctp/
cp thostmduserapi_se.so libs/ctp/
```

### 2. 配置连接参数

编辑 `config/ctp.json` 文件，设置正确的连接参数：

```json
{
    "用户名": "242407",
    "密码": "1234%^&*QWE",
    "经纪商代码": "9999",
    "交易服务器": "182.254.243.31:30001",
    "行情服务器": "182.254.243.31:30011",
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000",
    "产品信息": "simnow_client_test"
}
```

### 3. 验证配置

运行测试脚本验证配置是否正确：

```bash
python test_ctp.py
```

## 使用方法

### 基本使用

```python
from core.ctp import CtpGateway, CtpConfig

# 创建配置对象
config = CtpConfig()

# 创建网关
gateway = CtpGateway(config)

# 连接CTP环境
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
from core.ctp import CtpGateway
from core.strategy_base import StrategyBase

class MyStrategy(StrategyBase):
    def __init__(self):
        super().__init__()
        self.ctp_gateway = CtpGateway()
        
    def on_init(self):
        """策略初始化"""
        # 连接CTP环境
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
chmod +x libs/ctp/*.so
```

### 2. 网络连接

确保服务器能够访问CTP服务器：
- 交易服务器：182.254.243.31:30001
- 行情服务器：182.254.243.31:30011

注意：CTP SimNow环境的服务器地址会定期更新，请以最新的官方地址为准。

### 3. 账户信息

使用正确的账户信息：
- 用户名：242407
- 密码：1234%^&*QWE
- 经纪商代码：9999

### 4. 交易时间

CTP环境的交易时间：
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

1. **测试优先**：在实盘交易前，充分测试CTP环境
2. **错误处理**：添加完善的错误处理机制
3. **日志记录**：记录关键操作和异常情况
4. **风控措施**：在CTP环境中测试风控逻辑

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

`vnpy-ctp` 的预编译 wheel 包与当前环境的 NumPy 版本不兼容，导致运行时找不到依赖的 CTP 动态库文件。这是因为：

1. **NumPy版本冲突**：vnpy 4.x 要求 numpy>=2.2.3，但 CTP 库通常需要较老的 NumPy 版本
2. **预编译包问题**：wheel 包在编译时硬编码了临时目录路径
3. **环境兼容性**：不同 Python 环境（Anaconda vs 标准虚拟环境）的兼容性问题

### 解决方案

#### 方法1：从源码重新编译（强烈推荐）⭐

这是经过实际验证的最有效解决方案：

1. **卸载现有版本**：
   ```bash
   pip uninstall vnpy-ctp -y
   ```

2. **克隆源码**：
   ```bash
   cd /root  # 或其他合适的目录
   git clone https://github.com/vnpy/vnpy_ctp.git
   cd vnpy_ctp
   ```

3. **安装构建依赖**：
   ```bash
   pip install meson-python ninja pybind11
   ```

4. **从源码编译安装**：
   ```bash
   pip install .
   ```

5. **验证安装**：
   ```bash
   python -c "from vnpy_ctp import CtpGateway; print('vnpy-ctp 安装成功！')"
   ```

#### 方法2：软链接法（临时解决）

如果方法1不可行，可以尝试软链接：

1. **查找vnpy-ctp安装目录**：
   ```bash
   python -c "import vnpy_ctp; print(vnpy_ctp.__file__)"
   ```

2. **创建软链接**：
   ```bash
   # 找到实际的库文件路径，然后创建软链接到错误信息中的路径
   ln -sf /path/to/actual/libthostmduserapi_se.so /tmp/pip-install-xxxx/vnpy_ctp/api/libthostmduserapi_se.so
   ln -sf /path/to/actual/libthosttraderapi_se.so /tmp/pip-install-xxxx/vnpy_ctp/api/libthosttraderapi_se.so
   ```

#### 方法3：环境变量法（不推荐）

```bash
export LD_LIBRARY_PATH=/path/to/vnpy_ctp/api:$LD_LIBRARY_PATH
```

### 完整测试流程

安装完成后，运行完整的CTP连接测试：

```bash
# 在ARBIG项目根目录下
python tests/ctp_connection_test.py
```

成功的输出应该包括：
- ✅ 交易服务器连接成功
- ✅ 交易服务器登录成功
- ✅ 行情服务器连接成功
- ✅ 行情服务器登录成功
- ✅ 成功接收行情数据

### 故障排除指南

#### 1. 编译错误

如果遇到编译错误，检查以下依赖：

```bash
# 安装系统依赖（Ubuntu/Debian）
sudo apt-get update
sudo apt-get install build-essential python3-dev

# 安装系统依赖（CentOS/RHEL）
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel

# 确保pip是最新版本
pip install --upgrade pip setuptools wheel
```

#### 2. 运行时错误

如果仍然出现库文件加载错误：

```bash
# 检查库文件是否存在
find /path/to/python/site-packages -name "*thostmduserapi*"

# 检查库文件依赖
ldd /path/to/vnpy_ctp/api/vnctpmd*.so
```

#### 3. 权限问题

确保库文件有正确的权限：

```bash
chmod +x /path/to/vnpy_ctp/api/*.so
```

### 环境要求

- **Python**: 3.8+ (推荐 3.11)
- **操作系统**: Linux (推荐 Ubuntu 20.04+/CentOS 8+)
- **内存**: 至少 4GB RAM
- **网络**: 能够访问CTP服务器

### 推荐环境配置

#### Anaconda环境（推荐）

```bash
# 创建专用环境
conda create -n vnpy python=3.11 -y
conda activate vnpy

# 安装基础依赖
pip install vnpy

# 从源码安装vnpy-ctp（按照方法1）
```

#### 标准虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install vnpy

# 从源码安装vnpy-ctp（按照方法1）
```

### 重要提醒

1. **必须从源码编译**：预编译的wheel包在大多数环境下都会有兼容性问题
2. **NumPy版本**：让pip自动处理NumPy版本依赖，不要手动指定版本
3. **测试先行**：安装完成后务必运行完整的连接测试
4. **环境隔离**：使用独立的Python环境避免依赖冲突

### 参考链接

- [vnpy官方论坛解决方案](https://www.vnpy.com/forum/topic/33714-qiu-zhu-ubuntuyun-xing-shi-diao-yong-ctp-apibao-cuo-wu-fa-zhao-dao-dong-tai-ku-libthostmduserapi-se-sowen-jian)
- [vnpy-ctp GitHub仓库](https://github.com/vnpy/vnpy_ctp)
- [CTP API官方文档](http://www.sfit.com.cn/)