"""
PropertyGraphService - 属性图服务

设计特点:
- 节点属性: 每个节点带有丰富的属性信息
- 关系属性: 边也可以有属性 (关系类型、权重等)
- 属性查询: 根据节点/边属性过滤和检索

使用场景:
- 知识图谱 (实体-关系-实体)
- 社交网络 (用户-好友关系-用户)
- 业务关系图 (公司-持股-公司)

索引配置:
- Graph 索引: 存储带属性的图结构
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..base_service import BaseMemoryService
from ..registry import MemoryServiceRegistry

if TYPE_CHECKING:
    pass

import logging

logger = logging.getLogger(__name__)


@MemoryServiceRegistry.register("property_graph")
class PropertyGraphService(BaseMemoryService):
    """
    属性图服务

    核心功能:
    - insert(): 插入节点 + 属性
    - add_relationship(): 添加关系 + 属性
    - retrieve(): 按属性查询节点
    - get_related_entities(): 获取相关实体 (支持关系类型过滤)
    """

    def _setup_indexes(self) -> None:
        """配置有向图索引"""
        # 创建有向图索引 (区分 A→B 和 B→A)
        self.collection.add_index(
            name="property_graph",
            index_type="graph",
            config={"directed": True},  # 有向图
        )

        logger.info("PropertyGraphService: Created directed property graph index")

    def insert(self, text: str, metadata: dict[str, Any] | None = None, **kwargs: Any) -> str:
        """
        插入实体节点

        Args:
            text: 实体名称/描述
            metadata: 节点属性
                - entity_type: 实体类型 (Person, Company, etc.)
                - properties: 自定义属性字典
            **kwargs:
                - relationships: List[Tuple[str, str, Dict]]
                  格式: [(target_id, relation_type, edge_properties), ...]

        Returns:
            entity_id: 实体 ID

        Example:
            # 插入公司实体
            company_id = service.insert(
                "Apple Inc.",
                metadata={
                    "entity_type": "Company",
                    "properties": {"founded": 1976, "industry": "Technology"}
                }
            )

            # 插入人物实体并关联到公司
            person_id = service.insert(
                "Steve Jobs",
                metadata={"entity_type": "Person"},
                relationships=[
                    (company_id, "FOUNDED", {"year": 1976}),
                    (company_id, "CEO", {"from": 1997, "to": 2011})
                ]
            )
        """
        # 1. 生成 data_id 并直接存储数据（绕过 collection.insert() 避免 GraphIndex 参数问题）
        import time

        data_id = self.collection._generate_id(text, metadata)
        self.collection.raw_data[data_id] = {
            "text": text,
            "metadata": metadata or {},
            "created_at": time.time(),
        }

        # 2. 手动添加节点到图索引
        graph_index = self.collection.indexes.get("property_graph")
        if graph_index:
            # 准备节点数据（包含所有元数据）
            node_data = {"text": text, "metadata": metadata or {}}
            graph_index.add(data_id, node_data)

        # 3. 添加关系
        relationships = kwargs.get("relationships", [])
        if relationships:
            for target_id, relation_type, edge_props in relationships:
                self._add_edge(data_id, target_id, relation_type, edge_props)

        logger.debug(f"Inserted entity {data_id[:8]}... with {len(relationships)} relationships")
        return data_id

    def retrieve(
        self,
        query: str | None = None,
        vector: Any = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 5,
        hints: dict[str, Any] | None = None,
        threshold: float | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        检索实体

        Args:
            query: 查询条件（entity_id或为空）
            vector: 查询向量（暂不使用）
            metadata: 元数据过滤条件（可选）
            top_k: 返回结果数量（默认5）
            hints: 检索策略提示（可选）
            threshold: 相似度阈值（可选）
            **kwargs: 额外参数
                - entity_type: 实体类型过滤
                - property_filters: 属性过滤{"key": "value"}

        Returns:
            实体列表

        Example:
            # 查询所有公司实体
            companies = service.retrieve(
                query="",
                top_k=10,
                entity_type="Company"
            )

            # 查询特定行业的公司
            tech_companies = service.retrieve(
                query="",
                entity_type="Company",
                property_filters={"industry": "Technology"}
            )
        """
        entity_type = kwargs.get("entity_type")
        property_filters = kwargs.get("property_filters", {})

        # 如果 query 是 ID，直接返回
        if query and self.collection.get(query):
            entity = self.collection.get(query)
            if entity:
                return [entity]

        # 否则，遍历所有数据进行过滤
        all_data = list(self.collection.raw_data.values())
        results = []

        for data in all_data:
            # 实体类型过滤
            if entity_type and data.get("metadata", {}).get("entity_type") != entity_type:
                continue

            # 属性过滤
            if property_filters:
                properties = data.get("metadata", {}).get("properties", {})
                if not all(properties.get(k) == v for k, v in property_filters.items()):
                    continue

            results.append(data)

            if len(results) >= top_k:
                break

        logger.debug(f"Retrieved {len(results)} entities matching filters")
        return results

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """
        添加关系边

        Args:
            source_id: 源实体 ID
            target_id: 目标实体 ID
            relation_type: 关系类型 (FOUNDED, CEO, WORKS_AT, etc.)
            properties: 关系属性 (权重、时间等)

        Returns:
            是否添加成功

        Example:
            # 添加工作关系
            service.add_relationship(
                source_id=person_id,
                target_id=company_id,
                relation_type="WORKS_AT",
                properties={"since": 2020, "position": "Engineer"}
            )
        """
        return self._add_edge(source_id, target_id, relation_type, properties or {})

    def get_related_entities(
        self,
        entity_id: str,
        relation_type: str | None = None,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        """
        获取相关实体

        Args:
            entity_id: 实体 ID
            relation_type: 关系类型过滤 (可选)
            direction: 关系方向
                - "outgoing": A→B (源实体是 entity_id)
                - "incoming": B→A (目标实体是 entity_id)
                - "both": 双向

        Returns:
            相关实体列表

        Example:
            # 获取某人创办的所有公司
            founded_companies = service.get_related_entities(
                person_id,
                relation_type="FOUNDED",
                direction="outgoing"
            )

            # 获取某公司的所有员工
            employees = service.get_related_entities(
                company_id,
                relation_type="WORKS_AT",
                direction="incoming"
            )
        """
        graph_index = self.collection.indexes.get("property_graph")
        if not graph_index:
            return []

        # 检查节点是否存在
        if not graph_index.contains(entity_id):
            return []

        # 收集邻居节点（根据方向）
        neighbor_ids = set()

        # GraphIndex 基于 NetworkX，直接访问底层图
        graph = graph_index.graph

        if direction in ("outgoing", "both") and graph.has_node(entity_id):
            # 出边：entity_id -> target
            neighbor_ids.update(graph.successors(entity_id))

        if direction in ("incoming", "both") and graph.has_node(entity_id):
            # 入边：source -> entity_id
            neighbor_ids.update(graph.predecessors(entity_id))

        # 过滤掉节点自己（防止自环）
        neighbor_ids.discard(entity_id)

        # 获取邻居数据
        results = []
        for neighbor_id in neighbor_ids:
            data = self.collection.get(neighbor_id)
            if data:
                # 添加 id 字段
                data["id"] = neighbor_id
                results.append(data)

        return results

    def _add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: dict[str, Any],
    ) -> bool:
        """
        添加边 (内部方法)

        Args:
            source_id: 源节点 ID
            target_id: 目标节点 ID
            relation_type: 关系类型
            properties: 边属性

        Returns:
            是否添加成功
        """
        graph_index = self.collection.indexes.get("property_graph")
        if not graph_index:
            logger.warning("Property graph index not found")
            return False

        # 检查节点是否存在
        if not self.collection.get(source_id):
            logger.warning(f"Source entity {source_id} not found")
            return False
        if not self.collection.get(target_id):
            logger.warning(f"Target entity {target_id} not found")
            return False

        # 确保目标节点在图中
        if target_id not in graph_index.graph:
            target_data = self.collection.get(target_id)
            graph_index.add(target_id, target_data)

        # 添加边 (将 relation_type 作为边的属性)
        edge_properties = {"relation_type": relation_type, **properties}
        weight = properties.get("weight", 1.0)

        graph_index.graph.add_edge(source_id, target_id, weight=weight, **edge_properties)

        logger.debug(f"Added edge: {source_id[:8]}... -{relation_type}-> {target_id[:8]}...")
        return True
