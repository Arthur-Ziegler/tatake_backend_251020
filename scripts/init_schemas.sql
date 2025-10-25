-- PostgreSQL Schema分离初始化脚本
-- 为TaKeKe项目创建领域分离的Schema

-- 1. 创建数据库（如果不存在）
-- CREATE DATABASE tatake;

-- 2. 连接到tatake数据库
-- \c tatake;

-- 3. 创建领域Schema
CREATE SCHEMA IF NOT EXISTS auth_domain;
CREATE SCHEMA IF NOT EXISTS task_domain;
CREATE SCHEMA IF NOT EXISTS reward_domain;
CREATE SCHEMA IF NOT EXISTS points_domain;
CREATE SCHEMA IF NOT EXISTS top3_domain;
CREATE SCHEMA IF NOT EXISTS focus_domain;

-- 4. 创建应用用户并授权
-- CREATE USER tatake_app WITH PASSWORD 'your_secure_password';

-- 5. 为每个Schema授予应用用户权限
GRANT USAGE ON SCHEMA auth_domain TO tatake_app;
GRANT CREATE ON SCHEMA auth_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth_domain TO tatake_app;

GRANT USAGE ON SCHEMA task_domain TO tatake_app;
GRANT CREATE ON SCHEMA task_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA task_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA task_domain TO tatake_app;

GRANT USAGE ON SCHEMA reward_domain TO tatake_app;
GRANT CREATE ON SCHEMA reward_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA reward_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA reward_domain TO tatake_app;

GRANT USAGE ON SCHEMA points_domain TO tatake_app;
GRANT CREATE ON SCHEMA points_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA points_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA points_domain TO tatake_app;

GRANT USAGE ON SCHEMA top3_domain TO tatake_app;
GRANT CREATE ON SCHEMA top3_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA top3_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA top3_domain TO tatake_app;

GRANT USAGE ON SCHEMA focus_domain TO tatake_app;
GRANT CREATE ON SCHEMA focus_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA focus_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA focus_domain TO tatake_app;

-- 6. 为将来的表设置默认权限（ALTER DEFAULT PRIVILEGES）
ALTER DEFAULT PRIVILEGES IN SCHEMA auth_domain GRANT ALL ON TABLES TO tatake_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA task_domain GRANT ALL ON TABLES TO tatake_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA reward_domain GRANT ALL ON TABLES TO tatake_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA points_domain GRANT ALL ON TABLES TO tatake_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA top3_domain GRANT ALL ON TABLES TO tatake_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA focus_domain GRANT ALL ON TABLES TO tatake_app;

-- 7. 创建只读用户（用于报表和分析）
-- CREATE USER tatake_readonly WITH PASSWORD 'readonly_password';
-- GRANT USAGE ON SCHEMA auth_domain TO tatake_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA auth_domain TO tatake_readonly;
-- 对其他schema重复授权...

-- 8. 设置默认搜索路径（可选，应用代码中设置更灵活）
-- ALTER ROLE tatake_app SET search_path TO task_domain, auth_domain, reward_domain, points_domain, top3_domain, focus_domain, public;

-- 9. 验证Schema创建成功
SELECT schema_name FROM information_schema.schemata
WHERE schema_name LIKE '%_domain'
ORDER BY schema_name;

-- 输出应该显示：
-- auth_domain
-- task_domain
-- reward_domain
-- points_domain
-- top3_domain
-- focus_domain

COMMIT;