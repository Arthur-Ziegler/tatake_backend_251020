"""
BaseService基类测试

测试服务层基类的功能和行为，确保基础服务功能正常工作。
遵循TDD原则，验证依赖注入、日志记录、异常处理、通用方法等功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import logging

from src.services.base import BaseService, ServiceFactory
from src.services.exceptions import (
    BusinessException,
    ResourceNotFoundException,
    ValidationException
)
from src.repositories.base import RepositoryNotFoundError, RepositoryValidationError


class TestBaseServiceInitialization:
    """BaseService初始化测试"""

    def test_base_service_initialization_with_all_repositories(self, mock_user_repo, mock_task_repo, mock_focus_repo, mock_reward_repo):
        """测试使用所有Repository初始化BaseService"""
        service = BaseService(
            user_repo=mock_user_repo,
            task_repo=mock_task_repo,
            focus_repo=mock_focus_repo,
            reward_repo=mock_reward_repo
        )

        assert service._user_repo is mock_user_repo
        assert service._task_repo is mock_task_repo
        assert service._focus_repo is mock_focus_repo
        assert service._reward_repo is mock_reward_repo
        assert service._service_name == "BaseService"
        assert service._logger is not None

    def test_base_service_initialization_partial_repositories(self, mock_user_repo):
        """测试部分Repository初始化BaseService"""
        service = BaseService(user_repo=mock_user_repo)

        assert service._user_repo is mock_user_repo
        assert service._task_repo is None
        assert service._focus_repo is None
        assert service._reward_repo is None

    def test_base_service_initialization_no_repositories(self):
        """测试无Repository初始化BaseService"""
        service = BaseService()

        assert service._user_repo is None
        assert service._task_repo is None
        assert service._focus_repo is None
        assert service._reward_repo is None

    @patch('src.services.base.logger')
    def test_base_service_logging_on_initialization(self, mock_logger, mock_user_repo):
        """测试初始化时的日志记录"""
        BaseService(user_repo=mock_user_repo)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "BaseService: Service initialized" in call_args[0][0]
        assert "BaseService" in call_args[1]["extra"]["service"]
        assert call_args[1]["extra"]["repositories"]["user_repo"] is True


class TestBaseServiceLogging:
    """BaseService日志记录测试"""

    def test_log_info(self, base_service):
        """测试信息日志记录"""
        with patch.object(base_service, '_logger') as mock_logger:
            message = "Test info message"
            context = {"user_id": "123", "action": "test"}

            base_service._log_info(message, context)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "BaseService: Test info message" in call_args[0][0]
            assert call_args[1]["extra"]["service"] == "BaseService"
            assert call_args[1]["extra"]["user_id"] == "123"
            assert call_args[1]["extra"]["action"] == "test"
            assert "timestamp" in call_args[1]["extra"]

    def test_log_warning(self, base_service):
        """测试警告日志记录"""
        with patch.object(base_service, '_logger') as mock_logger:
            message = "Test warning message"
            context = {"warning_type": "test"}

            base_service._log_warning(message, context)

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "BaseService: Test warning message" in call_args[0][0]
            assert call_args[1]["extra"]["warning_type"] == "test"

    def test_log_error_without_exception(self, base_service):
        """测试无异常的错误日志记录"""
        with patch.object(base_service, '_logger') as mock_logger:
            message = "Test error message"
            context = {"error_code": "TEST_ERROR"}

            base_service._log_error(message, context=context)

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "BaseService: Test error message" in call_args[0][0]
            assert call_args[1]["extra"]["error_code"] == "TEST_ERROR"
            assert "error_type" not in call_args[1]["extra"]
            assert call_args[1]["exc_info"] is None

    def test_log_error_with_exception(self, base_service):
        """测试带异常的错误日志记录"""
        with patch.object(base_service, '_logger') as mock_logger:
            message = "Test error message"
            error = ValueError("Test exception")
            context = {"error_code": "TEST_ERROR"}

            base_service._log_error(message, error, context)

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "BaseService: Test error message" in call_args[0][0]
            assert call_args[1]["extra"]["error_type"] == "ValueError"
            assert call_args[1]["extra"]["error_message"] == "Test exception"
            assert call_args[1]["exc_info"] is error


class TestBaseServiceExceptionHandling:
    """BaseService异常处理测试"""

    def test_handle_repository_error_with_not_found_error(self, base_service):
        """测试处理RepositoryNotFoundError"""
        repo_error = RepositoryNotFoundError("User not found")
        operation = "get_user"
        context = {"user_id": "123"}

        with pytest.raises(ResourceNotFoundException) as exc_info:
            base_service._handle_repository_error(repo_error, operation, context)

        exception = exc_info.value
        assert isinstance(exception, ResourceNotFoundException)
        assert exception.cause == repo_error
        assert exception.details["user_id"] == "123"

    def test_handle_repository_error_with_validation_error(self, base_service):
        """测试处理RepositoryValidationError"""
        repo_error = RepositoryValidationError("Invalid email")
        operation = "create_user"
        context = {"email": "invalid"}

        with pytest.raises(ValidationException) as exc_info:
            base_service._handle_repository_error(repo_error, operation, context)

        exception = exc_info.value
        assert isinstance(exception, ValidationException)
        assert exception.cause == repo_error

    def test_handle_repository_error_with_generic_error(self, base_service):
        """测试处理通用异常"""
        generic_error = ValueError("Generic error")
        operation = "some_operation"
        context = {"test": True}

        with pytest.raises(BusinessException) as exc_info:
            base_service._handle_repository_error(generic_error, operation, context)

        exception = exc_info.value
        assert isinstance(exception, BusinessException)
        assert exception.error_code == "SERVICE_REPOSITORY_ERROR"
        assert exception.cause == generic_error
        assert exception.details["test"] is True

    def test_handle_repository_error_logs_error(self, base_service):
        """测试异常处理时记录错误日志"""
        with patch.object(base_service, '_log_error') as mock_log_error:
            error = ValueError("Test error")
            operation = "test_operation"
            context = {"test": True}

            with pytest.raises(BusinessException):
                base_service._handle_repository_error(error, operation, context)

            mock_log_error.assert_called_once_with(
                f"Repository error in {operation}",
                error,
                context
            )


class TestBaseServiceParameterValidation:
    """BaseService参数验证测试"""

    def test_validate_required_params_success(self, base_service):
        """测试必需参数验证成功"""
        params = {"email": "test@example.com", "password": "secret123"}
        required_fields = ["email", "password"]

        # 应该不抛出异常
        base_service._validate_required_params(params, required_fields)

    def test_validate_required_params_missing_field(self, base_service):
        """测试必需参数验证失败 - 缺少字段"""
        params = {"email": "test@example.com"}
        required_fields = ["email", "password"]

        with pytest.raises(ValidationException) as exc_info:
            base_service._validate_required_params(params, required_fields)

        exception = exc_info.value
        assert "Missing required parameters" in exception.message
        assert "password" in exception.details["missing_fields"]
        assert "email" not in exception.details["missing_fields"]

    def test_validate_required_params_none_value(self, base_service):
        """测试必需参数验证失败 - None值"""
        params = {"email": None, "password": "secret123"}
        required_fields = ["email", "password"]

        with pytest.raises(ValidationException) as exc_info:
            base_service._validate_required_params(params, required_fields)

        exception = exc_info.value
        assert "email" in exception.details["missing_fields"]

    def test_validate_required_params_empty_params(self, base_service):
        """测试必需参数验证失败 - 空参数"""
        params = {}
        required_fields = ["email", "password"]

        with pytest.raises(ValidationException) as exc_info:
            base_service._validate_required_params(params, required_fields)

        exception = exc_info.value
        assert set(exception.details["missing_fields"]) == {"email", "password"}


class TestBaseServiceUtilityMethods:
    """BaseService工具方法测试"""

    def test_check_resource_exists_success(self, base_service, mock_user_repo, mock_user):
        """检查资源存在 - 成功"""
        mock_user_repo.get_by_id.return_value = mock_user

        result = base_service._check_resource_exists(mock_user_repo, "user123", "User")

        assert result == mock_user
        mock_user_repo.get_by_id.assert_called_once_with("user123")

    def test_check_resource_exists_not_found(self, base_service, mock_user_repo):
        """检查资源存在 - 未找到"""
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundException) as exc_info:
            base_service._check_resource_exists(mock_user_repo, "user123", "User")

        exception = exc_info.value
        assert exception.details["resource_type"] == "User"
        assert exception.details["resource_id"] == "user123"

    def test_check_resource_exists_repository_error(self, base_service, mock_user_repo):
        """检查资源存在 - Repository错误"""
        mock_user_repo.get_by_id.side_effect = ValueError("Database error")

        with pytest.raises(BusinessException) as exc_info:
            base_service._check_resource_exists(mock_user_repo, "user123", "User")

        exception = exc_info.value
        assert exception.error_code == "SERVICE_REPOSITORY_ERROR"

    def test_paginate_results(self, base_service, mock_user_repo):
        """测试分页查询"""
        # 模拟Repository返回数据
        mock_user_repo.count.return_value = 25
        mock_user_repo.find_many.return_value = ["user1", "user2", "user3"]

        result = base_service._paginate_results(
            mock_user_repo,
            page=2,
            per_page=10,
            status="active"
        )

        # 验证调用参数
        mock_user_repo.count.assert_called_once_with(status="active")
        mock_user_repo.find_many.assert_called_once_with(limit=10, offset=10, status="active")

        # 验证返回结果
        assert result["items"] == ["user1", "user2", "user3"]
        pagination = result["pagination"]
        assert pagination["page"] == 2
        assert pagination["per_page"] == 10
        assert pagination["total_count"] == 25
        assert pagination["total_pages"] == 3  # ceil(25/10)
        assert pagination["has_next"] is True
        assert pagination["has_prev"] is True

    def test_paginate_results_first_page(self, base_service, mock_user_repo):
        """测试分页查询 - 第一页"""
        mock_user_repo.count.return_value = 5
        mock_user_repo.find_many.return_value = ["user1", "user2"]

        result = base_service._paginate_results(mock_user_repo, page=1, per_page=10)

        pagination = result["pagination"]
        assert pagination["has_next"] is False
        assert pagination["has_prev"] is False
        assert pagination["total_pages"] == 1

    def test_execute_in_transaction_success(self, base_service):
        """测试事务执行 - 成功"""
        operation_func = Mock(return_value="success")
        operation_func.__name__ = "test_operation"

        with patch.object(base_service, '_log_info') as mock_log_info:
            result = base_service._execute_in_transaction(operation_func, arg1="value1")

        assert result == "success"
        operation_func.assert_called_once_with(arg1="value1")
        assert mock_log_info.call_count == 2  # 开始和完成

    def test_execute_in_transaction_failure(self, base_service):
        """测试事务执行 - 失败"""
        error = ValueError("Operation failed")
        operation_func = Mock(side_effect=error)
        operation_func.__name__ = "test_operation"

        with patch.object(base_service, '_log_info') as mock_log_info:
            with patch.object(base_service, '_log_error') as mock_log_error:
                with pytest.raises(BusinessException):
                    base_service._execute_in_transaction(operation_func)

        mock_log_info.assert_called_once()  # 只有开始日志
        assert mock_log_error.call_count == 2  # Transaction failed 和 Repository error

    def test_execute_in_transaction_business_exception(self, base_service):
        """测试事务执行 - 业务异常"""
        business_error = BusinessException("SERVICE_TEST_ERROR", "Test error")
        operation_func = Mock(side_effect=business_error)
        operation_func.__name__ = "test_operation"

        with pytest.raises(BusinessException) as exc_info:
            base_service._execute_in_transaction(operation_func)

        assert exc_info.value is business_error  # 应该重新抛出相同的异常

    def test_to_dict_with_object(self, base_service):
        """测试对象转字典"""
        mock_obj = Mock()
        mock_obj.to_dict.return_value = {"id": "123", "name": "test"}

        result = base_service._to_dict(mock_obj)

        assert result == {"id": "123", "name": "test"}
        mock_obj.to_dict.assert_called_once()

    def test_to_dict_without_to_dict_method(self, base_service):
        """测试无to_dict方法的对象转字典"""
        class TestObject:
            def __init__(self):
                self.id = "123"
                self.name = "test"
                self._private = "secret"

        obj = TestObject()
        result = base_service._to_dict(obj)

        assert result == {"id": "123", "name": "test", "_private": "secret"}

    def test_to_dict_with_exclude_fields(self, base_service):
        """测试排除字段的对象转字典"""
        mock_obj = Mock()
        mock_obj.to_dict.return_value = {"id": "123", "name": "test", "password": "secret"}

        result = base_service._to_dict(mock_obj, exclude_fields=["password"])

        assert result == {"id": "123", "name": "test"}

    def test_filter_sensitive_data(self, base_service):
        """测试敏感数据过滤"""
        data = {
            "id": "123",
            "email": "test@example.com",
            "password_hash": "secret123",
            "token": "abc123"
        }

        result = base_service._filter_sensitive_data(data)

        assert result["id"] == "123"
        assert result["email"] == "test@example.com"
        assert result["password_hash"] == "***"
        assert result["token"] == "***"

    def test_filter_sensitive_data_custom_fields(self, base_service):
        """测试自定义敏感字段过滤"""
        data = {
            "id": "123",
            "email": "test@example.com",
            "custom_secret": "secret_value"
        }

        result = base_service._filter_sensitive_data(
            data,
            sensitive_fields=["custom_secret"]
        )

        assert result["id"] == "123"
        assert result["email"] == "test@example.com"
        assert result["custom_secret"] == "***"


class TestBaseServiceDependencyManagement:
    """BaseService依赖管理测试"""

    def test_ensure_repository_success(self, base_service, mock_user_repo):
        """测试确保Repository存在 - 成功"""
        base_service._user_repo = mock_user_repo

        result = base_service._ensure_repository("user_repo")

        assert result is mock_user_repo

    def test_ensure_repository_missing(self):
        """测试确保Repository存在 - 缺失"""
        # 创建一个没有user_repo的服务实例
        service = BaseService()  # 没有注入任何repository

        with pytest.raises(BusinessException) as exc_info:
            service._ensure_repository("user_repo")

        exception = exc_info.value
        assert exception.error_code == "SERVICE_DEPENDENCY_MISSING"
        assert "user_repo" in exception.details["missing_repository"]

    def test_get_user_repository(self, base_service, mock_user_repo):
        """测试获取用户Repository"""
        base_service._user_repo = mock_user_repo

        result = base_service.get_user_repository()

        assert result is mock_user_repo

    def test_get_task_repository_missing(self):
        """测试获取任务Repository - 缺失"""
        # 创建一个没有task_repo的服务实例
        service = BaseService()  # 没有注入任何repository

        with pytest.raises(BusinessException) as exc_info:
            service.get_task_repository()

        exception = exc_info.value
        assert exception.error_code == "SERVICE_DEPENDENCY_MISSING"


class TestServiceFactory:
    """ServiceFactory测试"""

    def test_create_service_with_all_repositories(self, mock_user_repo, mock_task_repo, mock_focus_repo, mock_reward_repo):
        """测试创建包含所有Repository的服务"""
        service = ServiceFactory.create_service(
            BaseService,
            user_repo=mock_user_repo,
            task_repo=mock_task_repo,
            focus_repo=mock_focus_repo,
            reward_repo=mock_reward_repo
        )

        assert isinstance(service, BaseService)
        assert service._user_repo is mock_user_repo
        assert service._task_repo is mock_task_repo
        assert service._focus_repo is mock_focus_repo
        assert service._reward_repo is mock_reward_repo

    def test_create_service_partial_repositories(self, mock_user_repo):
        """测试创建部分Repository的服务"""
        service = ServiceFactory.create_service(
            BaseService,
            user_repo=mock_user_repo
        )

        assert isinstance(service, BaseService)
        assert service._user_repo is mock_user_repo
        assert service._task_repo is None

    def test_create_service_with_session(self, temp_db_session):
        """测试使用数据库会话创建服务"""
        with patch('src.services.base.UserRepository') as mock_user_repo_class, \
             patch('src.services.base.TaskRepository') as mock_task_repo_class, \
             patch('src.services.base.FocusRepository') as mock_focus_repo_class, \
             patch('src.services.base.RewardRepository') as mock_reward_repo_class:

            # 配置Mock构造函数
            mock_user_repo = Mock()
            mock_task_repo = Mock()
            mock_focus_repo = Mock()
            mock_reward_repo = Mock()

            mock_user_repo_class.return_value = mock_user_repo
            mock_task_repo_class.return_value = mock_task_repo
            mock_focus_repo_class.return_value = mock_focus_repo
            mock_reward_repo_class.return_value = mock_reward_repo

            service = ServiceFactory.create_service_with_session(BaseService, temp_db_session)

            assert isinstance(service, BaseService)
            mock_user_repo_class.assert_called_once_with(temp_db_session)
            mock_task_repo_class.assert_called_once_with(temp_db_session)
            mock_focus_repo_class.assert_called_once_with(temp_db_session)
            mock_reward_repo_class.assert_called_once_with(temp_db_session)

    def test_create_service_with_session_none(self):
        """测试使用None会话创建服务"""
        service = ServiceFactory.create_service_with_session(BaseService, None)

        assert isinstance(service, BaseService)
        assert service._user_repo is None
        assert service._task_repo is None


@pytest.mark.unit
class TestBaseServicePerformance:
    """BaseService性能测试"""

    def test_logging_performance(self, base_service, performance_monitor):
        """测试日志记录性能"""
        with performance_monitor("logging", max_time_seconds=0.1):
            for i in range(1000):
                base_service._log_info(f"Test message {i}", {"iteration": i})

    def test_validation_performance(self, base_service, performance_monitor):
        """测试参数验证性能"""
        params = {"email": "test@example.com", "password": "secret123", "name": "Test User"}
        required_fields = ["email", "password", "name"]

        with performance_monitor("validation", max_time_seconds=0.05):
            for _ in range(1000):
                base_service._validate_required_params(params, required_fields)

    def test_data_transformation_performance(self, base_service, performance_monitor):
        """测试数据转换性能"""
        mock_obj = Mock()
        mock_obj.to_dict.return_value = {"id": "123", "name": "test", "email": "test@example.com"}

        with performance_monitor("data_transformation", max_time_seconds=0.1):
            for _ in range(1000):
                base_service._to_dict(mock_obj)
                base_service._filter_sensitive_data(mock_obj.to_dict())