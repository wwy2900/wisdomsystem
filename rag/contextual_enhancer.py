from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_models.tongyi import ChatTongyi
from utils.network_env import ensure_no_proxy_hosts


ensure_no_proxy_hosts()


class ContextualEnhancer:
    def __init__(self):
        self.model = ChatTongyi(model="qwen-turbo")
        self.prompt_template = PromptTemplate.from_template("""
请为以下文档片段生成上下文描述，用于提升检索效果。

文档标题：{document_title}
文档片段：
{chunk_content}

请输出：【章节：xxx】【主题：xxx】【摘要：xxx】
""")
        self.chain = self.prompt_template | self.model | StrOutputParser()

    def enhance(self, document_title: str, chunk_content: str) -> str:
        context = self.chain.invoke({
            "document_title": document_title,
            "chunk_content": chunk_content
        })
        return f"{context}\n{chunk_content}"
