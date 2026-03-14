# CTP 安装与排障指南

## 概述

本文档只关注当前版本 ARBIG 中真正还有效的两件事：

1. 如何准备 `vnpy` / `vnpy_ctp`
2. 如何让 Trading Service 正常读取 `config/ctp_sim.json` 并连接 CTP

旧版 `core/ctp/`、`libs/ctp/`、`config/ctp.json`、`test_ctp.py` 这类结构已经不再是当前项目的主路径，以下内容均以当前服务实现为准。

## 当前实现位置

当前项目里，CTP 相关逻辑主要集中在以下位置：

- `services/trading_service/core/ctp_integration.py`
- `services/trading_service/api/real_trading.py`
- `config/ctp_sim.json`

其中：

- Trading Service 负责初始化 `vnpy_ctp.CtpGateway`
- Web Admin 和 Strategy Service 都不直接管理 CTP 连接
- CTP 配置文件默认从 `config/ctp_sim.json` 读取

## 快速检查

在启动系统前，建议先确认以下三项：

```bash
python -c "import vnpy; print('vnpy ok')"
python -c "from vnpy_ctp import CtpGateway; print('vnpy_ctp ok')"
python -c "from pathlib import Path; print(Path('config/ctp_sim.json').exists())"
```

如果这三项里任何一项失败，先不要启动服务，先解决环境问题。

## 配置文件

当前使用的配置文件是 `config/ctp_sim.json`。

示例：

```json
{
    "用户名": "your_username",
    "密码": "your_password",
    "经纪商代码": "9999",
    "交易服务器": "182.254.243.31:30001",
    "行情服务器": "182.254.243.31:30011",
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000",
    "产品信息": "simnow_client_test"
}
```

说明：

- 实际地址请以 SimNow 或券商最新信息为准
- `config/ctp_sim.json` 缺失时，Trading Service 会直接报配置文件不存在

## 推荐启动验证路径

建议按下面顺序验证，而不是一开始就启动整套系统：

1. 先确认 Python 环境能导入 `vnpy` 和 `vnpy_ctp`
2. 再确认 `config/ctp_sim.json` 存在且字段完整
3. 再启动 `services/trading_service/main.py`
4. 最后通过接口检查连接状态

示例：

```bash
python services/trading_service/main.py --port 8001
curl http://localhost:8001/real_trading/status
curl http://localhost:8001/real_trading/test_connection
```

如果 Trading Service 能起来，但 `status` 里显示未连接，通常说明问题在 CTP 环境本身，而不是 Web 或 Strategy Service。

## vnpy-ctp 安装问题解决方案

### 问题描述

在安装 `vnpy-ctp` 时，可能会遇到以下错误：

```text
ImportError: /tmp/pip-install-xxxx/vnpy_ctp/api/libthostmduserapi_se.so: cannot open shared object file: No such file or directory
```

### 根本原因

`vnpy-ctp` 的预编译 wheel 包与当前环境的 NumPy 版本不兼容，导致运行时找不到依赖的 CTP 动态库文件。这是因为：

1. **NumPy版本冲突**：vnpy 4.x 要求 numpy>=2.2.3，但 CTP 库通常需要较老的 NumPy 版本
2. **预编译包问题**：wheel 包在编译时硬编码了临时目录路径
3. **环境兼容性**：不同 Python 环境之间可能存在编译和链接差异

### 解决方案

#### 方法1：从源码重新编译（强烈推荐）

这是经过实际验证的最有效解决方案：

1. **卸载现有版本**：

   ```bash
   pip uninstall vnpy-ctp -y
   ```

2. **克隆源码**：

   ```bash
   cd /tmp  # 或其他合适的目录
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

### 安装后验证

安装完成后，至少做两步验证：

```bash
python -c "from vnpy_ctp import CtpGateway; print('vnpy-ctp 安装成功！')"
python services/trading_service/main.py --port 8001
```

然后再访问：

```bash
curl http://localhost:8001/real_trading/status
curl http://localhost:8001/real_trading/test_connection
```

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

# Linux 下检查库文件依赖
ldd /path/to/vnpy_ctp/api/vnctpmd*.so
```

#### 3. 权限问题

确保库文件有正确的权限：

```bash
chmod +x /path/to/vnpy_ctp/api/*.so
```

### 环境要求

- **Python**: 以当前 `vnpy` / `vnpy_ctp` 兼容性为准
- **操作系统**: Linux 与 macOS 都可尝试，但以本机编译结果为准
- **内存**: 至少 4GB RAM
- **网络**: 能够访问CTP服务器

### 推荐环境配置

#### 方案 A：conda 环境

```bash
# 创建专用环境
conda create -n vnpy python=3.11 -y
conda activate vnpy

# 安装基础依赖
pip install vnpy

# 从源码安装 vnpy-ctp（按照方法1）
```

#### 方案 B：标准虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install vnpy

# 从源码安装 vnpy-ctp（按照方法1）
```

### 重要提醒

1. 优先用独立环境，不要直接污染系统 Python
2. 如果 `pip install vnpy-ctp` 失败，优先尝试源码安装
3. 先验证 `vnpy_ctp` 可导入，再启动 Trading Service
4. 非交易时间连接失败不一定代表安装失败

### 参考链接

- [vnpy官方论坛解决方案](https://www.vnpy.com/forum/topic/33714-qiu-zhu-ubuntuyun-xing-shi-diao-yong-ctp-apibao-cuo-wu-fa-zhao-dao-dong-tai-ku-libthostmduserapi-se-sowen-jian)
- [vnpy-ctp GitHub仓库](https://github.com/vnpy/vnpy_ctp)
- [CTP API官方文档](http://www.sfit.com.cn/)
