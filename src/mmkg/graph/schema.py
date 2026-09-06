"""图谱 schema 定义与初始化（约束 + 索引）。

本体设计（详见 docs/architecture.md）：
  节点  Product / Brand / Category(类目树) / AttributeValue(facet=value) / Occasion / Outfit
  关系  HAS_BRAND / IN_CATEGORY / PARENT_OF(类目树) / HAS_ATTRIBUTE / SUITABLE_FOR
        CO_PURCHASED(共购) / PAIRS_WITH(VLM 搭配，M3) / IN_OUTFIT(M3)
  向量  Product.image_embedding / text_embedding（M2 建向量索引）
"""

from neo4j.exceptions import ClientError

CONSTRAINTS = [
    ("product_asin", "CREATE CONSTRAINT product_asin IF NOT EXISTS FOR (p:Product) REQUIRE p.asin IS UNIQUE"),
    ("brand_name", "CREATE CONSTRAINT brand_name IF NOT EXISTS FOR (b:Brand) REQUIRE b.name IS UNIQUE"),
    ("category_id", "CREATE CONSTRAINT category_id IF NOT EXISTS FOR (c:Category) REQUIRE c.id IS UNIQUE"),
    ("attribute_value_key", "CREATE CONSTRAINT attribute_value_key IF NOT EXISTS FOR (a:AttributeValue) REQUIRE a.key IS UNIQUE"),
    ("occasion_name", "CREATE CONSTRAINT occasion_name IF NOT EXISTS FOR (o:Occasion) REQUIRE o.name IS UNIQUE"),
    ("outfit_id", "CREATE CONSTRAINT outfit_id IF NOT EXISTS FOR (of:Outfit) REQUIRE of.id IS UNIQUE"),
]

# 查询热路径上的范围索引
INDEXES = [
    "CREATE INDEX product_ingest_status IF NOT EXISTS FOR (p:Product) ON (p.ingest_status)",
    "CREATE INDEX product_attr_status IF NOT EXISTS FOR (p:Product) ON (p.attr_status)",
    "CREATE INDEX product_rating IF NOT EXISTS FOR (p:Product) ON (p.rating_count)",
]

# M2 建向量索引（维度取决于 CLIP 模型，ViT-B/32 = 512）
VECTOR_INDEXES = {
    "product_image_vec": (
        "CREATE VECTOR INDEX product_image_vec IF NOT EXISTS FOR (p:Product) ON (p.image_embedding) "
        "OPTIONS {indexConfig: {`vector.dimensions`: 512, `vector.similarity_function`: 'cosine'}}"
    ),
    "product_text_vec": (
        "CREATE VECTOR INDEX product_text_vec IF NOT EXISTS FOR (p:Product) ON (p.text_embedding) "
        "OPTIONS {indexConfig: {`vector.dimensions`: 512, `vector.similarity_function`: 'cosine'}}"
    ),
}


def init_schema(store, with_vector: bool = False) -> list[str]:
    """幂等初始化约束与索引，返回执行过的语句说明。"""
    applied: list[str] = []
    for name, stmt in CONSTRAINTS:
        store.run(stmt)
        applied.append(f"constraint:{name}")
    for stmt in INDEXES:
        store.run(stmt)
        applied.append(f"index:{stmt.split()[2]}")
    if with_vector:
        for name, stmt in VECTOR_INDEXES.items():
            try:
                store.run(stmt)
                applied.append(f"vector-index:{name}")
            except ClientError as e:  # 维度不匹配等：留到 M2 处理
                applied.append(f"vector-index:{name}:SKIPPED({e.code})")
    return applied
