from dataclasses import dataclass


@dataclass
class Item:
    id: str
    name_en: str
    name_tc: str
    category: str
    current_price: int
    user_price: int
    is_visible: bool = True

    def update_user_price(self, new_price: int) -> None:
        if new_price < 0:
            raise ValueError("價格不能為負數")
        self.user_price = new_price

    def set_visibility(self, visible: bool) -> None:
        self.is_visible = visible
