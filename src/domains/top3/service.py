"""Top3领域Service层"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlmodel import Session

from .repository import Top3Repository
from .schemas import SetTop3Request, Top3Response, GetTop3Response
from .exceptions import Top3AlreadyExistsException, Top3NotFoundException
from .models import TaskTop3

from src.domains.reward.service import RewardService
from src.domains.reward.exceptions import InsufficientPointsException
from src.domains.points.service import PointsService
from src.domains.task.repository import TaskRepository
from src.domains.task.exceptions import TaskNotFoundException


class Top3Service:
    """Top3服务层"""

    def __init__(self, session: Session, points_service=None):
        self.session = session
        self.top3_repo = Top3Repository(session)
        self.points_service = points_service or PointsService(session)  # 注入PointsService，提供默认值
        self.task_repo = TaskRepository(session)

    def set_top3(self, user_id: UUID, request: SetTop3Request) -> Dict[str, Any]:
        """
        设置Top3任务

        校验：
        1. 日期不能重复
        2. 积分余额>=300
        3. 所有任务ID必须属于当前用户
        """
        # 解析日期
        target_date = date.fromisoformat(request.date)

        # 检查是否已设置
        existing = self.top3_repo.get_by_user_and_date(user_id, target_date)
        if existing:
            raise Top3AlreadyExistsException(request.date)

        # 检查积分（使用PointsService获取实时余额）
        current_balance = self.points_service.get_balance(user_id)
        if current_balance < 300:
            raise InsufficientPointsException(300, current_balance)

        # 检查所有任务是否存在且属于用户
        for task_id_str in request.task_ids:
            task_id = UUID(task_id_str)
            task = self.task_repo.get_by_id(str(task_id), str(user_id))
            if not task:
                raise TaskNotFoundException(task_id_str)
            if task.user_id != str(user_id):
                raise TaskNotFoundException(task_id_str)

        # 扣除积分（使用PointsService）
        self.points_service.add_points(
            user_id=user_id,
            amount=-300,  # 负数表示扣除
            source_type="top3_cost"
        )

        # 创建Top3记录
        top3 = self.top3_repo.create(user_id, target_date, request.task_ids)

        # 计算剩余余额
        remaining_balance = current_balance - 300

        # 提取task_id字符串列表，处理两种数据格式
        task_id_strings = []
        for item in top3.task_ids:
            if isinstance(item, dict):
                # 新格式：{"task_id": "uuid", "position": 1}
                task_id_strings.append(item["task_id"])
            else:
                # 旧格式：直接是task_id字符串
                task_id_strings.append(item)

        return {
            "date": top3.top_date.isoformat(),
            "task_ids": task_id_strings,
            "points_consumed": top3.points_consumed,
            "remaining_balance": remaining_balance  # 新增字段
        }

    def get_user_top3(self, user_id: UUID, target_date: date) -> Optional[Dict[str, Any]]:
        """获取用户指定日期的Top3记录"""
        return self.top3_repo.get_by_user_and_date(user_id, target_date)

    def get_top3(self, user_id: UUID, target_date_str: str) -> Dict[str, Any]:
        """获取指定日期的Top3"""
        target_date = date.fromisoformat(target_date_str)
        top3 = self.top3_repo.get_by_user_and_date(user_id, target_date)

        if not top3:
            # 返回空的Top3响应，而不是抛出异常
            return {
                "date": target_date_str,
                "task_ids": [],
                "points_consumed": 0,
                "created_at": None
            }

        # 提取task_id字符串列表，处理两种数据格式
        task_id_strings = []
        for item in top3.task_ids:
            if isinstance(item, dict):
                # 新格式：{"task_id": "uuid", "position": 1}
                task_id_strings.append(item["task_id"])
            else:
                # 旧格式：直接是task_id字符串
                task_id_strings.append(item)

        return {
            "date": top3.top_date.isoformat(),
            "task_ids": task_id_strings,
            "points_consumed": top3.points_consumed,
            "created_at": top3.created_at.isoformat()
        }

    def is_task_in_today_top3(self, user_id: str, task_id: str) -> bool:
        """
        检查指定任务是否在用户今日的Top3列表中

        Args:
            user_id (str): 用户ID
            task_id (str): 任务ID

        Returns:
            bool: 如果任务在今日Top3中返回True，否则返回False
        """
        # 获取今日日期
        today = date.today()

        # 获取用户今日的Top3记录
        today_top3 = self.top3_repo.get_by_user_and_date(UUID(user_id), today)

        # 如果今日没有设置Top3，返回False
        if not today_top3:
            return False

        # 检查任务是否在今日Top3的任务列表中
        # task_ids存储的是JSON字符串列表，需要解析
        today_task_ids = today_top3.task_ids if today_top3.task_ids else []

        # task_ids可能是 [{"task_id": "xxx"}, ...] 格式或者是直接的字符串列表
        for task_item in today_task_ids:
            if isinstance(task_item, dict):
                # 如果是字典格式，提取task_id字段
                if task_item.get("task_id") == task_id:
                    return True
            elif isinstance(task_item, str):
                # 如果是字符串格式，直接比较
                if task_item == task_id:
                    return True

        return False
