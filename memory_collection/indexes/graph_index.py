"""GraphIndex - 基于 NetworkX 的图索引实现

用于存储和查询实体之间的关系网络。支持：
- 实体关系存储（节点+边）
- 图遍历查询（BFS/DFS）
- K-hop 邻居查询
- 完整的持久化支持

典型用法：
    >>> config = {
    ...     "relation_key": "related_to",  # 指定关系字段
    ...     "directed": True,               # 是否有向图
    ... }
    >>> index = GraphIndex(config)
    >>> index.add("entity1", {"related_to": ["entity2", "entity3"]})
    >>> neighbors = index.query("entity1", hop=2)  # 2-hop 邻居
"""

import json
from pathlib import Path
from typing import Any

try:
    import networkx as nx
except ImportError as e:
    raise ImportError("GraphIndex requires networkx. Install with: pip install networkx") from e

from .base_index import BaseIndex


class GraphIndex(BaseIndex):
    """基于 NetworkX 的图索引

    存储实体之间的关系，支持图遍历查询。

    配置参数：
        relation_key (str): 数据中表示关系的字段名，默认 "related_to"
        directed (bool): 是否为有向图，默认 True
        default_weight (float): 边的默认权重，默认 1.0

    数据格式示例：
        {
            "id": "entity1",
            "related_to": ["entity2", "entity3"],  # relation_key 字段
            "weights": {"entity2": 0.8, "entity3": 0.5}  # 可选：边权重
        }
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化图索引

        Args:
            config: 配置字典，支持：
                - relation_key: 关系字段名（默认 "related_to"）
                - directed: 是否有向图（默认 True）
                - default_weight: 默认边权重（默认 1.0）
        """
        super().__init__(config)
        self.relation_key = self.config.get("relation_key", "related_to")
        self.directed = self.config.get("directed", True)
        self.default_weight = self.config.get("default_weight", 1.0)

        # 创建图
        if self.directed:
            self.graph = nx.DiGraph()
        else:
            self.graph = nx.Graph()

    def add(self, data_id: str, data: dict[str, Any]) -> bool:
        """添加实体及其关系到图中

        Args:
            data_id: 实体 ID
            data: 实体数据，需包含 relation_key 字段

        Returns:
            是否添加成功
        """
        # 添加节点
        self.graph.add_node(data_id, **data)

        # 添加边（如果有关系字段）
        if self.relation_key in data:
            related_ids = data[self.relation_key]
            if not isinstance(related_ids, list):
                related_ids = [related_ids]

            # 获取权重（如果有）
            weights = data.get("weights", {})

            for target_id in related_ids:
                weight = weights.get(target_id, self.default_weight)
                self.graph.add_edge(data_id, target_id, weight=weight)

        return True

    def remove(self, data_id: str) -> bool:
        """从图中移除实体

        Args:
            data_id: 实体 ID

        Returns:
            是否移除成功
        """
        if data_id not in self.graph:
            return False

        self.graph.remove_node(data_id)
        return True

    def query(
        self, query: Any, top_k: int = 10, threshold: float | None = None, **kwargs
    ) -> list[str]:
        """图遍历查询

        Args:
            query: 查询参数，可以是：
                - str: 单个起始节点 ID
                - List[str]: 多个起始节点 ID
            top_k: 最多返回多少个邻居（默认 10）
            threshold: 未使用（兼容接口）
            **kwargs: 额外参数：
                - hop (int): 遍历深度，默认 1
                - traversal (str): 遍历方式，"bfs" 或 "dfs"，默认 "bfs"
                - include_start (bool): 是否包含起始节点，默认 True

        Returns:
            遍历到的节点 ID 列表

        示例:
            >>> # 1-hop 邻居（包含起点）
            >>> index.query("entity1", hop=1)
            >>> # 2-hop 邻居（不包含起点）
            >>> index.query("entity1", hop=2, include_start=False)
            >>> # 多起点查询
            >>> index.query(["entity1", "entity2"], hop=1)
        """
        hop = kwargs.get("hop", 1)
        traversal = kwargs.get("traversal", "bfs")
        include_start = kwargs.get("include_start", True)

        # 统一处理单个或多个起点
        start_nodes = [query] if isinstance(query, str) else list(query)

        # 检查起点是否存在
        valid_starts = [n for n in start_nodes if n in self.graph]
        if not valid_starts:
            return []

        # 执行遍历
        if traversal == "dfs":
            neighbors = self._dfs_neighbors(valid_starts, hop)
        else:
            neighbors = self._bfs_neighbors(valid_starts, hop)

        # 是否包含起始节点
        if not include_start:
            neighbors = [n for n in neighbors if n not in start_nodes]

        # 限制返回数量
        return neighbors[:top_k]

    def _bfs_neighbors(self, start_nodes: list[str], hop: int) -> list[str]:
        """BFS 遍历获取 K-hop 邻居"""
        visited = set(start_nodes)
        current_level = set(start_nodes)

        for _ in range(hop):
            next_level = set()
            for node in current_level:
                if node in self.graph:
                    # 获取所有邻居（有向图和无向图都支持 neighbors()）
                    if self.directed:
                        neighbors = set(self.graph.successors(node))
                    else:
                        neighbors = set(self.graph.neighbors(node))
                    next_level.update(neighbors - visited)

            visited.update(next_level)
            current_level = next_level

            if not current_level:
                break

        return list(visited)

    def _dfs_neighbors(self, start_nodes: list[str], hop: int) -> list[str]:
        """DFS 遍历获取 K-hop 邻居"""
        visited = set()

        def dfs(node: str, depth: int):
            if depth > hop or node in visited:
                return
            visited.add(node)

            if depth < hop and node in self.graph:
                # 获取邻居（有向图和无向图）
                if self.directed:
                    neighbors = self.graph.successors(node)
                else:
                    neighbors = self.graph.neighbors(node)

                for neighbor in neighbors:
                    dfs(neighbor, depth + 1)

        for start in start_nodes:
            if start in self.graph:
                dfs(start, 0)

        return list(visited)

    def contains(self, data_id: str) -> bool:
        """检查实体是否在图中

        Args:
            data_id: 实体 ID

        Returns:
            是否存在
        """
        return data_id in self.graph

    def size(self) -> int:
        """返回图中节点数量

        Returns:
            节点数量
        """
        return self.graph.number_of_nodes()

    def save(self, path: Path) -> bool:
        """保存图到磁盘

        Args:
            path: 保存路径（目录）

        Returns:
            是否保存成功
        """
        try:
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)

            # 保存配置
            config_path = path / "config.json"
            with open(config_path, "w") as f:
                json.dump(self.config, f, indent=2)

            # 保存图结构
            # 创建副本以处理不兼容的属性类型
            graph_copy = self.graph.copy()

            # GraphML 不支持列表和复杂类型，需要序列化为字符串
            for _node, data in graph_copy.nodes(data=True):
                for key, value in list(data.items()):
                    if isinstance(value, (list, dict)):
                        data[f"{key}_json"] = json.dumps(value)
                        del data[key]

            # 保存图（使用 GraphML 格式）
            graph_path = path / "graph.graphml"
            nx.write_graphml(graph_copy, str(graph_path))

            return True

        except Exception as e:
            print(f"Failed to save GraphIndex: {e}")
            return False

    def load(self, path: Path) -> bool:
        """从磁盘加载图

        Args:
            path: 加载路径（目录）

        Returns:
            是否加载成功
        """
        try:
            path = Path(path)
            if not path.exists():
                return False

            # 加载配置
            config_path = path / "config.json"
            if config_path.exists():
                with open(config_path) as f:
                    self.config = json.load(f)
                    self.relation_key = self.config.get("relation_key", "related_to")
                    self.directed = self.config.get("directed", True)
                    self.default_weight = self.config.get("default_weight", 1.0)

            # 加载图结构
            graph_path = path / "graph.graphml"
            if graph_path.exists():
                self.graph = nx.read_graphml(str(graph_path))

                # 反序列化 JSON 字段
                for _node, data in self.graph.nodes(data=True):
                    for key in list(data.keys()):
                        if key.endswith("_json"):
                            original_key = key[:-5]  # 移除 "_json" 后缀
                            data[original_key] = json.loads(data[key])
                            del data[key]

                # GraphML 加载后会丢失有向/无向信息，需要转换
                if self.directed and not isinstance(self.graph, nx.DiGraph):
                    self.graph = nx.DiGraph(self.graph)
                elif not self.directed and not isinstance(self.graph, nx.Graph):
                    self.graph = nx.Graph(self.graph)

            return True

        except Exception as e:
            print(f"Failed to load GraphIndex: {e}")
            return False

    def get_neighbors(self, data_id: str, hop: int = 1) -> list[str]:
        """获取指定节点的邻居（快捷方法）

        Args:
            data_id: 节点 ID
            hop: 跳数（默认 1）

        Returns:
            邻居节点 ID 列表
        """
        return self.query(data_id, hop=hop, top_k=10000)

    def get_degree(self, data_id: str) -> int:
        """获取节点的度数

        Args:
            data_id: 节点 ID

        Returns:
            度数（有向图返回出度）
        """
        if data_id not in self.graph:
            return 0
        return self.graph.out_degree(data_id)

    def get_edge_weight(self, source: str, target: str) -> float | None:
        """获取边的权重

        Args:
            source: 源节点 ID
            target: 目标节点 ID

        Returns:
            边权重，不存在返回 None
        """
        if self.graph.has_edge(source, target):
            return self.graph[source][target].get("weight", self.default_weight)
        return None

    def clear(self) -> None:
        """清空图索引

        清除所有节点和边，重置图为空状态。
        """
        self.graph.clear()
