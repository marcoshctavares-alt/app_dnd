from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
AbilityKey = Literal["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
DamageDice = Annotated[str, StringConstraints(pattern=r"^\d{0,2}d(4|6|8|10|12|20|100)$")]


class Item(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: Name
    kind: Literal["weapon", "armor", "shield", "gear"] = "gear"
    catalog_id: str | None = None
    quantity: int = Field(default=1, ge=1, le=9999)
    weight: float = Field(default=0, ge=0, le=100000)
    equipped: bool = False
    notes: str | None = Field(default=None, max_length=500)


class Attack(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: Name
    ability: AbilityKey = "strength"
    proficient: bool = True
    damage_dice: DamageDice = "1d6"
    damage_type: str = Field(default="", max_length=50)
    to_hit_bonus: int = Field(default=0, ge=-20, le=20)
    damage_bonus: int = Field(default=0, ge=-20, le=20)
    weapon_id: str | None = None
    off_hand: bool = False
    off_hand_modifier: bool = False


class Coins(BaseModel):
    cp: int = Field(default=0, ge=0)
    sp: int = Field(default=0, ge=0)
    ep: int = Field(default=0, ge=0)
    gp: int = Field(default=0, ge=0)
    pp: int = Field(default=0, ge=0)

    @property
    def total_gp(self) -> float:
        return self.cp / 100 + self.sp / 10 + self.ep / 2 + self.gp + self.pp * 10

    @property
    def count(self) -> int:
        return self.cp + self.sp + self.ep + self.gp + self.pp
