from abc import ABC, abstractmethod

from app.domain.item_group import ItemGroup


class GroupRepositoryPort(ABC):
    @abstractmethod
    def list_groups(self) -> list[ItemGroup]:
        """取得所有分組，依定義順序排列"""
