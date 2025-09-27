"""
知识库检索Mock服务
模拟知识库检索的业务逻辑
"""

import random
import time
from typing import List

from ..models import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSource,
    SourceType
)


class MockKnowledgeService:
    """Mock知识库服务"""

    def __init__(self):
        # 预设知识库条目
        self.knowledge_base = [
            {
                "text": "派蒙是旅行者的向导和同伴，她是一个神秘的小仙灵，拥有星空般的头发和可爱的外表。派蒙总是飘在空中，有时候会说一些可爱的话。",
                "keywords": ["派蒙", "向导", "同伴", "仙灵", "可爱"],
                "source": SourceType.CUSTOM,
                "metadata": {"category": "character", "name": "paimon", "region": "all"}
            },
            {
                "text": "提瓦特大陆是一个被七位神统治的幻想世界，每个神都掌管着一个国家和对应的元素力量。七神分别是风神、岩神、雷神、草神、水神、火神和冰神。",
                "keywords": ["提瓦特", "七神", "世界", "元素", "国家"],
                "source": SourceType.PUBLIC,
                "metadata": {"category": "lore", "topic": "world_setting"}
            },
            {
                "text": "蒙德城是风神巴巴托斯守护的自由之城，位于提瓦特大陆的西部。这里的人们崇尚自由，城市建筑具有欧洲中世纪风格。",
                "keywords": ["蒙德", "风神", "巴巴托斯", "自由", "城市"],
                "source": SourceType.PUBLIC,
                "metadata": {"category": "location", "region": "mondstadt"}
            },
            {
                "text": "璃月港是岩神摩拉克斯守护的商业之城，以贸易和商业闻名。这里有着丰富的历史文化和美丽的山水风光。",
                "keywords": ["璃月", "岩神", "摩拉克斯", "商业", "贸易"],
                "source": SourceType.PUBLIC,
                "metadata": {"category": "location", "region": "liyue"}
            },
            {
                "text": "原神中的元素系统包括七种基本元素：风、岩、雷、草、水、火、冰。不同元素之间可以产生各种元素反应，如燃烧、蒸发、融化等。",
                "keywords": ["元素", "反应", "风", "岩", "雷", "草", "水", "火", "冰"],
                "source": SourceType.PUBLIC,
                "metadata": {"category": "gameplay", "topic": "elements"}
            },
            {
                "text": "冒险家协会是帮助旅行者完成各种委托任务的组织，在各个城市都设有分部。凯瑟琳是协会的接待员，负责发布和管理任务。",
                "keywords": ["冒险家协会", "委托", "任务", "凯瑟琳"],
                "source": SourceType.PUBLIC,
                "metadata": {"category": "organization", "name": "adventurers_guild"}
            },
            {
                "text": "料理在提瓦特大陆是非常重要的，不同的料理可以为角色提供各种增益效果。派蒙特别喜欢美食，经常想着要吃好吃的东西。",
                "keywords": ["料理", "美食", "食物", "派蒙", "好吃"],
                "source": SourceType.CUSTOM,
                "metadata": {"category": "gameplay", "topic": "cooking", "character": "paimon"}
            }
        ]

    def _calculate_relevance_score(self, query: str, knowledge_item: dict) -> float:
        """计算查询与知识条目的相关性分数"""
        query_lower = query.lower()

        # 检查关键词匹配
        keyword_matches = sum(1 for keyword in knowledge_item["keywords"]
                            if keyword.lower() in query_lower)

        # 检查文本内容匹配
        text_lower = knowledge_item["text"].lower()
        text_matches = sum(1 for word in query_lower.split()
                          if len(word) > 1 and word in text_lower)

        # 计算基础分数
        total_keywords = len(knowledge_item["keywords"])
        total_query_words = len([w for w in query_lower.split() if len(w) > 1])

        if total_keywords == 0 or total_query_words == 0:
            return 0.0

        keyword_score = keyword_matches / total_keywords
        text_score = text_matches / total_query_words if total_query_words > 0 else 0

        # 综合分数
        score = (keyword_score * 0.7 + text_score * 0.3)

        # 添加一些随机性来模拟实际检索的不确定性
        score *= random.uniform(0.8, 1.2)

        return min(score, 1.0)

    def _filter_results(self, results: List[tuple], request: KnowledgeSearchRequest) -> List[tuple]:
        """根据请求参数过滤结果"""
        filtered = []

        for item, score in results:
            # 检查最小分数
            if score < request.min_score:
                continue

            # 检查过滤条件
            if request.filters:
                metadata = item["metadata"]
                match = True
                for key, value in request.filters.items():
                    if key not in metadata or metadata[key] != value:
                        match = False
                        break
                if not match:
                    continue

            filtered.append((item, score))

        return filtered

    async def search_knowledge(self, request: KnowledgeSearchRequest, trace_id: str) -> KnowledgeSearchResponse:
        """检索知识库"""
        start_time = time.time()

        # 模拟检索延迟
        import asyncio
        await asyncio.sleep(random.uniform(0.05, 0.2))

        # 计算每个知识条目的相关性分数
        results = []
        for item in self.knowledge_base:
            score = self._calculate_relevance_score(request.query, item)
            if score > 0:
                results.append((item, score))

        # 按分数排序
        results.sort(key=lambda x: x[1], reverse=True)

        # 应用过滤条件
        results = self._filter_results(results, request)

        # 取前topk个结果
        results = results[:request.topk]

        # 转换为响应格式
        hits = []
        for item, score in results:
            hits.append(KnowledgeSource(
                text=item["text"],
                source=item["source"],
                score=round(score, 3),
                metadata=item["metadata"]
            ))

        processing_time = (time.time() - start_time) * 1000

        return KnowledgeSearchResponse(
            hits=hits,
            embedding_model="bge-m3",
            total_count=len(self.knowledge_base),
            trace_id=trace_id
        )


# 单例实例
_knowledge_service = None


def get_knowledge_service() -> MockKnowledgeService:
    """获取知识库服务实例"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = MockKnowledgeService()
    return _knowledge_service