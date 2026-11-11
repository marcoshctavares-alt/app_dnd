from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4

from .equipment import Attack, Coins, Item
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Ruleset = Literal["dnd-5e-2014", "dnd-5e-2024"]
Score = Annotated[int, Field(ge=1, le=30)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(max_length=100)]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AbilityScores(BaseModel):
    strength: Score = 10
    dexterity: Score = 10
    constitution: Score = 10
    intelligence: Score = 10
    wisdom: Score = 10
    charisma: Score = 10

    def modifier(self, ability: str) -> int:
        return ability_modifier(getattr(self, ability))


class HitPoints(BaseModel):
    current: int = Field(ge=0)
    maximum: int = Field(ge=1)
    temporary: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _current_within_maximum(self) -> "HitPoints":
        if self.current > self.maximum:
            raise ValueError("PV atuais não podem exceder o máximo")
        return self


class SpellBook(BaseModel):
    known: list[str] = Field(default_factory=list)
    prepared: list[str] = Field(default_factory=list)
    slots_used: dict[int, int] = Field(default_factory=dict)

    @field_validator("slots_used")
    @classmethod
    def _valid_slots(cls, value: dict[int, int]) -> dict[int, int]:
        for level, used in value.items():
            if not 1 <= level <= 9 or used < 0:
                raise ValueError("Espaços de magia inválidos")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> "SpellBook":
        if len(set(self.known)) != len(self.known) or len(set(self.prepared)) != len(self.prepared):
            raise ValueError("Magias duplicadas")
        if not set(self.prepared) <= set(self.known):
            raise ValueError("Toda magia preparada precisa estar na lista da ficha")
        return self


class SkillProficiencies(BaseModel):
    proficient: list[str] = Field(default_factory=list)
    expertise: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _valid(self) -> "SkillProficiencies":
        from app_dnd.data.skills import SKILLS

        for lst in (self.proficient, self.expertise):
            if len(set(lst)) != len(lst) or not set(lst) <= set(SKILLS):
                raise ValueError("Perícias inválidas ou repetidas")
        if not set(self.expertise) <= set(self.proficient):
            raise ValueError("Especialização exige proficiência na perícia")
        return self


class Profile(BaseModel):
    background: str = Field(default="", max_length=100)
    alignment: str = Field(default="", max_length=100)
    age: str = Field(default="", max_length=50)
    height: str = Field(default="", max_length=50)
    weight: str = Field(default="", max_length=50)
    eyes: str = Field(default="", max_length=50)
    skin: str = Field(default="", max_length=50)
    hair: str = Field(default="", max_length=50)
    personality_traits: str = Field(default="", max_length=3000)
    ideals: str = Field(default="", max_length=3000)
    bonds: str = Field(default="", max_length=3000)
    flaws: str = Field(default="", max_length=3000)
    features: str = Field(default="", max_length=6000)
    backstory: str = Field(default="", max_length=10000)
    allies: str = Field(default="", max_length=3000)
    treasure: str = Field(default="", max_length=3000)


class Character(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    name: Name
    player_name: ShortText | None = None
    ruleset: Ruleset
    species: ShortText | None = None
    subrace: ShortText | None = None
    character_class: ShortText | None = None
    subclass: ShortText | None = None
    level: int = Field(default=1, ge=1, le=20)
    abilities: AbilityScores = Field(default_factory=AbilityScores)
    hit_points: HitPoints
    skills: SkillProficiencies = Field(default_factory=SkillProficiencies)
    profile: Profile = Field(default_factory=Profile)
    feats: list[ShortText] = Field(default_factory=list, max_length=40)
    hit_dice_used: int = Field(default=0, ge=0, le=20)
    resources_used: dict[ShortText, int] = Field(default_factory=dict)
    spells: SpellBook = Field(default_factory=SpellBook)
    inventory: list[Item] = Field(default_factory=list)
    attacks: list[Attack] = Field(default_factory=list)
    coins: Coins = Field(default_factory=Coins)
    portrait_id: UUID | None = None
    created_at: AwareDatetime = Field(default_factory=utcnow)
    updated_at: AwareDatetime = Field(default_factory=utcnow)

    @field_validator("resources_used")
    @classmethod
    def _valid_resources(cls, value: dict[str, int]) -> dict[str, int]:
        if len(value) > 30 or any(used < 0 or used > 1000 for used in value.values()):
            raise ValueError("Recursos de classe inválidos")
        return value

    @property
    def proficiency_bonus(self) -> int:
        return proficiency_bonus(self.level)


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def proficiency_bonus(level: int) -> int:
    return 2 + (level - 1) // 4
