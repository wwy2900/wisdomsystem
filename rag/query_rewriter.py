from functools import lru_cache
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models.tongyi import ChatTongyi
import re


class QueryRewriter:
    def __init__(self):
        self.light_model = ChatTongyi(model="qwen-turbo")
        self.prompt_template = PromptTemplate.from_template("""
请将用户的问题从三个不同角度改写成适合向量检索的形式，保证多样性且不偏离意图。

三个改写角度：
1. 同义替换版：将关键词替换为同义词或专业术语（如"咋"→"如何"，"豆子"→"颗粒物"）
2. 句式转换版：改变句式结构，如将疑问句转换为陈述句或解决方案式（如"噪音太大"→"如何解决噪音大问题"）
3. 意图补全版：补充省略的主语和上下文信息（如"咋充电"→"扫地机器人如何充电"）

原始问题：{query}

请按以下格式输出三个改写结果：
【同义替换版】：xxx
【句式转换版】：xxx
【意图补全版】：xxx
""")
        self.chain = self.prompt_template | self.light_model | StrOutputParser()

    @lru_cache(maxsize=1000)
    def rewrite(self, query: str) -> str:
        return self.chain.invoke({"query": query})

    def _parse_rewrites(self, output: str) -> list:
        """解析三个改写结果"""
        rewrites = []
        
        patterns = [
            (r"【同义替换版】[:：]\s*(.+?)(?=\n【|$)", "同义替换版"),
            (r"【句式转换版】[:：]\s*(.+?)(?=\n【|$)", "句式转换版"),
            (r"【意图补全版】[:：]\s*(.+?)(?=\n【|$)", "意图补全版"),
        ]
        
        for pattern, label in patterns:
            match = re.search(pattern, output, re.DOTALL)
            if match:
                rewrites.append({
                    "text": match.group(1).strip(),
                    "type": label
                })
        
        return rewrites

    def rewrite_multi_with_filter(self, query: str, num_rewrites: int = 3, threshold: float = 0.8):
        """多路改写并过滤，只返回相似度≥threshold的改写结果"""
        from rag.semantic_checker import SemanticChecker
        
        checker = SemanticChecker()
        valid_rewrites = []
        
        output = self.chain.invoke({"query": query})
        rewrites = self._parse_rewrites(output)
        
        for rewrite in rewrites:
            similarity = checker.calculate_similarity(query, rewrite["text"])
            
            if similarity >= threshold:
                valid_rewrites.append({
                    "text": rewrite["text"],
                    "similarity": similarity,
                    "type": rewrite["type"]
                })
        
        return valid_rewrites