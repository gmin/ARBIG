# 配置文件说明

## 📋 配置文件列表

### **敏感配置文件（不会上传到 Git）**

这些文件包含账号密码等敏感信息，已添加到 `.gitignore`，不会上传到远程仓库：

- `ctp_sim.json` - SimNow 仿真账号配置
- `ctp_sim2.json` - SimNow 仿真账号配置2（备用）
- `database.json` - 数据库连接配置

### **示例配置文件（会上传到 Git）**

这些是配置模板，供参考使用：

- `ctp_sim.json.example` - SimNow 仿真账号配置示例
- `ctp_sim2.json.example` - SimNow 仿真账号配置2示例
- `database.json.example` - 数据库连接配置示例

## 🚀 首次使用步骤

### 1. 复制示例配置文件

```bash
cd config/

# 复制 CTP 仿真配置
cp ctp_sim.json.example ctp_sim.json
cp ctp_sim2.json.example ctp_sim2.json

# 复制数据库配置
cp database.json.example database.json
```

### 2. 修改配置文件

编辑复制后的文件，填入真实的账号信息：

#### `ctp_sim.json`
```json
{
    "用户名": "你的SimNow用户名",
    "密码": "你的SimNow密码",
    "经纪商代码": "9999",
    "交易服务器": "182.254.243.31:30001",
    "行情服务器": "182.254.243.31:30011",
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000"
}
```

#### `database.json`
```json
{
    "host": "localhost",
    "port": 3306,
    "user": "数据库用户名",
    "password": "数据库密码",
    "database": "arbig_trading"
}
```

### 3. 验证配置

```bash
# 测试 CTP 连接
python tests/legacy/ctp_connection_test.py

# 测试数据库连接
python tests/test_database.py
```

## ⚠️ 安全提示

1. **永远不要**将包含真实账号密码的配置文件上传到 Git
2. **定期修改**密码，特别是实盘账号
3. **妥善保管**配置文件，不要分享给他人
4. 如果不小心上传了敏感信息，立即：
   - 修改账号密码
   - 使用 `git filter-branch` 或 `BFG Repo-Cleaner` 清理 Git 历史

## 📚 相关文档

- [SimNow 仿真平台](http://www.simnow.com.cn/)
- [CTP API 文档](https://www.sfit.com.cn/DocumentDown/api_3.html)
- [系统配置说明](../docs/CONFIGURATION.md)

