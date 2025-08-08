# ARBIG数据库连接信息总结

## 数据库服务状态

### MySQL 8.0.42
- ✅ **状态**: 已安装并运行
- 🔗 **连接**: localhost:3306
- 👤 **用户**: root
- 🔑 **密码**: arbig123
- 📊 **数据库**: arbig_trading
- 📋 **表数量**: 7个核心表 + 3个视图
- 💾 **存储引擎**: InnoDB
- 🔤 **字符集**: utf8mb4_unicode_ci

### Redis
- ❌ **状态**: 已完全移除
- 📝 **说明**: Redis功能已移除，行情数据直接使用vnpy内存缓存
- 🚀 **优势**: 简化架构，提升性能，减少依赖

## 快速连接测试

### MySQL连接测试
```bash
# 测试连接
mysql -u root -p'arbig123' -e "SELECT 'MySQL连接成功' as status;"

# 查看数据库
mysql -u root -p'arbig123' -e "SHOW DATABASES;"

# 查看表
mysql -u root -p'arbig123' arbig_trading -e "SHOW TABLES;"

# 查看账户数据
mysql -u root -p'arbig123' arbig_trading -e "SELECT * FROM accounts;"
```

### Redis连接测试
```bash
# 测试连接
redis-cli ping

# 查看服务器信息
redis-cli info server

# 查看内存使用
redis-cli info memory

# 测试数据操作
redis-cli set test_key "Hello Redis"
redis-cli get test_key
redis-cli del test_key
```

## Python连接示例

### MySQL连接
```python
import aiomysql

async def test_mysql_connection():
    try:
        conn = await aiomysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='arbig123',
            db='arbig_trading',
            charset='utf8mb4'
        )
        
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM accounts")
            result = await cursor.fetchone()
            print(f"账户数量: {result[0]}")
        
        conn.close()
        print("✅ MySQL连接测试成功")
        
    except Exception as e:
        print(f"❌ MySQL连接失败: {e}")
```

### Redis连接
```python
import aioredis

async def test_redis_connection():
    try:
        redis = await aioredis.create_redis_pool(
            'redis://localhost:6379',
            db=0,
            encoding='utf-8'
        )
        
        # 测试基本操作
        await redis.set('test_key', 'Hello Redis')
        value = await redis.get('test_key')
        print(f"Redis测试值: {value}")
        
        # 测试Stream操作
        await redis.xadd('test_stream', {'field': 'value'})
        result = await redis.xrevrange('test_stream', count=1)
        print(f"Stream测试: {result}")
        
        # 清理测试数据
        await redis.delete('test_key', 'test_stream')
        
        redis.close()
        await redis.wait_closed()
        print("✅ Redis连接测试成功")
        
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
```

### 使用ARBIG数据库管理器
```python
from shared.database.connection import init_database, get_db_manager, get_market_data_redis

async def test_arbig_database():
    # 数据库配置
    mysql_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'arbig123',
        'database': 'arbig_trading',
        'charset': 'utf8mb4'
    }
    
    redis_config = {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    }
    
    try:
        # 初始化连接
        success = await init_database(mysql_config, redis_config)
        if not success:
            print("❌ 数据库初始化失败")
            return
        
        # 测试MySQL操作
        db_manager = get_db_manager()
        accounts = await db_manager.execute_query("SELECT * FROM accounts")
        print(f"✅ 查询到 {len(accounts)} 个账户")
        
        # 测试Redis操作
        market_redis = get_market_data_redis()
        tick_data = {
            'timestamp': 1691234567890,
            'last_price': 450.50,
            'volume': 1000
        }
        await market_redis.save_tick_data('au2509', tick_data)
        latest = await market_redis.get_latest_tick('au2509')
        print(f"✅ 保存并读取行情数据: {latest['last_price']}")
        
        # 关闭连接
        await db_manager.close()
        print("✅ ARBIG数据库测试完成")
        
    except Exception as e:
        print(f"❌ ARBIG数据库测试失败: {e}")
```

## 数据库管理工具使用

### 使用ARBIG数据库管理工具
```bash
# 进入vnpy环境
conda activate vnpy
cd /root/ARBIG

# 查看所有表
python scripts/db_manager.py tables

# 查看账户信息
python scripts/db_manager.py accounts

# 查看持仓信息
python scripts/db_manager.py positions

# 查看交易记录
python scripts/db_manager.py trades --limit 10

# 查看策略触发记录
python scripts/db_manager.py triggers --limit 10

# 查看表结构
python scripts/db_manager.py info --table accounts

# 备份数据库
python scripts/db_manager.py backup --file backup_$(date +%Y%m%d).sql
```

## 服务管理命令

### MySQL服务管理
```bash
# 查看MySQL状态
sudo systemctl status mysql

# 启动MySQL
sudo systemctl start mysql

# 停止MySQL
sudo systemctl stop mysql

# 重启MySQL
sudo systemctl restart mysql

# 设置开机自启
sudo systemctl enable mysql
```

### Redis服务管理
```bash
# 查看Redis状态
sudo systemctl status redis-server

# 启动Redis
sudo systemctl start redis-server

# 停止Redis
sudo systemctl stop redis-server

# 重启Redis
sudo systemctl restart redis-server

# 设置开机自启
sudo systemctl enable redis-server
```

## 监控和维护

### 性能监控
```bash
# MySQL性能监控
mysql -u root -p'arbig123' -e "SHOW PROCESSLIST;"
mysql -u root -p'arbig123' -e "SHOW STATUS LIKE 'Connections';"

# Redis性能监控
redis-cli info stats
redis-cli info memory
redis-cli --latency
```

### 日志查看
```bash
# MySQL日志
sudo tail -f /var/log/mysql/error.log

# Redis日志
sudo tail -f /var/log/redis/redis-server.log
```

### 数据备份
```bash
# MySQL备份
mysqldump -u root -p'arbig123' arbig_trading > backup_$(date +%Y%m%d_%H%M%S).sql

# Redis备份
redis-cli bgsave
sudo cp /var/lib/redis/dump.rdb /backup/redis_backup_$(date +%Y%m%d_%H%M%S).rdb
```

## 故障排除

### 常见问题及解决方案

#### MySQL连接问题
```bash
# 检查MySQL进程
ps aux | grep mysql

# 检查端口占用
netstat -tlnp | grep 3306

# 重置root密码
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'arbig123';"
```

#### Redis连接问题
```bash
# 检查Redis进程
ps aux | grep redis

# 检查端口占用
netstat -tlnp | grep 6379

# 测试Redis配置
redis-cli config get "*"
```

## 安全建议

### MySQL安全
- ✅ 已设置root密码
- 🔄 建议创建专用应用用户
- 🔄 建议限制远程连接
- 🔄 建议定期更新密码

### Redis安全
- ⚠️ 当前无密码保护
- 🔄 建议设置密码
- ✅ 已绑定本地地址
- 🔄 建议禁用危险命令

---

**创建时间**: 2025-08-06  
**最后更新**: 2025-08-06  
**验证状态**: ✅ 所有连接已测试通过
