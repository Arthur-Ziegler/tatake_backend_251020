"""
Task领域测试夹具配置

提供测试所需的公共夹具（fixtures），包括：
1. 测试数据库会话
2. 测试用户数据
3. 测试任务数据
4. FastAPI测试客户端

设计原则：
1. 隔离性：每个测试都使用独立的数据库状态
2. 可配置：支持不同测试场景的配置
3. 重复性：确保测试结果可重复
4. 性能：合理的测试数据规模

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone, timedelta
from typing import Generator, Dict, Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy import StaticPool

from src.api.main import app
from src.database.connection import get_session
from src.domains.auth.models import Auth
from src.domains.task.models import Task, TaskStatus, TaskPriority


# 测试数据库配置
@pytest.fixture(scope="function")
def test_db_session() -> Generator[Session, None, None]:
    """
    创建测试数据库会话

    使用内存SQLite数据库进行测试，确保测试之间的隔离性。
    每个测试函数都会获得一个全新的数据库实例。

    Yields:
        Session: 数据库会话
    """
    # 创建临时内存数据库
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )

    # 创建所有表
    SQLModel.metadata.create_all(engine)

    # 创建会话
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="function")
def test_user(test_db_session: Session) -> Auth:
    """
    创建测试用户

    在测试数据库中创建一个测试用户，用于任务相关的测试。

    Args:
        test_db_session (Session): 测试数据库会话

    Returns:
        Auth: 测试用户实体
    """
    user = Auth(
        wechat_openid=f"test_openid_{uuid4().hex[:8]}",
        is_guest=False,
        jwt_version=1
    )

    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)

    return user


@pytest.fixture(scope="function")
def test_user_list(test_db_session: Session) -> list[Auth]:
    """
    创建多个测试用户

    创建3个测试用户，用于多用户场景的测试。

    Args:
        test_db_session (Session): 测试数据库会话

    Returns:
        list[Auth]: 测试用户列表
    """
    users = []
    for i in range(3):
        user = Auth(
            wechat_openid=f"test_user_{i}_{uuid4().hex[:8]}",
            is_guest=False,
            jwt_version=1
        )
        test_db_session.add(user)
        users.append(user)

    test_db_session.commit()

    # 刷新所有用户以获取ID
    for user in users:
        test_db_session.refresh(user)

    return users


@pytest.fixture(scope="function")
def test_task_data() -> Dict[str, Any]:
    """
    提供测试任务数据

    返回标准的测试任务数据字典，用于创建测试任务。

    Returns:
        Dict[str, Any]: 测试任务数据
    """
    return {
        "title": "测试任务",
        "description": "这是一个用于测试的任务",
        "status": TaskStatus.PENDING,
        "priority": TaskPriority.MEDIUM,
        "tags": ["测试", "示例"],
        "due_date": datetime.now(timezone.utc) + timedelta(days=7),
        "planned_start_time": datetime.now(timezone.utc) + timedelta(hours=1),
        "planned_end_time": datetime.now(timezone.utc) + timedelta(hours=3)
    }


@pytest.fixture(scope="function")
def test_task(test_db_session: Session, test_user: Auth, test_task_data: Dict[str, Any]) -> Task:
    """
    创建测试任务

    在测试数据库中创建一个测试任务，关联到指定的测试用户。

    Args:
        test_db_session (Session): 测试数据库会话
        test_user (Auth): 测试用户
        test_task_data (Dict[str, Any]): 测试任务数据

    Returns:
        Task: 测试任务实体
    """
    task = Task(
        user_id=test_user.id,
        **test_task_data
    )

    test_db_session.add(task)
    test_db_session.commit()
    test_db_session.refresh(task)

    return task


@pytest.fixture(scope="function")
def test_task_list(test_db_session: Session, test_user: Auth) -> list[Task]:
    """
    创建多个测试任务

    为指定用户创建5个不同状态的任务，用于列表查询测试。

    Args:
        test_db_session (Session): 测试数据库会话
        test_user (Auth): 测试用户

    Returns:
        list[Task]: 测试任务列表
    """
    tasks = []
    base_time = datetime.now(timezone.utc)

    task_configs = [
        {
            "title": "待处理任务",
            "status": TaskStatus.PENDING,
            "priority": TaskPriority.HIGH,
            "tags": ["重要", "紧急"],
            "due_date": base_time + timedelta(days=1)
        },
        {
            "title": "进行中任务",
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.MEDIUM,
            "tags": ["开发"],
            "due_date": base_time + timedelta(days=3)
        },
        {
            "title": "已完成任务",
            "status": TaskStatus.COMPLETED,
            "priority": TaskPriority.LOW,
            "tags": ["已完成"],
            "due_date": base_time + timedelta(days=5)
        },
        {
            "title": "子任务1",
            "status": TaskStatus.PENDING,
            "priority": TaskPriority.MEDIUM,
            "tags": ["子任务"],
            "due_date": base_time + timedelta(days=2)
        },
        {
            "title": "子任务2",
            "status": TaskStatus.PENDING,
            "priority": TaskPriority.LOW,
            "tags": ["子任务"],
            "due_date": base_time + timedelta(days=4)
        }
    ]

    for i, config in enumerate(task_configs):
        task = Task(
            user_id=test_user.id,
            description=f"这是第{i+1}个测试任务的描述",
            created_at=base_time + timedelta(minutes=i*10),
            updated_at=base_time + timedelta(minutes=i*10 + 5),
            **config
        )
        tasks.append(task)
        test_db_session.add(task)

    # 设置父子关系：子任务1 -> 子任务2 -> 待处理任务
    tasks[3].parent_id = tasks[4].id  # 子任务1的父任务是子任务2
    tasks[4].parent_id = tasks[0].id  # 子任务2的父任务是待处理任务

    test_db_session.commit()

    # 刷新所有任务以获取ID
    for task in tasks:
        test_db_session.refresh(task)

    return tasks


@pytest.fixture(scope="function")
def test_task_tree(test_db_session: Session, test_user: Auth) -> Dict[str, Task]:
    """
    创建测试任务树

    创建一个三层任务树结构，用于测试父子关系和级联操作。

    结构：
    - 根任务
      - 子任务1
        - 孙任务1
        - 孙任务2
      - 子任务2

    Args:
        test_db_session (Session): 测试数据库会话
        test_user (Auth): 测试用户

    Returns:
        Dict[str, Task]: 任务字典，包含根任务、子任务和孙任务
    """
    base_time = datetime.now(timezone.utc)

    # 创建根任务
    root_task = Task(
        user_id=test_user.id,
        title="根任务",
        description="这是根任务",
        status=TaskStatus.PENDING,
        priority=TaskPriority.HIGH,
        tags=["根任务"],
        created_at=base_time,
        updated_at=base_time
    )
    test_db_session.add(root_task)
    test_db_session.flush()  # 获取ID但不提交

    # 创建子任务1
    child1_task = Task(
        user_id=test_user.id,
        title="子任务1",
        description="这是子任务1",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.MEDIUM,
        parent_id=root_task.id,
        tags=["子任务"],
        created_at=base_time + timedelta(minutes=5),
        updated_at=base_time + timedelta(minutes=5)
    )
    test_db_session.add(child1_task)
    test_db_session.flush()

    # 创建子任务2
    child2_task = Task(
        user_id=test_user.id,
        title="子任务2",
        description="这是子任务2",
        status=TaskStatus.PENDING,
        priority=TaskPriority.LOW,
        parent_id=root_task.id,
        tags=["子任务"],
        created_at=base_time + timedelta(minutes=10),
        updated_at=base_time + timedelta(minutes=10)
    )
    test_db_session.add(child2_task)
    test_db_session.flush()

    # 创建孙任务1
    grandchild1_task = Task(
        user_id=test_user.id,
        title="孙任务1",
        description="这是孙任务1",
        status=TaskStatus.COMPLETED,
        priority=TaskPriority.LOW,
        parent_id=child1_task.id,
        tags=["孙任务"],
        created_at=base_time + timedelta(minutes=15),
        updated_at=base_time + timedelta(minutes=15)
    )
    test_db_session.add(grandchild1_task)
    test_db_session.flush()

    # 创建孙任务2
    grandchild2_task = Task(
        user_id=test_user.id,
        title="孙任务2",
        description="这是孙任务2",
        status=TaskStatus.PENDING,
        priority=TaskPriority.MEDIUM,
        parent_id=child1_task.id,
        tags=["孙任务"],
        created_at=base_time + timedelta(minutes=20),
        updated_at=base_time + timedelta(minutes=20)
    )
    test_db_session.add(grandchild2_task)

    test_db_session.commit()

    # 刷新所有任务
    for task in [root_task, child1_task, child2_task, grandchild1_task, grandchild2_task]:
        test_db_session.refresh(task)

    return {
        "root": root_task,
        "child1": child1_task,
        "child2": child2_task,
        "grandchild1": grandchild1_task,
        "grandchild2": grandchild2_task
    }


@pytest.fixture(scope="function")
def test_client(test_db_session: Session) -> Generator[TestClient, None, None]:
    """
    创建FastAPI测试客户端

    创建一个配置了测试数据库的FastAPI测试客户端。

    Args:
        test_db_session (Session): 测试数据库会话

    Yields:
        TestClient: FastAPI测试客户端
    """
    # 重写数据库依赖
    def override_get_session():
        yield test_db_session

    # 重写用户ID依赖（模拟认证）
    def override_get_current_user_id():
        return test_db_session.exec(
            "SELECT id FROM auth LIMIT 1"
        ).first() or uuid4()

    # 应用依赖重写
    app.dependency_overrides[get_session] = override_get_session
    try:
        from src.api.dependencies import get_current_user_id
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    except ImportError:
        pass  # 依赖不存在时忽略

    # 创建测试客户端
    with TestClient(app) as client:
        yield client

    # 清理依赖重写
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(test_user: Auth) -> Dict[str, str]:
    """
    创建认证请求头

    为测试用户创建模拟的JWT认证请求头。

    Args:
        test_user (Auth): 测试用户

    Returns:
        Dict[str, str]: 包含Authorization的请求头
    """
    # 在实际测试中，这里应该生成真实的JWT token
    # 为了简化测试，使用模拟token
    return {
        "Authorization": f"Bearer mock_token_for_user_{test_user.id}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="function")
def invalid_headers() -> Dict[str, str]:
    """
    创建无效认证请求头

    返回无效的认证请求头，用于测试认证失败场景。

    Returns:
        Dict[str, str]: 无效的请求头
    """
    return {
        "Authorization": "Bearer invalid_token",
        "Content-Type": "application/json"
    }