from app.domain.item import Item
from app.ports.item_repository_port import ItemRepositoryPort


class InMemoryItemRepository(ItemRepositoryPort):
    def __init__(self):
        self._storage: dict[str, Item] = {
            "baro_01": Item(
                id="baro_01",
                name_en="Primed Continuity",
                name_tc="持久力 Prime",
                category="baro",
                current_price=45,
                user_price=45,
                is_visible=True,
            ),
            "baro_02": Item(
                id="baro_02",
                name_en="Primed Target Cracker",
                name_tc="弱點專精 Prime",
                category="baro",
                current_price=50,
                user_price=50,
                is_visible=True,
            ),
            "baro_03": Item(
                id="baro_03",
                name_en="Primed Flow",
                name_tc="川流不息 Prime",
                category="baro",
                current_price=60,
                user_price=58,
                is_visible=False,
            ),
        }

    async def get_by_category(self, category: str) -> list[Item]:
        return [item for item in self._storage.values() if item.category == category]

    async def get_by_id(self, item_id: str) -> Item | None:
        return self._storage.get(item_id)

    async def save(self, item: Item) -> None:
        self._storage[item.id] = item
