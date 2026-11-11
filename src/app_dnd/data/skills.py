from __future__ import annotations

SKILLS: dict[str, tuple[str, str]] = {
    "acrobatics": ("Acrobacia", "dexterity"),
    "animal-handling": ("Lidar com Animais", "wisdom"),
    "arcana": ("Arcanismo", "intelligence"),
    "athletics": ("Atletismo", "strength"),
    "deception": ("Enganação", "charisma"),
    "history": ("História", "intelligence"),
    "insight": ("Intuição", "wisdom"),
    "intimidation": ("Intimidação", "charisma"),
    "investigation": ("Investigação", "intelligence"),
    "medicine": ("Medicina", "wisdom"),
    "nature": ("Natureza", "intelligence"),
    "perception": ("Percepção", "wisdom"),
    "performance": ("Atuação", "charisma"),
    "persuasion": ("Persuasão", "charisma"),
    "religion": ("Religião", "intelligence"),
    "sleight-of-hand": ("Prestidigitação", "dexterity"),
    "stealth": ("Furtividade", "dexterity"),
    "survival": ("Sobrevivência", "wisdom"),
}

CLASS_SAVES: dict[str, tuple[str, str]] = {
    "Bárbaro": ("strength", "constitution"),
    "Bardo": ("dexterity", "charisma"),
    "Clérigo": ("wisdom", "charisma"),
    "Druida": ("intelligence", "wisdom"),
    "Guerreiro": ("strength", "constitution"),
    "Monge": ("strength", "dexterity"),
    "Paladino": ("wisdom", "charisma"),
    "Patrulheiro": ("strength", "dexterity"),
    "Ladino": ("dexterity", "intelligence"),
    "Feiticeiro": ("constitution", "charisma"),
    "Bruxo": ("wisdom", "charisma"),
    "Mago": ("intelligence", "wisdom"),
}

CLASS_ARMOR: dict[str, str] = {
    "Bárbaro": "leves, médias, escudos",
    "Bardo": "leves",
    "Clérigo": "leves, médias, escudos",
    "Druida": "leves, médias, escudos (não metálicos)",
    "Guerreiro": "todas, escudos",
    "Monge": "nenhuma",
    "Paladino": "todas, escudos",
    "Patrulheiro": "leves, médias, escudos",
    "Ladino": "leves",
    "Feiticeiro": "nenhuma",
    "Bruxo": "leves",
    "Mago": "nenhuma",
}
