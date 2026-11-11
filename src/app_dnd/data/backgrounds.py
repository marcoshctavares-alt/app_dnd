from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Background:
    name: str
    abilities: tuple[str, str, str]
    feat: str
    skills: tuple[str, str]
    tool: str
    equipment: str


BACKGROUNDS_2024: tuple[Background, ...] = (
    Background(
        "Acólito", ("intelligence", "wisdom", "charisma"), "Iniciado em Magia (Clérigo)",
        ("insight", "religion"), "Suprimentos de Calígrafo",
        "(A) Suprimentos de Calígrafo, Livro (orações), Símbolo Sagrado, Pergaminho (10 folhas), Robe, 8 PO; ou (B) 50 PO",
    ),
    Background(
        "Criminoso", ("dexterity", "constitution", "intelligence"), "Alerta",
        ("sleight-of-hand", "stealth"), "Ferramentas de Ladrão",
        "(A) 2 Adagas, Ferramentas de Ladrão, Pé de Cabra, 2 Bolsas, Roupas de Viajante, 16 PO; ou (B) 50 PO",
    ),
    Background(
        "Sábio", ("constitution", "intelligence", "wisdom"), "Iniciado em Magia (Mago)",
        ("arcana", "history"), "Suprimentos de Calígrafo",
        "(A) Bordão, Suprimentos de Calígrafo, Livro (história), Pergaminho (8 folhas), Robe, 8 PO; ou (B) 50 PO",
    ),
    Background(
        "Soldado", ("strength", "dexterity", "constitution"), "Atacante Selvagem",
        ("athletics", "intimidation"), "Jogo de azar (à escolha)",
        "(A) Lança, Arco Curto, 20 Flechas, Jogo de azar, Kit de Curandeiro, Aljava, Roupas de Viajante, 14 PO; ou (B) 50 PO",
    ),
)

BACKGROUND_NAMES = tuple(b.name for b in BACKGROUNDS_2024)


def find_background(name: str | None) -> Background | None:
    return next((b for b in BACKGROUNDS_2024 if b.name == name), None)
