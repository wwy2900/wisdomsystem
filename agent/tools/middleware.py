from typing import Callable, Any, Dict
from utils.prompt_loader import load_system_prompts, load_report_prompts
from utils.logger_handler import logger


def create_monitor_tool():
    """创建工具监控中间件"""
    def monitor_tool_func(request: Any, handler: Callable) -> Any:
        logger.info(f"[tool monitor]执行工具：{getattr(request, 'tool_call', {}).get('name', 'unknown')}")
        logger.info(f"[tool monitor]传入参数：{getattr(request, 'tool_call', {}).get('args', {})}")

        try:
            result = handler(request)
            tool_name = getattr(request, 'tool_call', {}).get('name', 'unknown')
            logger.info(f"[tool monitor]工具{tool_name}调用成功")

            if tool_name == "fill_context_for_report":
                if hasattr(request, 'runtime'):
                    request.runtime.context["report"] = True

            return result
        except Exception as e:
            tool_name = getattr(request, 'tool_call', {}).get('name', 'unknown')
            logger.error(f"工具{tool_name}调用失败，原因：{str(e)}")
            raise e

    return monitor_tool_func


def create_log_before_model():
    """创建模型调用前日志中间件"""
    def log_before_model_func(state: Dict, runtime: Any = None) -> None:
        message_count = len(state.get('messages', []))
        logger.info(f"[log_before_model]即将调用模型，带有{message_count}条消息")

        messages = state.get('messages', [])
        if messages:
            last_msg = messages[-1]
            msg_type = type(last_msg).__name__
            content = getattr(last_msg, 'content', '')[:100] if hasattr(last_msg, 'content') else ''
            logger.debug(f"[log_before_model]{msg_type} | {content}")

        return None

    return log_before_model_func


def create_report_prompt_switch():
    """创建动态提示词切换中间件"""
    def report_prompt_switch_func(request: Any = None, runtime: Any = None) -> str:
        is_report = False
        
        if runtime and hasattr(runtime, 'context'):
            is_report = runtime.context.get("report", False)
        
        if is_report:
            logger.info("[prompt switch]切换到报告生成提示词")
            return load_report_prompts()
        
        return load_system_prompts()

    return report_prompt_switch_func


# 导出中间件实例
monitor_tool = create_monitor_tool()
log_before_model = create_log_before_model()
report_prompt_switch = create_report_prompt_switch()
