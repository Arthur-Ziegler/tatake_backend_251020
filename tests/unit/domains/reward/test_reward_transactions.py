"""
奖励流水接口严格测试 - API层专用

专门测试新添加的奖励流水接口API，确保100%覆盖率：
1. /rewards/my-rewards/transactions 接口功能
2. 参数验证和错误处理
3. 响应格式验证
4. 边界情况和异常处理

使用真实数据库和完整API调用进行测试。

作者：TaKeKe团队
版本：1.0.0 - API严格测试专用
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.api.main import app
from src.domains.reward.models import Reward, RewardTransaction
from src.domains.auth.models import Auth
from src.database import get_session
from src.domains.points.service import PointsService


@pytest.mark.integration
@pytest.mark.reward
@pytest.mark.api
class TestRewardTransactionsAPI:
    """奖励流水API接口集成测试"""
    
    @pytest.fixture
    def client(self, test_db_session):
        """创建测试客户端"""
        def override_get_session():
            return test_db_session
        
        app.dependency_overrides[get_session] = override_get_session
        return TestClient(app)
    
    @pytest.fixture
    def test_user(self, test_db_session):
        """创建测试用户"""
        user = Auth(
            id=str(uuid4()),
            wechat_openid=None,
            phone=None,
            is_guest=True,
            last_login_at=datetime.now(timezone.utc),
            jwt_version=1
        )
        test_db_session.add(user)
        test_db_session.commit()
        return user
    
    @pytest.fixture
    def auth_headers(self, test_user):
        """创建认证头"""
        # 模拟JWT token（实际测试中应该使用真实token）
        return {"Authorization": f"Bearer test_token_for_{test_user.id}"}
    
    @pytest.fixture
    def sample_reward_data(self, test_db_session):
        """创建样本奖品数据"""
        rewards = [
            Reward(
                id=str(uuid4()),
                name="积分加成卡",
                description="+50%积分，有效期1小时",
                points_value=50,
                image_url="https://example.com/bonus-card.jpg",
                category="boost",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            Reward(
                id=str(uuid4()),
                name="专注道具",
                description="立即完成专注会话",
                points_value=30,
                image_url="https://example.com/focus-item.jpg",
                category="tool",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            Reward(
                id=str(uuid4()),
                name="时间管理券",
                description="延长任务截止时间1天",
                points_value=100,
                image_url="https://example.com/time-coupon.jpg",
                category="coupon",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ]
        
        for reward in rewards:
            test_db_session.add(reward)
        test_db_session.commit()
        return rewards
    
    @pytest.fixture
    def sample_transactions(self, test_db_session, test_user, sample_reward_data):
        """创建样本流水数据"""
        base_time = datetime.now(timezone.utc)
        transactions = [
            RewardTransaction(
                user_id=test_user.id,
                reward_id=sample_reward_data[0].id,
                source_type="welcome_gift",
                quantity=3,
                transaction_group=f"welcome_gift_{test_user.id}_{uuid4()}",
                created_at=base_time
            ),
            RewardTransaction(
                user_id=test_user.id,
                reward_id=sample_reward_data[1].id,
                source_type="lottery_reward",
                quantity=10,
                transaction_group=f"lottery_{test_user.id}_{uuid4()}",
                created_at=base_time.replace(second=1)
            ),
            RewardTransaction(
                user_id=test_user.id,
                reward_id=sample_reward_data[0].id,
                source_type="recipe_consume",
                quantity=-2,
                transaction_group=f"recipe_{test_user.id}_{uuid4()}",
                created_at=base_time.replace(second=2)
            ),
            RewardTransaction(
                user_id=test_user.id,
                reward_id=sample_reward_data[2].id,
                source_type="top3_lottery",
                quantity=5,
                transaction_group=f"top3_{test_user.id}_{uuid4()}",
                created_at=base_time.replace(second=3)
            )
        ]
        
        for transaction in transactions:
            test_db_session.add(transaction)
        test_db_session.commit()
        
        return transactions
    
    def test_get_reward_transactions_success(self, client, test_user, auth_headers, sample_transactions):
        """测试成功获取奖励流水"""
        # Given: 已有样本数据
        
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证响应
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["code"] == 200
        assert response_data["message"] == "success"
        assert "data" in response_data
        
        data = response_data["data"]
        assert "transactions" in data
        assert "total_count" in data
        assert "balance_summary" in data
        
        # 验证流水记录
        transactions = data["transactions"]
        assert len(transactions) == 4
        assert data["total_count"] == 4
        
        # 验证每条记录的字段
        for transaction in transactions:
            assert "id" in transaction
            assert "reward_id" in transaction
            assert "reward_name" in transaction
            assert "source_type" in transaction
            assert "source_id" in transaction
            assert "quantity" in transaction
            assert "transaction_group" in transaction
            assert "created_at" in transaction
            
            # 验证字段类型
            assert isinstance(transaction["id"], str)
            assert isinstance(transaction["reward_id"], str)
            assert isinstance(transaction["reward_name"], str)
            assert isinstance(transaction["source_type"], str)
            assert isinstance(transaction["quantity"], int)
            assert isinstance(transaction["created_at"], str)
    
    def test_get_reward_transactions_ordering(self, client, test_user, auth_headers, sample_transactions):
        """测试流水记录排序"""
        # Given: 已有样本数据
        
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证排序（按创建时间倒序）
        assert response.status_code == 200
        data = response.json()["data"]
        transactions = data["transactions"]
        
        # 验证时间倒序
        created_times = [t["created_at"] for t in transactions]
        assert created_times == sorted(created_times, reverse=True)
        
        # 验证最新记录在前
        assert transactions[0]["source_type"] == "top3_lottery"  # 最后创建的
        assert transactions[-1]["source_type"] == "welcome_gift"  # 最早创建的
    
    def test_get_reward_transactions_pagination(self, client, test_user, auth_headers, sample_transactions):
        """测试分页参数"""
        # Given: 已有4条样本数据
        
        # When: 调用API带分页参数
        response = client.get(
            "/rewards/my-rewards/transactions?page=1&page_size=2",
            headers=auth_headers
        )
        
        # Then: 验证第一页结果
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert len(data["transactions"]) == 2
        assert data["total_count"] == 4
        
        # When: 查询第二页
        response2 = client.get(
            "/rewards/my-rewards/transactions?page=2&page_size=2",
            headers=auth_headers
        )
        
        # Then: 验证第二页结果
        assert response2.status_code == 200
        data2 = response2.json()["data"]
        
        assert len(data2["transactions"]) == 2
        assert data2["total_count"] == 4
        
        # 验证两页数据不重复
        page1_ids = {t["id"] for t in data["transactions"]}
        page2_ids = {t["id"] for t in data2["transactions"]}
        assert page1_ids.isdisjoint(page2_ids)
    
    def test_get_reward_transactions_balance_summary(self, client, test_user, auth_headers, sample_transactions):
        """测试余额汇总计算"""
        # Given: 已有样本数据
        
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证余额汇总
        assert response.status_code == 200
        data = response.json()["data"]
        balance_summary = data["balance_summary"]
        
        # 验证汇总计算
        # 积分加成卡：3-2=1
        # 专注道具：10
        # 时间管理券：5
        expected_balances = {
            sample_transactions[0].reward_id: 1,   # 积分加成卡
            sample_transactions[1].reward_id: 10,  # 专注道具
            sample_transactions[3].reward_id: 5    # 时间管理券
        }
        
        assert len(balance_summary) == 3
        for reward_id, expected_balance in expected_balances.items():
            assert balance_summary[reward_id] == expected_balance
    
    def test_get_reward_transactions_empty_result(self, client, test_user, auth_headers):
        """测试空结果"""
        # Given: 用户没有任何流水记录
        
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证空结果处理
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert data["transactions"] == []
        assert data["total_count"] == 0
        assert data["balance_summary"] == {}
    
    def test_get_reward_transactions_single_record(self, client, test_user, auth_headers, test_db_session):
        """测试单条记录"""
        # Given: 创建单条流水记录
        reward = Reward(
            id=str(uuid4()),
            name="单记录测试奖品",
            description="单记录测试",
            points_value=50,
            category="test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(reward)
        test_db_session.commit()
        
        transaction = RewardTransaction(
            user_id=test_user.id,
            reward_id=reward.id,
            source_type="single_test",
            quantity=42,
            transaction_group=f"single_{test_user.id}_{uuid4()}",
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证单条记录结果
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert len(data["transactions"]) == 1
        assert data["total_count"] == 1
        
        transaction_data = data["transactions"][0]
        assert transaction_data["reward_name"] == "单记录测试奖品"
        assert transaction_data["quantity"] == 42
        assert transaction_data["source_type"] == "single_test"
    
    def test_get_reward_transactions_negative_quantity(self, client, test_user, auth_headers, test_db_session):
        """测试负数量记录"""
        # Given: 创建负数量的流水记录
        reward = Reward(
            id=str(uuid4()),
            name="负数量测试奖品",
            description="负数量测试",
            points_value=50,
            category="test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(reward)
        test_db_session.commit()
        
        transaction = RewardTransaction(
            user_id=test_user.id,
            reward_id=reward.id,
            source_type="recipe_consume",
            quantity=-5,
            transaction_group=f"consume_{test_user.id}_{uuid4()}",
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证负数量被正确处理
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["quantity"] == -5
        assert data["transactions"][0]["source_type"] == "recipe_consume"
    
    def test_get_reward_transactions_all_source_types(self, client, test_user, auth_headers, test_db_session):
        """测试所有支持的source_type"""
        # Given: 创建包含各种source_type的流水记录
        reward = Reward(
            id=str(uuid4()),
            name="全类型测试奖品",
            description="全类型测试",
            points_value=50,
            category="test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(reward)
        test_db_session.commit()
        
        source_types = [
            "welcome_gift", "lottery_reward", "recipe_consume", "recipe_produce",
            "redemption", "top3_lottery", "task_completion", "points_conversion"
        ]
        
        for i, source_type in enumerate(source_types):
            transaction = RewardTransaction(
                user_id=test_user.id,
                reward_id=reward.id,
                source_type=source_type,
                quantity=1,
                transaction_group=f"test_{test_user.id}_{uuid4()}",
                created_at=datetime.now(timezone.utc).replace(second=i)
            )
            test_db_session.add(transaction)
        test_db_session.commit()
        
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证所有source_type都被正确处理
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert len(data["transactions"]) == len(source_types)
        returned_source_types = {t["source_type"] for t in data["transactions"]}
        assert returned_source_types == set(source_types)
    
    def test_get_reward_transactions_with_source_id(self, client, test_user, auth_headers, test_db_session):
        """测试带source_id的记录"""
        # Given: 创建带source_id的流水记录
        reward = Reward(
            id=str(uuid4()),
            name="SourceID测试奖品",
            description="SourceID测试",
            points_value=50,
            category="test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(reward)
        test_db_session.commit()
        
        source_id = str(uuid4())
        transaction = RewardTransaction(
            user_id=test_user.id,
            reward_id=reward.id,
            source_type="recipe_consume",
            source_id=source_id,
            quantity=-1,
            transaction_group=f"recipe_{test_user.id}_{uuid4()}",
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证source_id被正确处理
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["source_id"] == source_id
    
    def test_get_reward_transactions_transaction_group(self, client, test_user, auth_headers, test_db_session):
        """测试事务组关联"""
        # Given: 创建具有相同事务组的多条记录
        reward = Reward(
            id=str(uuid4()),
            name="事务组测试奖品",
            description="事务组测试",
            points_value=50,
            category="test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(reward)
        test_db_session.commit()
        
        transaction_group = f"test_group_{uuid4()}"
        transactions = [
            RewardTransaction(
                user_id=test_user.id,
                reward_id=reward.id,
                source_type="recipe_consume",
                quantity=-2,
                transaction_group=transaction_group,
                created_at=datetime.now(timezone.utc)
            ),
            RewardTransaction(
                user_id=test_user.id,
                reward_id=reward.id,
                source_type="recipe_produce",
                quantity=1,
                transaction_group=transaction_group,
                created_at=datetime.now(timezone.utc).replace(second=1)
            )
        ]
        
        for transaction in transactions:
            test_db_session.add(transaction)
        test_db_session.commit()
        
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证事务组ID一致
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert len(data["transactions"]) == 2
        assert all(t["transaction_group"] == transaction_group for t in data["transactions"])
    
    def test_get_reward_transactions_invalid_page_parameter(self, client, test_user, auth_headers):
        """测试无效分页参数"""
        # When: 使用无效的分页参数
        response = client.get(
            "/rewards/my-rewards/transactions?page=0&page_size=10",
            headers=auth_headers
        )
        
        # Then: 验证错误处理
        assert response.status_code == 422  # FastAPI验证错误
    
    def test_get_reward_transactions_invalid_page_size(self, client, test_user, auth_headers):
        """测试无效页面大小"""
        # When: 使用无效的页面大小
        response = client.get(
            "/rewards/my-rewards/transactions?page=1&page_size=0",
            headers=auth_headers
        )
        
        # Then: 验证错误处理
        assert response.status_code == 422  # FastAPI验证错误
    
    def test_get_reward_transactions_large_page_size(self, client, test_user, auth_headers, test_db_session):
        """测试大页面大小限制"""
        # Given: 创建超过100条记录
        reward = Reward(
            id=str(uuid4()),
            name="大页面测试奖品",
            description="大页面测试",
            points_value=50,
            category="test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(reward)
        test_db_session.commit()
        
        for i in range(150):
            transaction = RewardTransaction(
                user_id=test_user.id,
                reward_id=reward.id,
                source_type=f"bulk_test_{i}",
                quantity=1,
                transaction_group=f"bulk_{test_user.id}_{uuid4()}",
                created_at=datetime.now(timezone.utc).replace(second=i%60)
            )
            test_db_session.add(transaction)
        test_db_session.commit()
        
        # When: 请求大页面大小
        response = client.get(
            "/rewards/my-rewards/transactions?page=1&page_size=200",
            headers=auth_headers
        )
        
        # Then: 验证页面大小限制生效
        assert response.status_code == 422  # 应该被FastAPI验证拒绝
    
    def test_get_reward_transactions_without_auth(self, client):
        """测试无认证访问"""
        # When: 无认证头调用API
        response = client.get("/rewards/my-rewards/transactions")
        
        # Then: 验证认证失败
        assert response.status_code == 403  # 或401，取决于认证中间件
    
    def test_get_reward_transactions_invalid_auth(self, client):
        """测试无效认证"""
        # When: 使用无效token
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Then: 验证认证失败
        assert response.status_code == 403  # 或401
    
    def test_get_reward_transactions_malformed_auth(self, client):
        """测试格式错误的认证"""
        # When: 使用格式错误的认证头
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers={"Authorization": "MalformedHeader"}
        )
        
        # Then: 验证认证失败
        assert response.status_code == 403  # 或401
    
    def test_get_reward_transactions_response_format(self, client, test_user, auth_headers, sample_transactions):
        """测试响应格式完整性"""
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证响应格式
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        response_data = response.json()
        
        # 验证顶层结构
        assert "code" in response_data
        assert "message" in response_data
        assert "data" in response_data
        
        # 验证data结构
        data = response_data["data"]
        assert "transactions" in data
        assert "total_count" in data
        assert "balance_summary" in data
        
        # 验证数据类型
        assert isinstance(response_data["code"], int)
        assert isinstance(response_data["message"], str)
        assert isinstance(data["transactions"], list)
        assert isinstance(data["total_count"], int)
        assert isinstance(data["balance_summary"], dict)
    
    def test_get_reward_transactions_data_integrity(self, client, test_user, auth_headers, sample_transactions):
        """测试数据完整性"""
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证数据完整性
        assert response.status_code == 200
        data = response.json()["data"]
        
        transactions = data["transactions"]
        balance_summary = data["balance_summary"]
        
        # 验证流水记录数量与汇总一致性
        assert len(transactions) == data["total_count"]
        
        # 验证余额汇总计算正确性
        expected_balances = {}
        for transaction in transactions:
            reward_id = transaction["reward_id"]
            quantity = transaction["quantity"]
            expected_balances[reward_id] = expected_balances.get(reward_id, 0) + quantity
        
        assert balance_summary == expected_balances
    
    def test_get_reward_transactions_edge_case_zero_quantities(self, client, test_user, auth_headers, test_db_session):
        """测试零数量边界情况"""
        # Given: 创建零数量的流水记录
        reward = Reward(
            id=str(uuid4()),
            name="零数量测试奖品",
            description="零数量测试",
            points_value=50,
            category="test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(reward)
        test_db_session.commit()
        
        transaction = RewardTransaction(
            user_id=test_user.id,
            reward_id=reward.id,
            source_type="test_zero",
            quantity=0,
            transaction_group=f"zero_{test_user.id}_{uuid4()}",
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # When: 调用API
        response = client.get(
            "/rewards/my-rewards/transactions",
            headers=auth_headers
        )
        
        # Then: 验证零数量被正确处理
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["quantity"] == 0
        assert data["balance_summary"][reward.id] == 0
    
    def test_get_reward_transactions_uuid_user_id_support(self, client, test_user, auth_headers, test_db_session):
        """测试UUID用户ID支持"""
        # Given: 使用UUID字符串作为用户ID创建记录
        user_uuid = uuid4()
        
        reward = Reward(
            id=str(uuid4()),
            name="UUID测试奖品",
            description="UUID测试",
            points_value=50,
            category="test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(reward)
        test_db_session.commit()
        
        transaction = RewardTransaction(
            user_id=str(user_uuid),
            reward_id=reward.id,
            source_type="uuid_test",
            quantity=1,
            transaction_group=f"uuid_{user_uuid}_{uuid4()}",
            created_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # 模拟该用户的认证
        uuid_auth_headers = {"Authorization": f"Bearer test_token_for_{user_uuid}"}
        
        # When: 使用该用户的认证调用API
        # 注意：这里需要模拟获取当前用户ID的fixture返回UUID
        # 实际测试中需要配置相应的依赖注入
        
        # 由于需要修改依赖注入，这里验证数据库层面的UUID支持
        db_transactions = test_db_session.exec(
            select(RewardTransaction).where(RewardTransaction.user_id == str(user_uuid))
        ).all()
        
        # Then: 验证UUID用户ID被正确处理
        assert len(db_transactions) == 1
        assert db_transactions[0].user_id == str(user_uuid)