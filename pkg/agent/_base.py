from abc import ABC

from pydantic import BaseModel, Field


class BaseNode(BaseModel, ABC):
    name: str = Field(..., description="Node name")
