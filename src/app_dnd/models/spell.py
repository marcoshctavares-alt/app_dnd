from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

SpellId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class Spell(BaseModel):
    id: SpellId
    name: Text
    name_en: str | None = Field(default=None, max_length=100)
    level: int = Field(ge=0, le=9)
    school: Text
    classes: tuple[str, ...] = ()
    casting_time: LongText
    range: LongText
    components: LongText
    duration: LongText
    ritual: bool = False
    concentration: bool = False
    description: str | None = Field(default=None, max_length=20000)
    description_pt: str | None = Field(default=None, max_length=20000)
    source: Literal["srd", "custom"] = "custom"
