from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Subrace:
    name: str
    bonuses: dict[str, int] = field(default_factory=dict)
    speed: int | None = None
    traits: tuple[str, ...] = ()


@dataclass(frozen=True)
class Race:
    name: str
    size: str
    speed: int
    bonuses: dict[str, int] = field(default_factory=dict)
    free_choices: int = 0
    free_choice_excludes: tuple[str, ...] = ()
    subraces: tuple[Subrace, ...] = ()
    traits: tuple[str, ...] = ()
    lineage_label: str = "Sub-raça"

    def subrace(self, name: str) -> Subrace:
        for sub in self.subraces:
            if sub.name == name:
                return sub
        raise ValueError(f"{name!r} não é sub-raça de {self.name}")


RACES_2014: tuple[Race, ...] = (
    Race("Anão", "Médio", 25, {"constitution": 2}, subraces=(Subrace("Anão da Colina", {"wisdom": 1}),)),
    Race("Elfo", "Médio", 30, {"dexterity": 2}, subraces=(Subrace("Elfo Alto", {"intelligence": 1}),)),
    Race("Halfling", "Pequeno", 25, {"dexterity": 2}, subraces=(Subrace("Pés-Leves", {"charisma": 1}),)),
    Race(
        "Humano",
        "Médio",
        30,
        {a: 1 for a in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")},
    ),
    Race("Draconato", "Médio", 30, {"strength": 2, "charisma": 1}),
    Race("Gnomo", "Pequeno", 25, {"intelligence": 2}, subraces=(Subrace("Gnomo das Rochas", {"constitution": 1}),)),
    Race("Meio-elfo", "Médio", 30, {"charisma": 2}, free_choices=2, free_choice_excludes=("charisma",)),
    Race("Meio-orc", "Médio", 30, {"strength": 2, "constitution": 1}),
    Race("Tiefling", "Médio", 30, {"charisma": 2, "intelligence": 1}),
)

_DRAGONS = (
    ("Negro", "Ácido"), ("Azul", "Elétrico"), ("Latão", "Fogo"), ("Bronze", "Elétrico"), ("Cobre", "Ácido"),
    ("Ouro", "Fogo"), ("Verde", "Venenoso"), ("Vermelho", "Fogo"), ("Prata", "Frio"), ("Branco", "Frio"),
)
_GIANTS = (
    ("Gigante das Nuvens", "Salto da Nuvem: ação bônus, teletransporta até 9 m para um espaço desocupado visível."),
    ("Gigante de Fogo", "Queimadura do Fogo: ao acertar um ataque, causa 1d10 de dano de Fogo extra."),
    ("Gigante do Gelo", "Frio do Gelo: ao acertar um ataque, causa 1d6 de dano de Frio extra e reduz o deslocamento do alvo em 3 m até o início do seu próximo turno."),
    ("Gigante da Colina", "Tombo da Colina: ao acertar uma criatura Grande ou menor, pode deixá-la Caída."),
    ("Gigante de Pedra", "Resistência da Pedra: ao sofrer dano, usa reação para reduzir o dano em 1d12 + modificador de Constituição."),
    ("Gigante da Tempestade", "Trovão da Tempestade: ao sofrer dano de criatura a até 18 m, usa reação para causar 1d8 de dano Trovejante nela."),
)
_USES = "Usos igual ao bônus de proficiência, recuperados em descanso longo."
_LEGACY_NOTE = "Níveis 3 e 5: aprende magia de nível superior, sempre preparada, conjurável uma vez sem espaço por descanso longo. Atributo de conjuração: Inteligência, Sabedoria ou Carisma."

SPECIES_2024: tuple[Race, ...] = (
    Race(
        "Draconato", "Médio", 30,
        subraces=tuple(
            Subrace(
                f"Dragão {color}",
                traits=(f"Sopro e Resistência a dano {dmg}.",),
            )
            for color, dmg in _DRAGONS
        ),
        lineage_label="Ancestralidade dracônica",
        traits=(
            "Sopro: no lugar de um ataque, cone de 4,5 m ou linha de 9 m × 1,5 m; salvaguarda de Destreza (CD 8 + Constituição + proficiência); 1d10 de dano (2d10 no nível 5, 3d10 no 11, 4d10 no 17), metade se passar. " + _USES,
            "Resistência a Dano: ao tipo de dano da ancestralidade.",
            "Visão no Escuro: 18 m.",
            "Voo Dracônico (nível 5): ação bônus, asas por 10 minutos, deslocamento de voo igual ao deslocamento; uma vez por descanso longo.",
        ),
    ),
    Race(
        "Anão", "Médio", 30,
        traits=(
            "Visão no Escuro: 36 m.",
            "Resiliência Anã: resistência a dano Venenoso e vantagem em salvaguardas contra a condição Envenenado.",
            "Robustez Anã: +1 PV máximo e +1 a cada nível.",
            "Tino para Pedra: ação bônus para ganhar Sentido Sísmico de 18 m por 10 minutos, sobre ou tocando pedra. " + _USES,
        ),
    ),
    Race(
        "Elfo", "Médio", 30,
        subraces=(
            Subrace("Drow", traits=("Visão no Escuro aumenta para 36 m; conhece o truque Luzes Dançantes.", "Nível 3: Fogo das Fadas. Nível 5: Escuridão.")),
            Subrace("Alto Elfo", traits=("Conhece o truque Prestidigitação, trocável por outro truque de Mago após descanso longo.", "Nível 3: Detectar Magia. Nível 5: Passo Nebuloso.")),
            Subrace("Elfo da Floresta", speed=35, traits=("Deslocamento 10,5 m; conhece o truque Druidcraft.", "Nível 3: Passos Largos. Nível 5: Passar sem Rastro.")),
        ),
        lineage_label="Linhagem élfica",
        traits=(
            "Visão no Escuro: 18 m.",
            "Ancestralidade Feérica: vantagem em salvaguardas contra a condição Enfeitiçado.",
            "Sentidos Aguçados: proficiência em Intuição, Percepção ou Sobrevivência.",
            "Transe: não precisa dormir; descanso longo em 4 horas.",
            _LEGACY_NOTE,
        ),
    ),
    Race(
        "Gnomo", "Pequeno", 30,
        subraces=(
            Subrace("Gnomo da Floresta", traits=("Conhece Ilusão Menor; Falar com Animais sempre preparada, conjurável sem espaço " + _USES.lower(),)),
            Subrace("Gnomo das Rochas", traits=("Conhece Reparar e Prestidigitação; pode criar um mecanismo Miúdo (CA 5, 1 PV) em 10 minutos, até 3 ao mesmo tempo.",)),
        ),
        lineage_label="Linhagem gnômica",
        traits=(
            "Visão no Escuro: 18 m.",
            "Astúcia Gnômica: vantagem em salvaguardas de Inteligência, Sabedoria e Carisma.",
            "Atributo de conjuração da linhagem: Inteligência, Sabedoria ou Carisma.",
        ),
    ),
    Race(
        "Golias", "Médio", 35,
        subraces=tuple(Subrace(name, traits=(text,)) for name, text in _GIANTS),
        lineage_label="Ancestralidade gigante",
        traits=(
            "Ancestralidade Gigante: um benefício à escolha. " + _USES,
            "Forma Grande (nível 5): ação bônus para ficar Grande por 10 minutos, vantagem em testes de Força e +3 m de deslocamento; uma vez por descanso longo.",
            "Constituição Poderosa: vantagem em testes para encerrar Agarrado e conta como um tamanho maior para capacidade de carga.",
        ),
    ),
    Race(
        "Halfling", "Pequeno", 30,
        traits=(
            "Corajoso: vantagem em salvaguardas contra a condição Amedrontado.",
            "Agilidade Halfling: pode atravessar o espaço de criaturas de tamanho maior.",
            "Sorte: ao tirar 1 em um d20 de Teste de D20, pode rolar de novo e usar o novo resultado.",
            "Furtividade Natural: pode se Esconder atrás de criatura pelo menos um tamanho maior.",
        ),
    ),
    Race(
        "Humano", "Médio", 30,
        traits=(
            "Engenhoso: ganha Inspiração Heroica ao terminar um descanso longo.",
            "Habilidoso: proficiência em uma perícia à escolha.",
            "Versátil: um talento de Origem à escolha (Habilidoso é recomendado).",
            "Tamanho Médio ou Pequeno, à escolha.",
        ),
    ),
    Race(
        "Orc", "Médio", 30,
        traits=(
            "Surto de Adrenalina: Correr como ação bônus e ganha PV temporários iguais ao bônus de proficiência. Usos igual ao bônus de proficiência, recuperados em descanso curto ou longo.",
            "Visão no Escuro: 36 m.",
            "Resistência Implacável: ao cair a 0 PV sem morrer, fica com 1 PV; uma vez por descanso longo.",
        ),
    ),
    Race(
        "Tiefling", "Médio", 30,
        subraces=(
            Subrace("Abissal", traits=("Resistência a dano Venenoso; conhece Rajada de Veneno.", "Nível 3: Raio do Enfermiço. Nível 5: Imobilizar Pessoa.")),
            Subrace("Ctônico", traits=("Resistência a dano Necrótico; conhece Toque Necrótico.", "Nível 3: Vitalidade Falsa. Nível 5: Raio do Enfraquecimento.")),
            Subrace("Infernal", traits=("Resistência a dano de Fogo; conhece Raio de Fogo.", "Nível 3: Repreensão Infernal. Nível 5: Escuridão.")),
        ),
        lineage_label="Legado ínfero",
        traits=(
            "Visão no Escuro: 18 m.",
            "Presença Sobrenatural: conhece o truque Taumaturgia.",
            _LEGACY_NOTE,
            "Tamanho Médio ou Pequeno, à escolha.",
        ),
    ),
)


def races_for(ruleset: str) -> tuple[Race, ...]:
    return RACES_2014 if ruleset == "dnd-5e-2014" else SPECIES_2024


def find_race(ruleset: str, name: str | None) -> Race | None:
    if not name:
        return None
    return next((r for r in races_for(ruleset) if r.name == name), None)


def lineage_label(ruleset: str, name: str | None) -> str:
    race = find_race(ruleset, name)
    return race.lineage_label if race and race.subraces else "Sub-raça"
