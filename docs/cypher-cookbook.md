# Cypher 查询手册

> 图谱日常查询速查。连接：`docker exec -it mmkg-neo4j cypher-shell -u neo4j -p <密码>` 或浏览器打开 http://localhost:7474

## 0. 概览统计

```cypher
// 各标签节点数
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY cnt DESC;

// 关系统计
MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt ORDER BY cnt DESC;
```

## 1. 商品与类目

```cypher
// 随机看 10 个商品
MATCH (p:Product) RETURN p.asin, p.title, p.price, p.rating LIMIT 10;

// 类目树（三层）
MATCH path = (root:Category {level: 1})-[:PARENT_OF*1..2]->(c)
RETURN root.name, collect(DISTINCT c.name) AS children LIMIT 10;

// 某类目下评分最高的商品
MATCH (p:Product)-[:IN_CATEGORY]->(c:Category {name: "Shirts"})
RETURN p.title, p.rating, p.rating_count, p.price
ORDER BY p.rating_count DESC LIMIT 10;

// 每个一级类目的商品量分布
MATCH (p:Product)-[:IN_CATEGORY]->(c:Category {level: 1})
RETURN c.name, count(p) AS products ORDER BY products DESC;
```

## 2. 品牌

```cypher
// 商品数最多的品牌
MATCH (b:Brand)<-[:HAS_BRAND]-(p:Product)
RETURN b.name, count(p) AS products, round(avg(p.rating)*100)/100 AS avg_rating
ORDER BY products DESC LIMIT 20;

// 品牌的类目覆盖（品牌×二级类目矩阵）
MATCH (b:Brand {name: "<品牌名>"})<-[:HAS_BRAND]-(p)-[:IN_CATEGORY]->(c {level: 2})
RETURN c.name, count(p) AS cnt ORDER BY cnt DESC;
```

## 3. 价格带与评分（运营洞察）

```cypher
// 按价格带看类目均价
MATCH (p:Product)-[:IN_CATEGORY]->(c:Category {level: 2})
WHERE p.price > 0
RETURN c.name,
       count(*) AS n,
       round(avg(p.price)*100)/100 AS avg_price,
       round(percentileCont(p.price, 0.5)*100)/100 AS median_price
ORDER BY n DESC LIMIT 15;
```

## 4. 共购与搭配（M3 后可用）

```cypher
// 共购最强的商品对
MATCH (a:Product)-[r:CO_PURCHASED]-(b:Product)
RETURN a.title, b.title, r.weight ORDER BY r.weight DESC LIMIT 20;

// 从一件商品出发找搭配（VLM 验证的 PAIRS_WITH）
MATCH (a:Product {asin: "<ASIN>"})-[r:PAIRS_WITH]-(b:Product)
RETURN b.asin, b.title, b.price, r.reason, r.confidence
ORDER BY r.confidence DESC;
```

## 5. 向量检索（M2 后可用）

```cypher
// 以图搜款：给定 query 向量，取最相似 20 个商品
CALL db.index.vector.queryNodes('product_image_vec', 20, $query_embedding)
YIELD node, score
RETURN node.asin, node.title, node.price, score ORDER BY score DESC;

// 向量召回 + 图上过滤（限定类目和价格）——混合检索的雏形
CALL db.index.vector.queryNodes('product_image_vec', 200, $query_embedding)
YIELD node, score
WHERE (node)-[:IN_CATEGORY]->(:Category {name: "Dresses"})
  AND node.price < 50
RETURN node.asin, node.title, score ORDER BY score DESC LIMIT 20;
```

## 6. 管线状态巡检

```cypher
# 各阶段状态分布
MATCH (p:Product)
RETURN p.ingest_status, p.attr_status, p.embed_status, count(*) AS cnt;
```
