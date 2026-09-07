"""VLM 属性抽取：schema 定义、校验与提示词。"""

from pydantic import BaseModel, Field, field_validator

FACETS = ("item_type", "gender", "color", "material", "style")
SEASONS = {"spring", "summer", "fall", "winter", "all_season"}
OCCASIONS = {"casual", "party", "work", "date", "outdoor", "sport", "travel", "home", "formal"}
GENDERS = {"men", "women", "unisex", "boys", "girls", "kids"}


class ProductAttributes(BaseModel):
    """VLM 抽取结果。统一英文规范值（与数据语言一致），查询层再做中文映射。"""

    item_type: str = Field(description="细分品类，如 running shoes / floral maxi dress")
    gender: str = "unisex"
    color: str | None = None
    material: str | None = None
    style: str | None = None
    season: list[str] = []
    occasion: list[str] = []

    @field_validator("item_type", "color", "material", "style")
    @classmethod
    def _norm(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lower()
        return v or None

    @field_validator("gender")
    @classmethod
    def _gender(cls, v: str) -> str:
        v = (v or "").strip().lower()
        return v if v in GENDERS else "unisex"

    @field_validator("season")
    @classmethod
    def _season(cls, v: list[str]) -> list[str]:
        out = [x.strip().lower() for x in v or [] if x.strip().lower() in SEASONS]
        return out or ["all_season"]

    @field_validator("occasion")
    @classmethod
    def _occasion(cls, v: list[str]) -> list[str]:
        return [x.strip().lower() for x in v or [] if x.strip().lower() in OCCASIONS]


SYSTEM_PROMPT = """You are a precise fashion e-commerce data extraction engine. \
Given one product image (and its listing title), extract structured attributes. \
Output ONLY one JSON object, no markdown, no explanation."""

USER_TEMPLATE = """Extract attributes for this clothing product.

Title: {title}

Rules:
- "item_type": specific garment category in 1-4 English words (e.g. "running shoes", "floral maxi dress", "leather bomber jacket")
- "gender": one of men / women / unisex / boys / girls / kids
- "color": dominant color as a single English word (e.g. "navy", "beige"); null if unclear
- "material": fabric in 1-2 English words (e.g. "cotton", "pu leather"); null if unclear
- "style": one English word (e.g. "casual", "formal", "streetwear", "vintage", "bohemian"); null if unclear
- "season": subset of ["spring","summer","fall","winter","all_season"]
- "occasion": subset of ["casual","party","work","date","outdoor","sport","travel","home","formal"]

Output JSON exactly in this shape:
{{"item_type": "...", "gender": "...", "color": "...", "material": "...", "style": "...", "season": [...], "occasion": [...]}}"""


def build_user_prompt(title: str) -> str:
    return USER_TEMPLATE.format(title=title.replace("{", "").replace("}", ""))
