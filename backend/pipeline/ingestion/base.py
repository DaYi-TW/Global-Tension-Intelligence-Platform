"""
BaseAdapter — 所有資料來源 Adapter 的共同介面
"""

from abc import ABC, abstractmethod
from typing import TypedDict


class RawEventDict(TypedDict):
    source_type:     str
    source_event_id: str
    raw_payload:     dict


class BaseAdapter(ABC):

    @abstractmethod
    async def fetch(self) -> list[RawEventDict]:
        """抓取原始資料，回傳 RawEventDict 列表"""
        ...

    @abstractmethod
    def get_source_type(self) -> str:
        """回傳來源識別字串，如 'gdelt' | 'acled' | 'newsapi'"""
        ...
