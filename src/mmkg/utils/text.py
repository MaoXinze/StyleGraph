"""文本/哈希工具：标题规范化去重、图像感知哈希。"""

import hashlib
import re

from PIL import Image


def normalize_title(title: str) -> str:
    """标题规范化：小写、撇号不拆词（men's→mens）、标点转空格、压空白。"""
    s = title.lower()
    s = re.sub(r"['’`´]", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_fingerprint(title: str) -> str:
    return hashlib.sha1(normalize_title(title).encode()).hexdigest()


def phash_of_image(img: Image.Image) -> str:
    """8x8 感知哈希（dHash 近似）：直接用像素梯度，避免额外依赖。"""
    g = img.convert("L").resize((9, 8), Image.LANCZOS)
    px = list(g.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            left = px[row * 9 + col]
            right = px[row * 9 + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return f"{bits:016x}"
