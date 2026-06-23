from utils.config_handler import prompts_conf
from utils.logger_handler import logger
from utils.path_tool import get_abs_path


def _load_prompt(config_key: str, prompt_name: str) -> str:
    try:
        prompt_path = get_abs_path(prompts_conf[config_key])
    except KeyError as exc:
        logger.error(f"[prompt_loader] missing config key: {config_key}")
        raise exc

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:
        logger.error(f"[prompt_loader] failed to load {prompt_name}: {str(exc)}")
        raise exc


def load_system_prompts() -> str:
    return _load_prompt("main_prompt_path", "system prompt")


def load_rag_prompts() -> str:
    return _load_prompt("rag_summarize_prompt_path", "rag prompt")
