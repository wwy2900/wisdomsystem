import os
import json
import csv
from contextvars import ContextVar
from datetime import datetime
from utils.logger_handler import logger
from langchain_core.tools import tool

from rag.rag_service import RagSummarizeService
from utils.config_handler import agent_conf
from utils.path_tool import get_abs_path

rag = RagSummarizeService()
current_tool_user_id: ContextVar[str | None] = ContextVar("current_tool_user_id", default=None)

external_data = {}

REQUIRED_FIELDS = ["user_id", "特征", "效率", "耗材", "对比", "时间"]


def set_tool_user_id(user_id: str | None):
    """Set request-scoped user id for tools invoked by the agent."""
    return current_tool_user_id.set(user_id)


def reset_tool_user_id(token):
    current_tool_user_id.reset(token)


def rag_summarize_for_user(query: str, user_id: str | None = None) -> str:
    return rag.rag_summarize(query, user_id=user_id)


@tool
def rag_summarize(query: str) -> str:
    """从向量存储中检索参考资料"""
    return rag_summarize_for_user(query, current_tool_user_id.get())


@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气，以消息字符串的形式返回"""
    return f"城市{city}天气为晴天，气温26摄氏度，空气湿度50%，南风1级，AQI21，最近6小时降雨概率极低"


@tool
def get_user_location() -> str:
    """获取用户所在城市的名称，以纯字符串形式返回。当前使用默认值，实际应用中应从用户上下文获取"""
    return "深圳"


@tool
def get_user_id() -> str:
    """获取用户的ID，以纯字符串形式返回。当前使用默认值，实际应用中应从用户上下文获取"""
    return "1001"


@tool
def get_current_month() -> str:
    """获取当前月份，以纯字符串形式返回（格式：YYYY-MM）"""
    return datetime.now().strftime("%Y-%m")


def generate_external_data():
    """加载外部CSV数据，使用csv.DictReader正确解析"""
    if not external_data:
        external_data_path = get_abs_path(agent_conf["external_data_path"])

        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件{external_data_path}不存在")

        with open(external_data_path, "r", encoding="utf-8", newline='') as f:
            reader = csv.DictReader(f)
            
            fieldnames = reader.fieldnames or []
            missing_fields = [field for field in REQUIRED_FIELDS if field not in fieldnames]
            if missing_fields:
                logger.error(f"[generate_external_data]CSV文件缺少必需字段: {missing_fields}")
                return

            for row_num, row in enumerate(reader, start=2):
                try:
                    user_id = row.get("user_id", "").strip()
                    feature = row.get("特征", "").strip()
                    efficiency = row.get("效率", "").strip()
                    consumables = row.get("耗材", "").strip()
                    comparison = row.get("对比", "").strip()
                    time = row.get("时间", "").strip()

                    if not user_id:
                        logger.warning(f"[generate_external_data]第{row_num}行缺少user_id，跳过")
                        continue

                    if user_id not in external_data:
                        external_data[user_id] = {}

                    external_data[user_id][time] = {
                        "特征": feature,
                        "效率": efficiency,
                        "耗材": consumables,
                        "对比": comparison,
                    }
                except Exception as e:
                    logger.error(f"[generate_external_data]第{row_num}行解析错误: {str(e)}")
                    continue

        logger.info(f"[generate_external_data]已加载{len(external_data)}个用户的外部数据")


@tool
def fetch_external_data(user_id: str, month: str) -> str:
    """从外部系统中获取指定用户在指定月份的使用记录，以JSON字符串形式返回，如果未检索到返回空字符串"""
    generate_external_data()

    try:
        data = external_data[user_id][month]
        return json.dumps(data, ensure_ascii=False)
    except KeyError:
        logger.warning(f"[fetch_external_data]未能检索到用户：{user_id}在{month}的使用记录数据")
        return ""


@tool
def fill_context_for_report():
    """无入参，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息"""
    return "fill_context_for_report已调用"
