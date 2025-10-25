"""
LLM响应模拟器

模拟真实LLM的响应模式，提供：
1. 工具调用验证响应模拟
2. 复杂查询理解响应
3. 错误场景和边界条件模拟
4. 性能和响应时间模拟
5. 多轮对话上下文管理

设计原则：
1. 真实性：模拟真实LLM的思维模式和响应特征
2. 多样性：提供各种响应场景的模拟
3. 可配置：支持不同测试场景的参数调整
4. 易扩展：便于添加新的模拟场景

作者：TaKeKe团队
版本：1.0.0
"""

import json
import random
import time
import logging
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

# 配置日志
logger = logging.getLogger(__name__)


class ResponseComplexity(Enum):
    """响应复杂度级别"""
    SIMPLE = "simple"           # 简单响应
    MODERATE = "moderate"       # 中等复杂度
    COMPLEX = "complex"         # 复杂响应
    VERY_COMPLEX = "very_complex"  # 非常复杂


class ResponseStyle(Enum):
    """响应风格"""
    PROFESSIONAL = "professional"   # 专业风格
    FRIENDLY = "friendly"           # 友好风格
    ANALYTICAL = "analytical"       # 分析风格
    CREATIVE = "creative"           # 创意风格


@dataclass
class SimulationConfig:
    """模拟配置"""
    complexity: ResponseComplexity = ResponseComplexity.MODERATE
    style: ResponseStyle = ResponseStyle.PROFESSIONAL
    include_json_format: bool = True
    include_analysis: bool = True
    include_suggestions: bool = True
    error_probability: float = 0.05
    response_delay_range: tuple = (0.5, 2.0)
    token_range: tuple = (100, 800)
    temperature_effect: float = 0.3


@dataclass
class SimulatedResponse:
    """模拟响应结构"""
    content: str
    tool_calls: List[Dict[str, Any]]
    analysis: Optional[str]
    suggestions: Optional[List[str]]
    metadata: Dict[str, Any]
    response_time: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


class LLMResponseSimulator:
    """LLM响应模拟器"""

    def __init__(self, config: Optional[SimulationConfig] = None):
        """初始化模拟器

        Args:
            config: 模拟配置，如果为None则使用默认配置
        """
        self.config = config or SimulationConfig()
        self.conversation_history: List[Dict[str, str]] = []
        self.response_patterns = self._initialize_response_patterns()

        logger.info(f"🎭 LLM响应模拟器已初始化，复杂度: {self.config.complexity.value}")

    def _initialize_response_patterns(self) -> Dict[str, Any]:
        """初始化响应模式"""
        return {
            "tool_validation": {
                "positive_templates": [
                    "✅ 工具调用验证通过。{analysis}",
                    "👍 功能测试成功。{analysis}",
                    "✓ 工具响应符合预期。{analysis}",
                    "🎯 验证结果正常。{analysis}"
                ],
                "negative_templates": [
                    "❌ 工具调用验证失败。{analysis}",
                    "⚠️ 检测到问题。{analysis}",
                    "🚨 错误需要修复。{analysis}",
                    "❗ 验证未通过。{analysis}"
                ],
                "analysis_patterns": [
                    "JSON格式正确，数据结构完整。",
                    "参数验证通过，类型匹配正确。",
                    "响应时间在合理范围内。",
                    "错误处理机制工作正常。",
                    "边界条件处理得当。"
                ]
            },
            "query_understanding": {
                "search_templates": [
                    "正在搜索相关任务：{query}",
                    "根据查询找到{count}个相关结果。",
                    "搜索完成，已匹配相关任务。",
                    "为您查找了相关的任务信息。"
                ],
                "filter_patterns": [
                    "已按{criteria}进行筛选。",
                    "应用了{filter_type}过滤条件。",
                    "根据指定的过滤条件筛选结果。",
                    "筛选后的结果更加精确。"
                ]
            },
            "error_scenarios": [
                "网络连接异常，请稍后重试。",
                "API调用频率超限，请稍后再试。",
                "参数验证失败，请检查输入格式。",
                "服务暂时不可用，请稍后重试。"
            ]
        }

    async def simulate_tool_validation_response(
        self,
        tool_name: str,
        tool_response: str,
        is_success: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> SimulatedResponse:
        """模拟工具验证响应

        Args:
            tool_name: 工具名称
            tool_response: 工具响应内容
            is_success: 是否成功
            context: 上下文信息

        Returns:
            模拟的响应对象
        """
        start_time = time.time()

        # 生成分析内容
        analysis = self._generate_tool_analysis(tool_name, tool_response, is_success, context)

        # 生成建议
        suggestions = self._generate_suggestions(tool_name, is_success, context)

        # 构建响应内容
        content = self._build_validation_content(tool_name, analysis, is_success)

        # 模拟响应延迟
        response_time = self._simulate_delay(start_time)

        # 生成元数据
        metadata = {
            "tool_name": tool_name,
            "validation_result": "success" if is_success else "failure",
            "complexity": self.config.complexity.value,
            "style": self.config.style.value,
            "estimated_tokens": random.randint(*self.config.token_range)
        }

        response = SimulatedResponse(
            content=content,
            tool_calls=[],
            analysis=analysis,
            suggestions=suggestions,
            metadata=metadata,
            response_time=response_time,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # 记录到对话历史
        self._add_to_history("tool_validation", asdict(response))

        return response

    async def simulate_query_understanding_response(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        filters_applied: Optional[List[str]] = None
    ) -> SimulatedResponse:
        """模拟查询理解响应

        Args:
            query: 用户查询
            search_results: 搜索结果
            filters_applied: 应用的过滤条件

        Returns:
            模拟的响应对象
        """
        start_time = time.time()

        # 生成查询分析
        analysis = self._generate_query_analysis(query, search_results)

        # 生成搜索结果描述
        result_description = self._generate_result_description(search_results, filters_applied)

        # 构建响应内容
        content = self._build_query_content(query, result_description, analysis)

        # 模拟响应延迟
        response_time = self._simulate_delay(start_time)

        # 生成元数据
        metadata = {
            "query": query,
            "result_count": len(search_results),
            "filters_applied": filters_applied or [],
            "complexity": self.config.complexity.value,
            "estimated_tokens": random.randint(*self.config.token_range)
        }

        response = SimulatedResponse(
            content=content,
            tool_calls=[],
            analysis=analysis,
            suggestions=[],  # 查询理解通常不需要建议
            metadata=metadata,
            response_time=response_time,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # 记录到对话历史
        self._add_to_history("query_understanding", asdict(response))

        return response

    async def simulate_error_recovery_response(
        self,
        error_type: str,
        recovery_action: str,
        success: bool = True
    ) -> SimulatedResponse:
        """模拟错误恢复响应

        Args:
            error_type: 错误类型
            recovery_action: 恢复动作
            success: 恢复是否成功

        Returns:
            模拟的响应对象
        """
        start_time = time.time()

        # 生成错误分析
        analysis = self._generate_error_analysis(error_type, recovery_action, success)

        # 生成恢复建议
        suggestions = self._generate_recovery_suggestions(error_type, success)

        # 构建响应内容
        content = self._build_error_recovery_content(error_type, recovery_action, analysis, success)

        # 模拟响应延迟
        response_time = self._simulate_delay(start_time)

        # 生成元数据
        metadata = {
            "error_type": error_type,
            "recovery_action": recovery_action,
            "recovery_success": success,
            "complexity": self.config.complexity.value
        }

        response = SimulatedResponse(
            content=content,
            tool_calls=[],
            analysis=analysis,
            suggestions=suggestions,
            metadata=metadata,
            response_time=response_time,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # 记录到对话历史
        self._add_to_history("error_recovery", asdict(response))

        return response

    async def simulate_multi_tool_chain_response(
        self,
        tool_chain: List[Dict[str, Any]],
        overall_success: bool = True
    ) -> SimulatedResponse:
        """模拟多工具链式调用响应

        Args:
            tool_chain: 工具链执行记录
            overall_success: 整体是否成功

        Returns:
            模拟的响应对象
        """
        start_time = time.time()

        # 生成链式调用分析
        analysis = self._generate_chain_analysis(tool_chain, overall_success)

        # 生成优化建议
        suggestions = self._generate_chain_suggestions(tool_chain, overall_success)

        # 构建响应内容
        content = self._build_chain_content(tool_chain, analysis, overall_success)

        # 模拟响应延迟
        response_time = self._simulate_delay(start_time)

        # 生成元数据
        metadata = {
            "tool_count": len(tool_chain),
            "overall_success": overall_success,
            "chain_complexity": self._calculate_chain_complexity(tool_chain),
            "complexity": self.config.complexity.value
        }

        response = SimulatedResponse(
            content=content,
            tool_calls=tool_chain,
            analysis=analysis,
            suggestions=suggestions,
            metadata=metadata,
            response_time=response_time,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # 记录到对话历史
        self._add_to_history("multi_tool_chain", asdict(response))

        return response

    def _generate_tool_analysis(
        self,
        tool_name: str,
        tool_response: str,
        is_success: bool,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """生成工具分析内容"""
        patterns = self.response_patterns["tool_validation"]["analysis_patterns"]
        base_analysis = random.choice(patterns)

        if is_success:
            return f"✅ {tool_name}工具验证成功。{base_analysis}"
        else:
            return f"❌ {tool_name}工具验证失败。检测到格式或逻辑问题。"

    def _generate_suggestions(
        self,
        tool_name: str,
        is_success: bool,
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成改进建议"""
        if is_success:
            return [
                "建议增加更多边界条件测试。",
                "考虑添加性能监控指标。"
            ]
        else:
            return [
                "请检查JSON格式是否符合规范。",
                "验证参数类型和值的有效性。",
                "确保错误处理逻辑完整。"
            ]

    def _build_validation_content(
        self,
        tool_name: str,
        analysis: str,
        is_success: bool
    ) -> str:
        """构建验证响应内容"""
        if is_success:
            templates = self.response_patterns["tool_validation"]["positive_templates"]
        else:
            templates = self.response_patterns["tool_validation"]["negative_templates"]

        template = random.choice(templates)
        return template.format(analysis=analysis)

    def _generate_query_analysis(
        self,
        query: str,
        search_results: List[Dict[str, Any]]
    ) -> str:
        """生成查询分析"""
        return f"查询'{query}'已理解，找到{len(search_results)}个相关结果。查询匹配度良好，结果相关性符合预期。"

    def _generate_result_description(
        self,
        search_results: List[Dict[str, Any]],
        filters_applied: Optional[List[str]]
    ) -> str:
        """生成结果描述"""
        description = f"搜索到{len(search_results)}个相关任务"

        if filters_applied:
            description += f"，已应用{len(filters_applied)}个过滤条件：{', '.join(filters_applied)}"

        description += "。"

        return description

    def _build_query_content(
        self,
        query: str,
        result_description: str,
        analysis: str
    ) -> str:
        """构建查询响应内容"""
        return f"🔍 {result_description}\n\n📊 {analysis}"

    def _generate_error_analysis(
        self,
        error_type: str,
        recovery_action: str,
        success: bool
    ) -> str:
        """生成错误分析"""
        if success:
            return f"错误'{error_type}'已通过'{recovery_action}'成功恢复。恢复机制工作正常。"
        else:
            return f"错误'{error_type}'的恢复尝试'{recovery_action}'失败。需要进一步诊断。"

    def _generate_recovery_suggestions(
        self,
        error_type: str,
        success: bool
    ) -> List[str]:
        """生成恢复建议"""
        if success:
            return [
                "建议记录此错误模式以改进预防机制。",
                "考虑优化恢复策略以提高效率。"
            ]
        else:
            return [
                "请检查网络连接和服务可用性。",
                "考虑实现备用恢复方案。"
            ]

    def _build_error_recovery_content(
        self,
        error_type: str,
        recovery_action: str,
        analysis: str,
        success: bool
    ) -> str:
        """构建错误恢复响应内容"""
        if success:
            return f"🛠️ 错误恢复成功\n\n{analysis}"
        else:
            return f"⚠️ 错误恢复失败\n\n{analysis}"

    def _generate_chain_analysis(
        self,
        tool_chain: List[Dict[str, Any]],
        overall_success: bool
    ) -> str:
        """生成链式调用分析"""
        success_count = sum(1 for tool in tool_chain if tool.get("success", False))
        total_count = len(tool_chain)

        if overall_success:
            return f"工具链执行成功，{success_count}/{total_count}个工具正常工作。数据流传递正确，状态管理有效。"
        else:
            return f"工具链执行部分失败，{success_count}/{total_count}个工具成功。需要检查数据传递和错误处理。"

    def _generate_chain_suggestions(
        self,
        tool_chain: List[Dict[str, Any]],
        overall_success: bool
    ) -> List[str]:
        """生成链式调用建议"""
        if overall_success:
            return [
                "建议监控链式调用的整体响应时间。",
                "考虑实现并行执行以提高性能。"
            ]
        else:
            return [
                "检查失败工具的依赖关系和输入数据。",
                "实现更好的错误隔离和回退机制。"
            ]

    def _build_chain_content(
        self,
        tool_chain: List[Dict[str, Any]],
        analysis: str,
        overall_success: bool
    ) -> str:
        """构建链式调用响应内容"""
        status = "✅ 成功" if overall_success else "⚠️ 部分失败"
        return f"🔗 工具链执行{status}\n\n📊 {analysis}"

    def _calculate_chain_complexity(self, tool_chain: List[Dict[str, Any]]) -> str:
        """计算链式调用复杂度"""
        if len(tool_chain) <= 2:
            return "low"
        elif len(tool_chain) <= 5:
            return "medium"
        else:
            return "high"

    def _simulate_delay(self, start_time: float) -> float:
        """模拟响应延迟"""
        base_delay = random.uniform(*self.config.response_delay_range)
        complexity_factor = {
            ResponseComplexity.SIMPLE: 0.8,
            ResponseComplexity.MODERATE: 1.0,
            ResponseComplexity.COMPLEX: 1.3,
            ResponseComplexity.VERY_COMPLEX: 1.6
        }[self.config.complexity]

        actual_delay = base_delay * complexity_factor
        time.sleep(actual_delay)  # 实际延迟

        return time.time() - start_time

    def _add_to_history(self, response_type: str, response_data: Dict[str, Any]):
        """添加到对话历史"""
        history_entry = {
            "type": response_type,
            "data": response_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.conversation_history.append(history_entry)

    def get_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.conversation_history.copy()

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        logger.info("🧹 响应模拟器历史已清空")

    def update_config(self, config: SimulationConfig):
        """更新配置"""
        self.config = config
        logger.info(f"⚙️ 模拟器配置已更新，复杂度: {config.complexity.value}")


# 便利函数
def create_simple_simulator() -> LLMResponseSimulator:
    """创建简单模拟器"""
    config = SimulationConfig(complexity=ResponseComplexity.SIMPLE)
    return LLMResponseSimulator(config)


def create_complex_simulator() -> LLMResponseSimulator:
    """创建复杂模拟器"""
    config = SimulationConfig(complexity=ResponseComplexity.COMPLEX)
    return LLMResponseSimulator(config)


# 导出所有公共类和函数
__all__ = [
    'ResponseComplexity',
    'ResponseStyle',
    'SimulationConfig',
    'SimulatedResponse',
    'LLMResponseSimulator',
    'create_simple_simulator',
    'create_complex_simulator'
]