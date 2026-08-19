import os
from typing import Any

from dotenv import load_dotenv

from src.query_processor.base import NodeBase
from src.query_processor.state import QueryGraphState
from tool.logger import logger
from utils.embedding_utils import generate_embeddings
from utils.milvus_utils import (
    create_hybrid_search_requests,
    escape_milvus_string,
    get_milvus_client,
    hybrid_search,
)

load_dotenv()


class NodeSearchEmbedding(NodeBase):
    """根据改写后的问题和已确认的商品名执行 Milvus 混合向量检索。"""

    name: str = "node_search_embedding"

    def process(self, state: QueryGraphState) -> dict[str, Any]:
        """生成稠密/稀疏向量并返回供下游节点使用的检索片段。"""
        try:
            query = state.get("rewritten_query")
            item_names = state.get("item_names", [])

            # 2026-08-16：先校验查询文本，避免将 None 传给向量模型而触发类型及运行时错误。
            if not query:
                logger.error("改写后的查询为空，无法生成向量")
                return {"embedding_chunks": []}

            embeddings = generate_embeddings([query])
            dense_vectors = embeddings.get("dense")
            sparse_vectors = embeddings.get("sparse")
            if not dense_vectors or not sparse_vectors:
                logger.error("向量生成失败")
                return {"embedding_chunks": []}

            dense_vec = dense_vectors[0]
            sparse_vec = sparse_vectors[0]

            # 2026-08-16：Milvus 集合名是必填字符串，缺失配置时提前返回明确错误。
            collection_name = os.getenv("CHUNKS_COLLECTION")
            if not collection_name:
                logger.error("环境变量 CHUNKS_COLLECTION 未配置")
                return {"embedding_chunks": []}

            expr: str | None = None
            if item_names:
                # 2026-08-16：逐项转义并显式加引号，防止特殊字符破坏 Milvus 过滤表达式。
                quoted_names = ", ".join(
                    f'"{escape_milvus_string(item_name)}"' for item_name in item_names
                )
                expr = f"item_name in [{quoted_names}]"
                logger.info(f"过滤条件: {expr}")
            else:
                logger.info("未指定商品名过滤，将全库检索")

            reqs = create_hybrid_search_requests(
                dense_vector=dense_vec,
                sparse_vector=sparse_vec,
                expr=expr,
                limit=10,
            )

            logger.info("开始执行 Milvus 混合检索...")
            client = get_milvus_client()
            res = hybrid_search(
                client=client,
                collection_name=collection_name,
                reqs=reqs,
                ranker_weights=(0.8, 0.2),
                output_fields=["chunk_id", "content", "item_name"],
            )

            return {"embedding_chunks": res[0] if res else []}
        except Exception as exc:
            logger.exception(f"向量搜索失败: {exc}")
            return {"embedding_chunks": []}
