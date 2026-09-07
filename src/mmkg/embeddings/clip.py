"""CLIP 编码器：图文同空间向量（本地 GPU）。

ViT-B-32/openai → 512 维；图片缺失/损坏返回 None，不拖垮整批。
"""

import logging
from pathlib import Path

import numpy as np
import torch
from PIL import Image

log = logging.getLogger(__name__)


class ClipEncoder:
    def __init__(self, model_name: str = "ViT-B-32", pretrained: str = "openai",
                 device: str | None = None):
        from mmkg.config import get_settings

        import open_clip

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        cache_dir = get_settings().clip_cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, cache_dir=str(cache_dir))
        self.model = self.model.to(self.device).eval()
        self.tokenizer = open_clip.get_tokenizer(model_name)
        self.dim = self.model.embed_dim
        log.info("CLIP %s/%s 就绪：%s，维度 %d", model_name, pretrained, self.device, self.dim)

    @torch.no_grad()
    def encode_images(self, paths: list[Path | None], batch_size: int = 64) -> list[list[float] | None]:
        """逐图预处理（容错），成批编码。返回与输入等长的列表，失败项为 None。"""
        feats: list[list[float] | None] = [None] * len(paths)
        pix: list[torch.Tensor] = []
        idx: list[int] = []
        for i, p in enumerate(paths):
            if not p:
                continue
            try:
                with Image.open(p) as img:
                    pix.append(self.preprocess(img.convert("RGB")))
                idx.append(i)
            except Exception as e:  # noqa: BLE001
                log.debug("图片不可用 %s: %s", p, e)
        for s in range(0, len(pix), batch_size):
            batch = torch.stack(pix[s:s + batch_size]).to(self.device)
            f = self.model.encode_image(batch).float().cpu().numpy()
            f = f / np.linalg.norm(f, axis=1, keepdims=True)
            for j, emb in zip(idx[s:s + batch_size], f):
                feats[j] = emb.tolist()
        return feats

    @torch.no_grad()
    def encode_texts(self, texts: list[str], batch_size: int = 256) -> list[list[float]]:
        feats: list[list[float]] = []
        for s in range(0, len(texts), batch_size):
            toks = self.tokenizer(texts[s:s + batch_size]).to(self.device)
            f = self.model.encode_text(toks).float().cpu().numpy()
            f = f / np.linalg.norm(f, axis=1, keepdims=True)
            feats.extend(f.tolist())
        return feats
