# 认证系统规格说明

## 概述

实现完整的用户认证系统，包括JWT令牌管理、游客模式、短信验证、微信登录等功能。移除Redis依赖，使用SQLite数据库进行所有数据存储。

## ADDED Requirements

### Requirement: JWT认证系统
系统 SHALL实现基于JWT的用户认证系统，支持访问令牌和刷新令牌机制。

#### Scenario: JWT令牌生成和验证
- **GIVEN** 用户需要登录系统
- **WHEN** 提供有效的登录凭据时
- **THEN** 系统 SHALL生成包含用户信息的JWT访问令牌
- **AND** 系统 SHALL生成对应的刷新令牌
- **AND** 访问令牌 SHALL在30分钟后过期
- **AND** 刷新令牌 SHALL在7天后过期
- **AND** 令牌 SHALL包含用户ID、权限和版本信息

#### Scenario: JWT令牌验证和黑名单
- **GIVEN** 用户访问受保护的API端点
- **WHEN** 提供JWT访问令牌时
- **THEN** 系统 SHALL验证令牌签名和有效期
- **AND** 系统 SHALL检查令牌是否在黑名单中
- **AND** 如果令牌无效或在黑名单中，系统 SHALL拒绝访问
- **AND** 系统 SHALL记录令牌验证日志

#### Scenario: 令牌刷新机制
- **GIVEN** 访问令牌即将过期或已过期
- **WHEN** 提供有效的刷新令牌时
- **THEN** 系统 SHALL生成新的访问令牌
- **AND** 系统 SHALL可选地生成新的刷新令牌
- **AND** 系统 SHALL将旧的访问令牌加入黑名单
- **AND** 系统 SHALL验证用户状态和权限

### Requirement: 游客模式认证
系统 SHALL支持游客模式，允许用户无需注册即可使用基础功能。

#### Scenario: 游客账号初始化
- **GIVEN** 新用户首次使用应用
- **WHEN** 调用游客初始化API时
- **THEN** 系统 SHALL创建临时用户账号
- **AND** 系统 SHALL生成游客标识符
- **AND** 系统 SHALL创建临时访问令牌
- **AND** 系统 SHALL记录设备信息和访问日志
- **AND** 游客账号 SHALL具有基础功能权限

#### Scenario: 游客账号升级
- **GIVEN** 游客用户希望升级为正式账号
- **WHEN** 提供升级信息（手机/邮箱/微信）时
- **THEN** 系统 SHALL验证升级信息的有效性
- **AND** 系统 SHALL将游客数据迁移到正式账号
- **AND** 系统 SHALL更新用户权限和功能
- **AND** 系统 SHALL生成新的正式令牌
- **AND** 系统 SHALL使游客令牌失效

### Requirement: 短信验证系统
系统 SHALL实现短信验证码系统，支持注册、登录、密码重置等场景。

#### Scenario: 短信验证码发送
- **GIVEN** 用户需要进行短信验证
- **WHEN** 提供手机号码时
- **THEN** 系统 SHALL验证手机号格式
- **AND** 系统 SHALL检查发送频率限制
- **AND** 系统 SHALL生成6位数字验证码
- **AND** 系统 SHALL将验证码存储到数据库
- **AND** 系统 SHALL调用Mock短信服务发送验证码
- **AND** 验证码 SHALL在5分钟后过期

#### Scenario: 短信验证码验证
- **GIVEN** 用户收到短信验证码
- **WHEN** 提供手机号和验证码时
- **THEN** 系统 SHALL验证验证码的有效性
- **AND** 系统 SHALL检查验证码是否过期
- **AND** 系统 SHALL检查尝试次数限制
- **AND** 系统 SHALL记录验证结果
- **AND** 验证成功后系统 SHALL使验证码失效

#### Scenario: 短信发送频率限制
- **GIVEN** 用户请求发送短信验证码
- **WHEN** 检查发送历史时
- **THEN** 系统 SHALL限制同一手机号1分钟内只能发送1次
- **AND** 系统 SHALL限制同一手机号1小时内最多发送5次
- **AND** 系统 SHALL限制同一手机号1天内最多发送10次
- **AND** 超出限制时系统 SHALL返回明确的错误信息

### Requirement: 微信登录集成
系统 SHALL支持微信登录，提供便捷的第三方认证方式。

#### Scenario: 微信授权登录
- **GIVEN** 用户选择微信登录
- **WHEN** 提供微信授权码时
- **THEN** 系统 SHALL调用Mock微信服务获取用户信息
- **AND** 系统 SHALL验证微信用户信息的有效性
- **AND** 系统 SHALL检查微信用户是否已注册
- **AND** 如果新用户，系统 SHALL自动创建账号
- **AND** 系统 SHALL生成JWT令牌并返回用户信息

#### Scenario: 微信账号绑定
- **GIVEN** 已有用户希望绑定微信账号
- **WHEN** 提供微信授权码时
- **THEN** 系统 SHALL验证微信用户信息
- **AND** 系统 SHALL检查微信账号是否已被绑定
- **AND** 系统 SHALL将微信账号与用户账号关联
- **AND** 系统 SHALL更新用户的登录方式选项

### Requirement: 数据库令牌管理
系统 SHALL使用SQLite数据库管理JWT令牌，替代Redis功能。

#### Scenario: 令牌黑名单管理
- **GIVEN** 用户登出或令牌需要失效
- **WHEN** 调用令牌失效操作时
- **THEN** 系统 SHALL将令牌ID添加到黑名单表
- **AND** 系统 SHALL记录令牌失效原因和时间
- **AND** 系统 SHALL设置黑名单记录的过期时间
- **AND** 系统 SHALL定期清理过期的黑名单记录

#### Scenario: 验证码数据库存储
- **GIVEN** 系统发送短信验证码
- **WHEN** 存储验证码信息时
- **THEN** 系统 SHALL将验证码存储到sms_verification表
- **AND** 系统 SHALL记录手机号、验证码、类型等信息
- **AND** 系统 SHALL设置验证码过期时间
- **AND** 系统 SHALL记录创建时间和更新时间

### Requirement: 用户信息管理
系统 SHALL提供用户信息的查询、更新和管理功能。

#### Scenario: 用户信息查询
- **GIVEN** 用户需要查看个人信息
- **WHEN** 调用用户信息API时
- **THEN** 系统 SHALL验证用户身份和权限
- **AND** 系统 SHALL返回用户基本信息
- **AND** 系统 SHALL脱敏敏感信息
- **AND** 系统 SHALL包含用户等级、积分等游戏化信息

#### Scenario: 用户信息更新
- **GIVEN** 用户需要更新个人信息
- **WHEN** 提供更新数据时
- **THEN** 系统 SHALL验证用户身份
- **AND** 系统 SHALL验证更新数据的格式和有效性
- **AND** 系统 SHALL更新用户信息
- **AND** 系统 SHALL记录更新日志
- **AND** 系统 SHALL使相关缓存失效

### Requirement: 文件上传和反馈
系统 SHALL支持头像上传和用户反馈功能。

#### Scenario: 头像文件上传
- **GIVEN** 用户希望上传头像
- **WHEN** 提供头像文件时
- **THEN** 系统 SHALL验证文件格式（jpg, png, gif）
- **AND** 系统 SHALL限制文件大小（最大2MB）
- **AND** 系统 SHALL生成缩略图
- **AND** 系统 SHALL存储文件并更新用户头像URL
- **AND** 系统 SHALL删除旧的头像文件

#### Scenario: 用户反馈提交
- **GIVEN** 用户希望提交反馈
- **WHEN** 提供反馈内容时
- **THEN** 系统 SHALL验证反馈内容格式
- **AND** 系统 SHALL分类反馈类型
- **AND** 系统 SHALL存储反馈信息
- **AND** 系统 SHALL记录反馈时间
- **AND** 系统 SHALL支持附件上传

## MODIFIED Requirements

### Requirement: 认证中间件适配
原有的认证中间件 SHALL修改以适配数据库令牌管理。

#### Scenario: 数据库令牌验证
- **GIVEN** 中间件需要验证JWT令牌
- **WHEN** 检查令牌黑名单时
- **THEN** 中间件 SHALL查询数据库黑名单表
- **AND** 中间件 SHALL移除Redis相关代码
- **AND** 中间件 SHALL优化数据库查询性能

## REMOVED Requirements

### Requirement: Redis缓存依赖
系统 SHALL移除所有Redis相关的认证缓存功能。

#### Scenario: Redis依赖清理
- **GIVEN** 系统原有Redis认证缓存
- **WHEN** 移除Redis依赖时
- **THEN** 系统 SHALL删除所有Redis相关代码
- **AND** 系统 SHALL更新配置文件
- **AND** 系统 SHALL使用数据库替代所有缓存功能

---

**规格版本**: 1.0.0
**创建日期**: 2025-10-20
**适用模块**: 认证系统API + AuthService
**依赖模块**: SQLite数据库, PyJWT, Mock SMS服务