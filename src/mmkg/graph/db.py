"""Neo4j 访问层：轻量封装，屏蔽驱动细节。"""

from collections.abc import Iterable
from typing import Any

from neo4j import GraphDatabase


class Neo4jStore:
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        self._driver.verify_connectivity()

    @classmethod
    def from_settings(cls, settings) -> "Neo4jStore":
        return cls(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    def close(self) -> None:
        self._driver.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # —— 基础执行 ——

    def run(self, cypher: str, **params: Any) -> list[dict]:
        """执行只读/DDL 语句，返回记录列表。"""
        with self._driver.session(database=self._database) as s:
            return [r.data() for r in s.run(cypher, **params)]

    def run_raw(self, cypher: str, **params: Any) -> list[Any]:
        """同 run，但保留驱动原始 Record（节点/关系对象带 element_id/labels 等方法）。"""
        with self._driver.session(database=self._database) as s:
            return list(s.run(cypher, **params))

    def write_batch(self, cypher: str, rows: Iterable[dict], batch_size: int = 500) -> int:
        """分批 UNWIND 写入，返回处理的行数。cypher 中用 $rows 引用批数据。"""
        total = 0
        buf: list[dict] = []
        for row in rows:
            buf.append(row)
            if len(buf) >= batch_size:
                total += self._flush(cypher, buf)
                buf = []
        if buf:
            total += self._flush(cypher, buf)
        return total

    def _flush(self, cypher: str, batch: list[dict]) -> int:
        with self._driver.session(database=self._database) as s:
            def _tx(tx):
                tx.run(cypher, rows=batch).consume()
            s.execute_write(_tx)
        return len(batch)

    # —— 常用查询 ——

    def counts(self) -> dict[str, int]:
        rows = self.run(
            """
            MATCH (n) WHERE n:Product OR n:Brand OR n:Category OR n:AttributeValue OR n:Occasion OR n:Outfit
            WITH [x IN labels(n) WHERE x IN ['Product','Brand','Category','AttributeValue','Occasion','Outfit']][0] AS lbl, count(*) AS c
            RETURN lbl, c ORDER BY lbl
            """
        )
        return {r["lbl"]: r["c"] for r in rows}

    def rel_counts(self) -> dict[str, int]:
        rows = self.run(
            """
            MATCH ()-[r]->()
            WITH type(r) AS t, count(*) AS c
            RETURN t, c ORDER BY t
            """
        )
        return {r["t"]: r["c"] for r in rows}

    def server_info(self) -> dict:
        rows = self.run("CALL dbms.components() YIELD name, versions RETURN name, versions LIMIT 1")
        return rows[0] if rows else {}
