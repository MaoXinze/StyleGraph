"""元数据行 → 标准商品记录的规范化与过滤（纯函数，便于单测）。"""

import re

from mmkg.utils.text import title_fingerprint

MIN_TITLE_LEN = 10
MIN_IMAGE_BYTES = 3 * 1024  # 下载校验用


def pick_image_url(images: list) -> str | None:
    """优先 large（~500px，CLIP 输入 224px 的最佳来源）；thumb 仅 38px 太小。"""
    for key in ("large", "variant", "hi_res", "thumb"):
        for img in images or []:
            url = img.get(key)
            if url:
                return url
    return None


def to_float(v) -> float | None:
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def thumb_url_to_large(url: str) -> str:
    """Amazon 图片 CDN 支持按图片 ID 动态出尺寸：把任意变体后缀换成 ~500px 版本。

    例：.../I/318p7apYldL._AC_SR38,50_.jpg -> .../I/318p7apYldL._AC_SL500_.jpg
    """
    m = re.match(r"(.*/images/I/[^.]+)\..*", url)
    return f"{m.group(1)}._AC_SL500_.jpg" if m else url


def build_category_nodes(cats) -> list[dict]:
    """扁平类目列表（['Clothing, Shoes & Jewelry','Men','Shoes']）→ 层级节点。

    相邻重名去重（避免 PARENT_OF 自环），最多保留 6 级。
    """
    path: list[str] = []
    for c in cats or []:
        if isinstance(c, str) and c.strip() and (not path or path[-1] != c.strip()):
            path.append(c.strip())
    return [
        {"id": "/".join(path[: i + 1]), "name": path[i], "level": i + 1}
        for i in range(min(len(path), 6))
    ]


def row_to_product(row: dict, min_rating_count: int) -> dict | None:
    """合格返回标准化记录，不合格返回 None（缺图/缺价/标题过短/评分过少）。"""
    asin = (row.get("parent_asin") or row.get("asin") or "").strip()
    title = (row.get("title") or "").strip()
    price = to_float(row.get("price"))
    rating_count = int(row.get("rating_number") or 0)
    image_url = pick_image_url(row.get("images") or [])

    if not asin or len(title) < MIN_TITLE_LEN or price is None:
        return None
    if rating_count < min_rating_count or not image_url:
        return None

    description = row.get("description")
    if isinstance(description, list):
        description = " ".join(str(x) for x in description)
    features = row.get("features") or []

    store = (row.get("store") or "").strip() or None

    category_nodes = build_category_nodes(row.get("categories"))

    return {
        "asin": asin,
        "title": title,
        "title_fp": title_fingerprint(title),
        "price": price,
        "rating": to_float(row.get("average_rating")) or 0.0,
        "rating_count": rating_count,
        "store": store,
        "features": [str(f) for f in features[:5]],
        "description": (description or "").strip()[:1000],
        "image_url": image_url,
        "image_file": None,
        "phash": None,
        "duplicate_of": None,
        "download_status": "pending",
        "category_nodes": category_nodes,
    }


def category_edges(nodes: list[dict]) -> list[dict]:
    """类目链的父子边：[{parent, child}]。"""
    return [
        {"parent": a["id"], "child": b["id"]}
        for a, b in zip(nodes, nodes[1:])
        if a["level"] + 1 == b["level"]
    ]
