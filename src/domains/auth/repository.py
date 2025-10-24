"""
简化认证领域Repository层

根据设计文档，Repository层大幅简化：
1. 只保留2个核心Repository：AuthRepository和AuditRepository
2. 移除SMS、Session、Token等非核心Repository
3. 简化方法签名，专注于核心功能
4. 支持微信登录和游客管理的简化操作

Repository职责:
- AuthRepository: 管理Auth实体的基础CRUD操作
- AuditRepository: 管理AuthLog实体的基础操作

设计原则:
- 极简化：只保留认证核心功能
- 单一职责：每个Repository只管理一种实体
- 同步操作：删除异步操作，保持代码简洁
- 基础功能：只保留最基本的数据库操作
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlmodel import select, update
from sqlalchemy import and_, desc
from sqlmodel import Session

from .models import Auth, AuthLog


class AuthRepository:
    """
    简化的认证Repository

    专注于Auth实体的基础CRUD操作：
    - 创建用户（游客和正式用户）
    - 查找用户（通过ID或微信OpenID）
    - 升级游客账号
    - 更新登录时间

    移除的功能：
    - 复杂查询操作
    - 统计功能
    - 审计日志查询
    """

    def __init__(self, session: Session):
        self.session = session

    def create_user(
        self,
        is_guest: bool,
        wechat_openid: Optional[str]
    ) -> Auth:
        """
        创建用户

        Args:
            is_guest: 是否为游客账号
            wechat_openid: 微信OpenID（游客为None，正式用户必填）

        Returns:
            Auth: 创建的用户实体
        """
        user = Auth(
            is_guest=is_guest,
            wechat_openid=wechat_openid
        )

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        return user

    def get_by_id(self, model_class, user_id) -> Optional[Auth]:
        """
        通过ID查找用户

        Args:
            model_class: 模型类（传入Auth）
            user_id: 用户ID（UUID或字符串）

        Returns:
            Optional[Auth]: 找到的用户实体，未找到时返回None
        """
        # 将UUID转换为字符串以匹配数据库中的存储格式
        user_id_str = str(user_id) if isinstance(user_id, UUID) else user_id
        statement = select(model_class).where(model_class.id == user_id_str)
        result = self.session.execute(statement).first()
        if result:
            return result[0]  # 获取实际的实体对象
        return None

    def get_by_wechat_openid(self, wechat_openid: str) -> Optional[Auth]:
        """
        通过微信OpenID查找用户

        Args:
            wechat_openid: 微信OpenID

        Returns:
            Optional[Auth]: 找到的用户实体，未找到时返回None
        """
        statement = select(Auth).where(Auth.wechat_openid == wechat_openid)
        result = self.session.execute(statement).first()
        if result:
            return result[0]  # 获取实际的实体对象
        return None

    def upgrade_guest_account(
        self,
        user_id: UUID,
        wechat_openid: str
    ) -> Auth:
        """
        升级游客账号为正式用户

        Args:
            user_id: 游客用户ID
            wechat_openid: 微信OpenID

        Returns:
            Auth: 升级后的用户实体
        """
        # 将UUID转换为字符串以匹配数据库中的存储格式
        user_id_str = str(user_id)
        statement = (
            update(Auth)
            .where(Auth.id == user_id_str)
            .values(
                is_guest=False,
                wechat_openid=wechat_openid,
                jwt_version=Auth.jwt_version + 1,
                updated_at=datetime.now(timezone.utc)
            )
        )

        self.session.execute(statement)
        self.session.commit()

        # 返回更新后的用户
        return self.get_by_id(Auth, user_id)

    def update_last_login(self, user_id: UUID) -> None:
        """
        更新用户最后登录时间

        Args:
            user_id: 用户ID
        """
        statement = (
            update(Auth)
            .where(Auth.id == user_id)
            .values(
                last_login_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        )

        self.session.execute(statement)
        self.session.commit()


class AuditRepository:
    """
    简化的审计日志Repository

    专注于AuthLog实体的基础操作：
    - 创建审计日志

    移除的功能：
    - 复杂查询和统计
    - 日期范围查询
    - 操作类型查询
    """

    def __init__(self, session: Session):
        self.session = session

    def create_log(
        self,
        user_id: Optional[UUID],
        action: str,
        result: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> AuthLog:
        """
        创建审计日志

        Args:
            user_id: 用户ID（可为空，用于游客操作）
            action: 操作类型（login, register, upgrade, token_refresh等）
            result: 操作结果（success, failure, error）
            details: 详细信息
            ip_address: IP地址
            user_agent: 用户代理
            device_id: 设备ID（已弃用但保留用于日志）
            error_code: 错误代码

        Returns:
            AuthLog: 创建的审计日志实体
        """
        log = AuthLog(
            user_id=user_id,
            action=action,
            result=result,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            device_id=device_id,
            error_code=error_code
        )

        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)

        return log


# ===== 删除的Repository注释 =====
# 以下Repository已被删除，原因：
# - SMSRepository: 移除短信验证功能
# - TokenRepository: 移除令牌黑名单功能
# - SessionRepository: 移除会话管理功能
# - UserRepository: 合并简化为AuthRepository