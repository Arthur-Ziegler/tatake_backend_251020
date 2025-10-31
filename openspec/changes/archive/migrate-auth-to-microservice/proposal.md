## Why
将现有认证系统完全迁移到外部认证微服务，实现认证逻辑与业务系统的彻底解耦，提供更丰富的认证方式（微信、邮箱、手机号），同时保持API接口的一致性和JWT本地验证能力。

## What Changes
- **BREAKING** 认证API路径变更为微服务路径格式
- **BREAKING** 移除本地认证数据库和相关代码
- **BREAKING** 删除所有本地认证相关测试文件
- 新增邮箱认证功能（注册、登录、绑定）
- 新增JWT本地验证机制（通过微服务公钥）
- 新增认证微服务透传层，自动注入project参数
- 保持现有JWT令牌认证中间件功能

## Impact
- Affected specs: None (新的认证能力)
- Affected code:
  - `src/domains/auth/` (完全删除)
  - `src/api/middleware/auth.py` (修改JWT验证)
  - `tests/unit/domains/auth/` (完全删除)
  - `tests/integration/auth/` (完全删除)