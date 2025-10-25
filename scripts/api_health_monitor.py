#!/usr/bin/env python3
"""
API健康监控系统

实时监控API参数健康状态，自动发现参数异常，
提供API质量监控和告警功能。

作者：TaTakeKe团队
版本：1.0.0
"""

import asyncio
import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class APIHealthCheck:
    """API健康检查结果"""
    endpoint: str
    status: HealthStatus
    response_time: float
    status_code: int
    error_message: Optional[str] = None
    parameter_issues: List[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.parameter_issues is None:
            self.parameter_issues = []
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class HealthReport:
    """健康报告"""
    total_endpoints: int
    healthy_endpoints: int
    warning_endpoints: int
    error_endpoints: int
    unknown_endpoints: int
    average_response_time: float
    checks: List[APIHealthCheck]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class APIHealthMonitor:
    """API健康监控器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.logger = self._setup_logger()
        self.previous_checks = {}
        self.health_history = []

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("APIHealthMonitor")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    async def check_endpoint_health(self, endpoint: str) -> APIHealthCheck:
        """检查单个端点健康状态"""
        start_time = time.time()
        url = f"{self.base_url}{endpoint}"

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    response_time = time.time() - start_time
                    status_code = response.status_code

                    # 分析响应内容
                    parameter_issues = await self._analyze_response_for_parameter_issues(response)

                    # 确定健康状态
                    if status_code == 200:
                        if parameter_issues:
                            status = HealthStatus.WARNING
                        elif response_time > 2.0:  # 超过2秒
                            status = HealthStatus.WARNING
                        else:
                            status = HealthStatus.HEALTHY
                    elif 400 <= status_code < 500:
                        status = HealthStatus.WARNING
                    else:
                        status = HealthStatus.ERROR

                    return APIHealthCheck(
                        endpoint=endpoint,
                        status=status,
                        response_time=response_time,
                        status_code=status_code,
                        parameter_issues=parameter_issues
                    )

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return APIHealthCheck(
                endpoint=endpoint,
                status=HealthStatus.ERROR,
                response_time=response_time,
                status_code=0,
                error_message="请求超时"
            )

        except Exception as e:
            response_time = time.time() - start_time
            return APIHealthCheck(
                endpoint=endpoint,
                status=HealthStatus.ERROR,
                response_time=response_time,
                status_code=0,
                error_message=str(e)
            )

    async def _analyze_response_for_parameter_issues(self, response) -> List[str]:
        """分析响应中的参数问题"""
        issues = []

        try:
            content = await response.text()

            # 检查是否包含参数错误信息
            lower_content = content.lower()

            if "args" in lower_content and "parameter" in lower_content:
                issues.append("响应中包含args参数相关错误")

            if "kwargs" in lower_content and "parameter" in lower_content:
                issues.append("响应中包含kwargs参数相关错误")

            if "validation error" in lower_content:
                issues.append("响应中包含验证错误")

            if "field required" in lower_content:
                issues.append("响应中包含必需字段缺失错误")

            # 尝试解析JSON并检查结构
            try:
                json_data = await response.json()
                if isinstance(json_data, dict):
                    # 检查错误详情
                    if "detail" in json_data and isinstance(json_data["detail"], list):
                        for error in json_data["detail"]:
                            if isinstance(error, dict) and "loc" in error:
                                location = error["loc"]
                                if any(param in str(location) for param in ["args", "kwargs"]):
                                    issues.append(f"参数位置错误: {location}")

            except:
                pass  # 不是JSON响应，跳过详细检查

        except Exception as e:
            self.logger.warning(f"分析响应时出错: {e}")

        return issues

    async def get_api_endpoints(self) -> List[str]:
        """获取所有API端点列表"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/openapi.json") as response:
                    if response.status == 200:
                        openapi_spec = await response.json()
                        paths = openapi_spec.get("paths", {})

                        endpoints = []
                        for path in paths.keys():
                            # 添加GET端点
                            endpoints.append(path)

                        return endpoints
        except Exception as e:
            self.logger.error(f"获取API端点列表失败: {e}")
            return []

    async def run_health_check(self) -> HealthReport:
        """运行完整的健康检查"""
        self.logger.info("开始API健康检查...")

        # 获取所有端点
        endpoints = await self.get_api_endpoints()
        if not endpoints:
            self.logger.warning("未找到任何API端点")
            return HealthReport(
                total_endpoints=0,
                healthy_endpoints=0,
                warning_endpoints=0,
                error_endpoints=0,
                unknown_endpoints=0,
                average_response_time=0,
                checks=[]
            )

        # 检查每个端点
        checks = []
        for endpoint in endpoints:
            self.logger.info(f"检查端点: {endpoint}")
            check = await self.check_endpoint_health(endpoint)
            checks.append(check)

        # 生成报告
        report = self._generate_health_report(checks)

        # 保存历史记录
        self.health_history.append(report)

        # 限制历史记录数量
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-50:]

        self.logger.info(f"健康检查完成: {report.healthy_endpoints}/{report.total_endpoints} 端点健康")

        return report

    def _generate_health_report(self, checks: List[APIHealthCheck]) -> HealthReport:
        """生成健康报告"""
        total = len(checks)
        healthy = sum(1 for check in checks if check.status == HealthStatus.HEALTHY)
        warning = sum(1 for check in checks if check.status == HealthStatus.WARNING)
        error = sum(1 for check in checks if check.status == HealthStatus.ERROR)
        unknown = sum(1 for check in checks if check.status == HealthStatus.UNKNOWN)

        avg_response_time = sum(check.response_time for check in checks) / total if total > 0 else 0

        return HealthReport(
            total_endpoints=total,
            healthy_endpoints=healthy,
            warning_endpoints=warning,
            error_endpoints=error,
            unknown_endpoints=unknown,
            average_response_time=avg_response_time,
            checks=checks
        )

    def print_health_report(self, report: HealthReport):
        """打印健康报告"""
        print("\n" + "="*60)
        print("🏥 API健康检查报告")
        print("="*60)
        print(f"检查时间: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"检查端点总数: {report.total_endpoints}")
        print(f"健康端点: {report.healthy_endpoints} ✅")
        print(f"警告端点: {report.warning_endpoints} ⚠️")
        print(f"错误端点: {report.error_endpoints} ❌")
        print(f"未知状态: {report.unknown_endpoints} ❓")
        print(f"平均响应时间: {report.average_response_time:.3f}秒")

        # 详细信息
        if report.error_endpoints > 0:
            print("\n❌ 错误端点详情:")
            for check in report.checks:
                if check.status == HealthStatus.ERROR:
                    print(f"  - {check.endpoint}: {check.error_message or 'HTTP ' + str(check.status_code)}")

        if report.warning_endpoints > 0:
            print("\n⚠️ 警告端点详情:")
            for check in report.checks:
                if check.status == HealthStatus.WARNING:
                    issues = ", ".join(check.parameter_issues) if check.parameter_issues else f"响应时间 {check.response_time:.3f}s"
                    print(f"  - {check.endpoint}: {issues}")

        print("="*60)

    def save_health_report(self, report: HealthReport, output_file: str = None):
        """保存健康报告到文件"""
        if not output_file:
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            output_file = f"health_report_{timestamp}.json"

        # 转换为可序列化格式
        report_dict = asdict(report)

        # 转换datetime为字符串
        report_dict['timestamp'] = report.timestamp.isoformat()

        # 转换checks中的datetime和status
        for check in report_dict['checks']:
            check['timestamp'] = datetime.fromisoformat(check['timestamp']).isoformat()
            check['status'] = check['status'].value

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        self.logger.info(f"健康报告已保存到: {output_file}")

    async def start_monitoring(self, interval: int = 300, continuous: bool = True):
        """开始持续监控"""
        self.logger.info(f"开始API健康监控，检查间隔: {interval}秒")

        while continuous:
            try:
                report = await self.run_health_check()
                self.print_health_report(report)

                # 检查是否有严重问题需要立即告警
                if report.error_endpoints > 0:
                    self.logger.error(f"发现 {report.error_endpoints} 个错误端点，需要立即关注！")

                # 保存报告
                self.save_health_report(report)

                if continuous:
                    await asyncio.sleep(interval)

            except KeyboardInterrupt:
                self.logger.info("监控被用户中断")
                break
            except Exception as e:
                self.logger.error(f"监控过程中出错: {e}")
                if continuous:
                    await asyncio.sleep(60)  # 出错后等待1分钟再继续


async def main():
    """主函数"""
    import argparse
    import aiohttp

    parser = argparse.ArgumentParser(description="API健康监控工具")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API服务器地址 (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="检查间隔秒数 (默认: 300)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="只执行一次检查"
    )
    parser.add_argument(
        "--output",
        help="报告输出目录"
    )

    args = parser.parse_args()

    # 创建监控器
    monitor = APIHealthMonitor(args.base_url)

    # 设置输出目录
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(exist_ok=True)
        # 修改保存报告的方法以使用指定目录
        original_save = monitor.save_health_report
        def save_with_dir(report, output_file=None):
            if not output_file:
                timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
                output_file = output_dir / f"health_report_{timestamp}.json"
            original_save(report, str(output_file))
        monitor.save_health_report = save_with_dir

    # 运行监控
    if args.once:
        report = await monitor.run_health_check()
        monitor.print_health_report(report)
        monitor.save_health_report(report)
    else:
        await monitor.start_monitoring(interval=args.interval)


if __name__ == "__main__":
    asyncio.run(main())