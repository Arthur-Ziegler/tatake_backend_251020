"""Top3领域Repository层"""

from datetime import date
from typing import Optional, List, Union
from uuid import UUID

from sqlmodel import Session, select

from src.core.uuid_converter import UUIDConverter
from .models import TaskTop3


class Top3Repository:
    """Top3仓储"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_user_and_date(self, user_id: Union[UUID, str], target_date: date) -> Optional[TaskTop3]:
        """根据用户和日期获取Top3"""
        user_id_str = UUIDConverter.ensure_string(user_id)
        statement = select(TaskTop3).where(
            TaskTop3.user_id == user_id_str,
            TaskTop3.top_date == target_date
        )
        # 使用.scalars().first()直接获取模型对象
        result = self.session.execute(statement).scalars().first()
        return result

    def create(self, user_id: Union[UUID, str], target_date: date, task_ids: List[str]) -> TaskTop3:
        """创建Top3记录"""
        # 转换task_ids格式为List[Dict[str, Any]]
        formatted_task_ids = [
            {"task_id": task_id, "position": i + 1}
            for i, task_id in enumerate(task_ids)
        ]

        top3 = TaskTop3(
            user_id=UUIDConverter.ensure_string(user_id),
            top_date=target_date,
            task_ids=formatted_task_ids,
            points_consumed=300
        )
        self.session.add(top3)
        self.session.commit()
        self.session.refresh(top3)
        return top3

    def is_task_in_today_top3(self, user_id: Union[UUID, str], task_id: Union[UUID, str]) -> bool:
        """检查任务是否在今天的Top3中"""
        today = date.today()
        top3 = self.get_by_user_and_date(user_id, today)
        if not top3:
            return False

        # 处理两种数据格式：旧格式（字符串数组）和新格式（对象数组）
        task_ids = top3.task_ids
        if not task_ids:
            return False

        task_id_str = UUIDConverter.ensure_string(task_id)

        # 检查是否是新格式（对象数组）
        if task_ids and isinstance(task_ids[0], dict):
            # 新格式：[{'task_id': 'uuid', 'position': 1}]
            return any(item.get('task_id') == task_id_str for item in task_ids)
        else:
            # 旧格式：['uuid']
            return task_id_str in task_ids
