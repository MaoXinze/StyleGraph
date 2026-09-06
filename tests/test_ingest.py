"""ingest 纯函数单元测试（无网络依赖）。"""

from mmkg.ingest.filters import category_edges, pick_image_url, row_to_product, thumb_url_to_large
from mmkg.utils.text import normalize_title, title_fingerprint


def make_row(**over):
    row = {
        "parent_asin": "B0TEST0001",
        "title": "Men's Classic Cotton Oxford Button Down Shirt Long Sleeve",
        "price": 29.99,
        "average_rating": 4.3,
        "rating_number": 156,
        "store": "ExampleBrand",
        "description": ["A comfortable shirt."],
        "features": ["100% cotton", "Machine washable"],
        "images": [{"thumb": "https://m.media-amazon.com/images/I/t.jpg",
                    "large": "https://m.media-amazon.com/images/I/l.jpg"}],
        "categories": ["Clothing, Shoes & Jewelry", "Men", "Shirts"],
    }
    row.update(over)
    return row


def test_row_to_product_accepts_valid():
    rec = row_to_product(make_row(), min_rating_count=10)
    assert rec is not None
    assert rec["asin"] == "B0TEST0001"
    assert rec["price"] == 29.99
    assert rec["image_url"].endswith("l.jpg")  # large 优先（CLIP 输入需要 224px+）
    assert rec["category_nodes"][0] == {
        "id": "Clothing, Shoes & Jewelry", "name": "Clothing, Shoes & Jewelry", "level": 1}
    assert rec["category_nodes"][-1] == {"id": "Clothing, Shoes & Jewelry/Men/Shirts", "name": "Shirts", "level": 3}


def test_build_category_nodes_dedupes_adjacent_and_caps_depth():
    from mmkg.ingest.filters import build_category_nodes
    nodes = build_category_nodes(["Clothing, Shoes & Jewelry", "Men", "Men", "Shoes", "Outdoor", "Hiking", "B", "C"])
    names = [n["name"] for n in nodes]
    assert "Men" in names and names.count("Men") == 1
    assert len(nodes) <= 6


def test_row_to_product_rejects_incomplete():
    assert row_to_product(make_row(images=[]), 10) is None            # 无图
    assert row_to_product(make_row(price=None), 10) is None           # 无价
    assert row_to_product(make_row(rating_number=3), 10) is None      # 评分过少
    assert row_to_product(make_row(title="short"), 10) is None        # 标题过短


def test_title_fingerprint_stable_and_insensitive():
    a = title_fingerprint("Men's  Shirt, LONG-SLEEVE!")
    b = title_fingerprint("mens shirt long sleeve")
    assert a == b
    assert normalize_title("  A   B-C! ") == "a b c"


def test_category_edges_builds_chain():
    nodes = [
        {"id": "Clothing", "name": "Clothing", "level": 1},
        {"id": "Clothing/Men", "name": "Men", "level": 2},
        {"id": "Clothing/Men/Shirts", "name": "Shirts", "level": 3},
    ]
    edges = category_edges(nodes)
    assert edges == [
        {"parent": "Clothing", "child": "Clothing/Men"},
        {"parent": "Clothing/Men", "child": "Clothing/Men/Shirts"},
    ]


def test_pick_image_url_fallback():
    assert pick_image_url([{"large": "L"}]) == "L"
    assert pick_image_url([{"thumb": "T", "large": "L"}]) == "L"  # large 优先（thumb 仅 38px）
    assert pick_image_url([{"thumb": "T"}]) == "T"
    assert pick_image_url([]) is None


def test_thumb_url_to_large():
    assert thumb_url_to_large(
        "https://m.media-amazon.com/images/I/318p7apYldL._AC_SR38,50_.jpg"
    ) == "https://m.media-amazon.com/images/I/318p7apYldL._AC_SL500_.jpg"
    assert thumb_url_to_large(
        "https://m.media-amazon.com/images/I/71abc+123._SX38_SY50_.jpg"
    ) == "https://m.media-amazon.com/images/I/71abc+123._AC_SL500_.jpg"
