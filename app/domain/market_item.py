from dataclasses import dataclass, field


@dataclass(frozen=True)
class ItemNames:
    """物品多語名稱，對應官方 i18n 的 en / zh-hant / zh-hans"""

    en: str
    zh_hant: str | None = None
    zh_hans: str | None = None

    def get(self, language: str) -> str:
        """依語言取得名稱，缺少該語言時退回英文"""
        normalized = language.replace("-", "_").lower()
        return getattr(self, normalized, None) or self.en


@dataclass(frozen=True)
class MarketItem:
    """Warframe.market 物品目錄中的單一物品，欄位語意對應官方 /v2/items"""

    id: str
    slug: str
    names: ItemNames
    tags: tuple[str, ...] = ()
    game_ref: str | None = None
    thumb: str | None = None
    icon: str | None = None
    sub_icon: str | None = None
    max_rank: int | None = None
    ducats: int | None = None
    vaulted: bool | None = None
    bulk_tradable: bool | None = None
    subtypes: tuple[str, ...] = field(default=())

    @property
    def image(self) -> str | None:
        """列表顯示用圖片：優先使用縮圖，沒有時退回原圖"""
        return self.thumb or self.icon

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags
