"""
测试基础 SQLModel 类
"""
import pytest
from datetime import datetime
from sqlmodel import SQLModel, Field
from typing import Optional

# 导入待实现的BaseSQLModel
from src.models.base_model import BaseSQLModel


class TestBaseSQLModel:
    """基础SQLModel类测试"""

    def test_base_sqlmodel_exists(self):
        """验证BaseSQLModel类存在且可导入"""
        assert BaseSQLModel is not None
        assert issubclass(BaseSQLModel, SQLModel)

    def test_base_sqlmodel_basic_fields(self):
        """测试基础SQLModel的基本字段"""
        # 创建一个继承自BaseSQLModel的测试模型
        class TestModel(BaseSQLModel, table=True):
            """测试模型"""
            __tablename__ = "test_models"

            name: str = Field(default="test", description="测试名称")

        # 创建实例
        model = TestModel()

        # 验证基础字段存在
        assert hasattr(model, 'id')
        assert hasattr(model, 'created_at')
        assert hasattr(model, 'updated_at')

        # 验证基础字段类型
        assert model.id is not None  # ID现在会自动生成
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

    def test_base_sqlmodel_table_configuration(self):
        """测试基础SQLModel的表配置"""
        import uuid

        class TestModel(BaseSQLModel, table=True):
            """测试模型"""
            __tablename__ = f"test_models_{uuid.uuid4().hex[:8]}"

            name: str = Field(default="test")

        # 验证表配置
        assert "test_models_" in TestModel.__tablename__
        assert TestModel.__table__.name == TestModel.__tablename__

    def test_base_sqlmodel_auto_timestamps(self):
        """测试基础SQLModel的自动时间戳"""
        import uuid

        class TestModel(BaseSQLModel, table=True):
            """测试模型"""
            __tablename__ = f"test_models_timestamp_{uuid.uuid4().hex[:8]}"

            name: str = Field(default="test")

        # 创建实例
        model1 = TestModel()
        created_at_1 = model1.created_at
        updated_at_1 = model1.updated_at

        # 等待一小段时间
        import time
        time.sleep(0.01)

        # 创建另一个实例
        model2 = TestModel()

        # 验证时间戳自动生成且不同
        assert model2.created_at > created_at_1
        assert model2.updated_at > updated_at_1

        # 验证每个实例的created_at和updated_at初始相同
        assert model1.created_at == model1.updated_at
        assert model2.created_at == model2.updated_at

    def test_base_sqlmodel_repr(self):
        """测试基础SQLModel的字符串表示"""
        import uuid

        class TestModel(BaseSQLModel, table=True):
            """测试模型"""
            __tablename__ = f"test_models_repr_{uuid.uuid4().hex[:8]}"

            name: str = Field(default="test")

        model = TestModel()
        repr_str = repr(model)

        # 验证repr包含类名和ID
        assert "TestModel" in repr_str
        assert "id=" in repr_str

    def test_base_sqlmodel_dict_conversion(self):
        """测试基础SQLModel的字典转换"""
        import uuid

        class TestModel(BaseSQLModel, table=True):
            """测试模型"""
            __tablename__ = f"test_models_dict_{uuid.uuid4().hex[:8]}"

            name: str = Field(default="test")
            description: Optional[str] = None

        model = TestModel(name="测试模型", description="测试描述")

        # 转换为字典
        model_dict = model.model_dump()

        # 验证字典包含所有字段
        assert "id" in model_dict
        assert "created_at" in model_dict
        assert "updated_at" in model_dict
        assert "name" in model_dict
        assert "description" in model_dict

        # 验证字段值
        assert model_dict["name"] == "测试模型"
        assert model_dict["description"] == "测试描述"