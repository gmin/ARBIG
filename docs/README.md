# ARBIG 文档中心

## 📚 文档导航

欢迎来到ARBIG量化交易系统的文档中心！这里包含了系统的完整技术文档。

### 🏗️ 系统架构

| 文档 | 描述 | 更新状态 |
|------|------|----------|
| [**系统架构**](ARCHITECTURE.md) | 详细的系统架构设计和技术栈 | ✅ v2.0 |
| [**架构更新**](ARCHITECTURE_UPDATE.md) | v2.0架构变更说明和升级指南 | ✅ 最新 |

### 📖 用户文档

| 文档 | 描述 | 适用对象 |
|------|------|----------|
| [**用户手册**](USER_MANUAL.md) | 完整的用户使用指南 | 👥 所有用户 |
| [**部署指南v2.0**](DEPLOYMENT_V2.md) | v2.0架构的部署配置 | 🔧 运维人员 |

### 🔧 技术文档

| 文档 | 描述 | 适用对象 |
|------|------|----------|
| [**API接口规范**](WEB_API_SPECIFICATION.md) | 完整的API接口文档 | 👨‍💻 开发者 |
| [**账户服务指南**](ACCOUNT_SERVICE_GUIDE.md) | 账户服务使用说明 | 👨‍💻 开发者 |
| [**行情服务指南**](MARKET_DATA_SERVICE_GUIDE.md) | 行情数据服务文档 | 👨‍💻 开发者 |
| [**交易服务指南**](TRADING_SERVICE_GUIDE.md) | 交易执行服务文档 | 👨‍💻 开发者 |

### 📊 策略文档

| 文档 | 描述 | 适用对象 |
|------|------|----------|
| [**策略总览**](strategies/README.md) | 策略文档导航和选择指南 | 📈 策略用户 |
| [**基差套利指南**](strategies/SPREAD_THRESHOLD_GUIDE.md) | 基差套利阈值设置详解 | 📈 策略用户 |

### 🎨 设计文档

| 文档 | 描述 | 状态 |
|------|------|------|
| [**Web界面设计**](WEB_UI_DESIGN.md) | Web界面设计规范 | 📋 参考 |
| [**指挥中心设计**](WEB_COMMAND_CENTER_DESIGN.md) | Web指挥中心设计思路 | 📋 参考 |
| [**实施计划**](WEB_COMMAND_CENTER_IMPLEMENTATION_PLAN.md) | 项目实施计划 | 📋 参考 |

## 🎯 快速导航

### 👋 新用户入门
1. 阅读 [README.md](../README.md) 了解项目概述
2. 查看 [系统架构](ARCHITECTURE.md) 理解系统设计
3. 按照 [部署指南](DEPLOYMENT_V2.md) 搭建环境
4. 参考 [用户手册](USER_MANUAL.md) 开始使用

### 👨‍💻 开发者指南
1. 了解 [系统架构](ARCHITECTURE.md) 和 [架构更新](ARCHITECTURE_UPDATE.md)
2. 查看 [API接口规范](WEB_API_SPECIFICATION.md)
3. 阅读各服务的技术文档
4. 参考策略开发相关文档

### 📈 策略用户
1. 查看 [策略总览](strategies/README.md) 选择合适策略
2. 阅读具体策略的详细文档
3. 参考 [用户手册](USER_MANUAL.md) 进行配置
4. 使用Web管理系统监控策略表现

### 🔧 运维人员
1. 参考 [部署指南](DEPLOYMENT_V2.md) 进行部署
2. 了解 [系统架构](ARCHITECTURE.md) 便于维护
3. 查看 [用户手册](USER_MANUAL.md) 中的监控部分
4. 关注 [架构更新](ARCHITECTURE_UPDATE.md) 了解变更

## 📋 文档状态

### ✅ 已完成文档
- 系统架构文档 (v2.0)
- 架构更新说明
- 部署指南 (v2.0)
- 策略文档重组
- API接口规范更新

### 🔄 需要更新的文档
- [ ] 用户手册 (需要更新v2.0架构内容)
- [ ] 各服务指南 (需要更新模块路径)
- [ ] 开发指南 (需要创建)

### 📝 计划新增文档
- [ ] 故障排除指南
- [ ] 性能优化指南
- [ ] 安全配置指南
- [ ] 监控告警配置
- [ ] 策略开发教程

## 🔍 文档搜索

### 按功能查找
- **交易功能**: [用户手册](USER_MANUAL.md), [交易服务指南](TRADING_SERVICE_GUIDE.md)
- **风控功能**: [用户手册](USER_MANUAL.md), [架构文档](ARCHITECTURE.md)
- **监控功能**: [用户手册](USER_MANUAL.md), [系统架构](ARCHITECTURE.md)
- **API开发**: [API接口规范](WEB_API_SPECIFICATION.md), 各服务指南
- **策略配置**: [策略总览](strategies/README.md), 具体策略文档

### 按角色查找
- **系统管理员**: [部署指南](DEPLOYMENT_V2.md), [系统架构](ARCHITECTURE.md)
- **交易员**: [用户手册](USER_MANUAL.md), [策略文档](strategies/)
- **开发者**: [API规范](WEB_API_SPECIFICATION.md), [架构文档](ARCHITECTURE.md)
- **风控人员**: [用户手册](USER_MANUAL.md), [架构文档](ARCHITECTURE.md)

## 📞 文档反馈

### 问题反馈
- **文档错误**: 请在GitHub Issues中报告
- **内容建议**: 欢迎提交Pull Request
- **新文档需求**: 在Issues中提出需求

### 贡献指南
1. Fork项目仓库
2. 在docs目录中编辑或新增文档
3. 遵循Markdown格式规范
4. 提交Pull Request

### 文档规范
- **格式**: 使用Markdown格式
- **命名**: 使用英文大写+下划线 (如: `USER_MANUAL.md`)
- **结构**: 包含目录、正文、示例代码
- **更新**: 重大变更需要更新版本号和日期

## 🎯 文档路线图

### 短期目标 (1个月)
- [ ] 完善用户手册的v2.0内容
- [ ] 更新所有服务指南的模块路径
- [ ] 创建故障排除指南
- [ ] 完善策略开发文档

### 中期目标 (3个月)
- [ ] 创建完整的开发者指南
- [ ] 增加更多策略文档
- [ ] 建立文档自动化测试
- [ ] 创建视频教程

### 长期目标 (6个月)
- [ ] 建立在线文档网站
- [ ] 多语言文档支持
- [ ] 交互式文档体验
- [ ] 社区贡献文档

---

**文档维护**: 本文档中心由ARBIG开发团队维护，欢迎社区贡献！

**最后更新**: 2025-01-09  
**文档版本**: v2.0
