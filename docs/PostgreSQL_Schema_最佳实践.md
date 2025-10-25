# PostgreSQL Schema分离最佳实践

## 开发规范

### 1. 模型定义规范

```python
# ✅ 正确的Schema模型定义
class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    __table_args__ = (
        {"schema": "task_domain"},  # 明确指定schema
        Index('idx_task_user_id', 'user_id'),
    )

# ❌ 错误的定义
class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    # 缺少schema配置
```

### 2. 查询规范

```python
# ✅ 使用专用的查询构建器
query_builder = TaskQueryBuilder("task", tenant_id="tenant1")
tasks = query_builder.get_user_tasks(user_id)

# ❌ 避免跨schema的直接查询
# 这种查询性能较差，应避免
session.execute(
    "SELECT * FROM task_domain.tasks t JOIN auth_domain.users u ON t.user_id = u.id"
)
```

### 3. 事务规范

```python
# ✅ 使用跨领域事务管理器
with cross_domains(["task", "points", "reward"]) as sessions:
    task_session = sessions["task"]
    points_session = sessions["points"]
    # 处理业务逻辑

# ❌ 避免手动管理多个session
task_session = get_session("task")
points_session = get_session("points")
# 手动管理容易出错
```

## 性能优化

### 1. 索引策略

```sql
-- 每个schema内的索引应该独立设计
CREATE INDEX idx_task_user_status ON task_domain.tasks(user_id, status);
CREATE INDEX idx_points_user_amount ON points_domain.points_transactions(user_id, amount);
```

### 2. 查询优化

```python
# ✅ 使用Schema内的查询
# 性能更好，可维护性更高
def get_user_tasks_with_rewards(user_id: str):
    with domain_session("task") as task_session:
        tasks = task_session.query(Task).where(Task.user_id == user_id).all()

    with domain_session("reward") as reward_session:
        rewards = reward_session.query(RewardTransaction).where(
            RewardTransaction.user_id == user_id
        ).all()

    return tasks, rewards

# ❌ 避免复杂的跨schema JOIN
# 性能较差，难以优化
def get_user_tasks_with_rewards_bad(user_id: str):
    # 这种查询应该避免
    session.execute("""
        SELECT t.*, r.* FROM task_domain.tasks t
        LEFT JOIN reward_domain.reward_transactions r ON t.user_id = r.user_id
        WHERE t.user_id = :user_id
    """, {"user_id": user_id})
```

## 安全考虑

### 1. 权限管理

```sql
-- 为不同应用创建不同用户
CREATE USER tatake_app WITH PASSWORD 'secure_password';
CREATE USER tatake_readonly WITH PASSWORD 'readonly_password';

-- 按Schema授权
GRANT USAGE ON SCHEMA task_domain TO tatake_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA task_domain TO tatake_app;

GRANT USAGE ON SCHEMA task_domain TO tatake_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA task_domain TO tatake_readonly;
```

### 2. 连接安全

```python
# ✅ 使用连接池和SSL
engine = create_engine(
    "postgresql://user:pass@host:5432/db",
    pool_size=20,
    connect_args={
        "sslmode": "require",
        "sslcert": "/path/to/client-cert.pem",
        "sslkey": "/path/to/client-key.pem"
    }
)
```

## 监控和运维

### 1. 监控指标

```sql
-- Schema级别的性能监控
SELECT
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples
FROM pg_stat_user_tables
WHERE schemaname LIKE '%_domain'
ORDER BY schemaname, tablename;

-- Schema大小监控
SELECT
    schemaname,
    pg_size_pretty(SUM(pg_total_relation_size(schemaname||'.'||tablename))) as total_size
FROM pg_tables
WHERE schemaname LIKE '%_domain'
GROUP BY schemaname;
```

### 2. 备份策略

```bash
# 按Schema备份
#!/bin/bash
SCHEMAS=("auth_domain" "task_domain" "reward_domain" "points_domain" "top3_domain" "focus_domain")
DATE=$(date +%Y%m%d_%H%M%S)

for schema in "${SCHEMAS[@]}"; do
    echo "备份Schema: $schema"
    pg_dump -h localhost -U tatake_app -d tatake -n $schema > "${schema}_${DATE}.sql"
done

# 恢复Schema
psql -h localhost -U tatake_app -d tatake -f auth_domain_20231025_143000.sql
```

## 多租户最佳实践

### 1. Schema命名规范

```python
# ✅ 推荐的命名规范
TENANT_SCHEMA_PATTERN = "{tenant}_domain"
# 例如: tenant1_task_domain, tenant2_auth_domain

# ❌ 避免的命名方式
# tenant1_task, tenant2_auth (缺少_domain后缀)
```

### 2. 租户隔离

```python
# ✅ 使用Schema翻译映射
def get_tenant_session(domain: str, tenant_id: str):
    schema_translate_map = {
        None: f"{tenant_id}_{domain}_domain"
    }
    return session.execution_options(schema_translate_map=schema_translate_map)

# ✅ 租户数据隔离验证
def verify_tenant_isolation(tenant_id: str):
    with domain_session("task", tenant_id) as session:
        tasks = session.query(Task).all()
        # 验证只返回当前租户的数据
        assert all(task.tenant_id == tenant_id for task in tasks)
```

## 测试策略

### 1. 单元测试

```python
# ✅ 使用测试专用Schema
@pytest.fixture
def test_session():
    with domain_session("task", tenant_id="test_tenant") as session:
        yield session

def test_create_task(test_session):
    task = Task(user_id="test_user", title="Test Task")
    test_session.add(task)
    test_session.commit()

    assert task.id is not None
    assert task.user_id == "test_user"
```

### 2. 集成测试

```python
# ✅ 测试跨领域事务
def test_cross_domain_transaction():
    with cross_domains(["task", "points"]) as sessions:
        task_session = sessions["task"]
        points_session = sessions["points"]

        # 创建任务
        task = Task(user_id="test_user", title="Test Task")
        task_session.add(task)

        # 添加积分
        points = PointsTransaction(
            user_id="test_user",
            amount=10,
            source_type="test"
        )
        points_session.add(points)

        # 验证数据一致性
        assert task.id is not None
        assert points.id is not None
```

## 故障排查

### 1. 常见问题

```sql
-- 问题1: Schema不存在
-- 解决: 检查Schema是否创建
SELECT schema_name FROM information_schema.schemata
WHERE schema_name = 'task_domain';

-- 问题2: 权限不足
-- 解决: 检查用户权限
SELECT has_schema_privilege('tatake_app', 'task_domain', 'USAGE');

-- 问题3: 表不存在
-- 解决: 检查表是否在正确的Schema中
SELECT tablename FROM pg_tables
WHERE schemaname = 'task_domain' AND tablename = 'tasks';
```

### 2. 性能问题

```sql
-- 检查慢查询
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
WHERE query LIKE '%task_domain%'
ORDER BY mean_time DESC
LIMIT 10;

-- 检查索引使用情况
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname LIKE '%_domain';
```

## 升级和维护

### 1. Schema版本控制

```python
# 使用Alembic管理Schema迁移
def upgrade():
    # 创建新Schema
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics_domain")

    # 在新Schema中创建表
    op.create_table('analytics_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        schema='analytics_domain'
    )

def downgrade():
    op.drop_table('analytics_events', schema='analytics_domain')
    op.execute("DROP SCHEMA IF EXISTS analytics_domain")
```

### 2. 数据清理

```sql
-- 定期清理过期数据
-- 删除90天前的日志
DELETE FROM auth_domain.auth_audit_logs
WHERE created_at < NOW() - INTERVAL '90 days';

-- 清理软删除的任务
DELETE FROM task_domain.tasks
WHERE is_deleted = TRUE AND updated_at < NOW() - INTERVAL '1 year';
```

---

**版本**: v1.0
**更新时间**: 2025-10-25
**维护者**: TaKeKe团队