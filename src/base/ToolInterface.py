# src/base/ToolInterface.py
from abc import ABC, abstractmethod

class ToolInterface(ABC):
    @abstractmethod
    def execute(self, argumento: str) -> str:
        pass
