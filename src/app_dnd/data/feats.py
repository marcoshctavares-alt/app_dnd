from __future__ import annotations

from dataclasses import dataclass

ORIGIN, GENERAL, FIGHTING_STYLE, EPIC_BOON = "Origem", "Geral", "Estilo de Luta", "Dádiva Épica"
CATEGORIES = (ORIGIN, GENERAL, FIGHTING_STYLE, EPIC_BOON)

NEEDS_FIGHTING_STYLE = "fighting_style"
NEEDS_SPELLCASTING = "spellcasting"
FIGHTING_STYLE_CLASSES = {"Guerreiro": 1, "Paladino": 2, "Patrulheiro": 2}


@dataclass(frozen=True)
class Feat:
    name: str
    category: str
    description: str
    min_level: int = 1
    abilities_any: tuple[str, ...] = ()
    ability_min: int = 0
    needs: str | None = None
    repeatable: bool = False
    asi: tuple[str, ...] = ()
    asi_shapes: tuple[tuple[int, ...], ...] = ()
    asi_cap: int = 20


def _magic_initiate(list_name: str, spells: str) -> Feat:
    return Feat(
        f"Iniciado em Magia ({list_name})", ORIGIN,
        f"Você aprende dois truques e uma magia de nível 1 da lista de {spells}. A magia de nível 1 fica sempre "
        "preparada e pode ser conjurada uma vez por Descanso Longo sem gastar espaço. Atributo de conjuração à "
        "escolha: Inteligência, Sabedoria ou Carisma. Ao subir de nível, pode trocar uma dessas magias.",
    )


ALL_ABILITIES = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")
_BOON = {"asi": ALL_ABILITIES, "asi_shapes": ((1,),), "asi_cap": 30}
_BOON_ASI = "Aumente um atributo à escolha em 1 (máximo 30). "

FEATS_2024: tuple[Feat, ...] = (
    Feat("Alerta", ORIGIN,
         "Soma seu Bônus de Proficiência à Iniciativa. Logo após rolar Iniciativa, pode trocá-la com a de um aliado "
         "disposto no mesmo combate (nenhum dos dois pode estar Incapacitado)."),
    _magic_initiate("Clérigo", "Clérigo"),
    _magic_initiate("Druida", "Druida"),
    _magic_initiate("Mago", "Mago"),
    Feat("Atacante Selvagem", ORIGIN,
         "Uma vez por turno, ao acertar um alvo com uma arma, role os dados de dano da arma duas vezes e use "
         "qualquer um dos resultados."),
    Feat("Habilidoso", ORIGIN,
         "Você ganha proficiência em três perícias ou ferramentas à sua escolha.", repeatable=True),
    Feat("Aumento de Atributo", GENERAL,
         "Aumente um atributo em 2 ou dois atributos em 1 (máximo 20).", min_level=4, repeatable=True,
         asi=ALL_ABILITIES, asi_shapes=((2,), (1, 1))),
    Feat("Agarrador", GENERAL,
         "Aumente Força ou Destreza em 1 (máximo 20). Ao acertar um Ataque Desarmado como parte da ação Atacar, pode "
         "causar dano e Agarrar no mesmo golpe (uma vez por turno). Vantagem em ataques contra criaturas que você "
         "agarra. Mover uma criatura agarrada do seu tamanho ou menor não custa movimento extra.",
         min_level=4, abilities_any=("strength", "dexterity"), ability_min=13,
         asi=("strength", "dexterity"), asi_shapes=((1,),)),
    Feat("Arquearia", FIGHTING_STYLE, "Bônus de +2 nas jogadas de ataque com armas à Distância.",
         needs=NEEDS_FIGHTING_STYLE),
    Feat("Defesa", FIGHTING_STYLE, "Usando armadura Leve, Média ou Pesada, você ganha +1 de CA.",
         needs=NEEDS_FIGHTING_STYLE),
    Feat("Combate com Armas Grandes", FIGHTING_STYLE,
         "Ao rolar dano com uma arma Corpo a Corpo empunhada com as duas mãos, trate 1 ou 2 nos dados como 3. A arma "
         "precisa ter a propriedade Duas Mãos ou Versátil.", needs=NEEDS_FIGHTING_STYLE),
    Feat("Combate com Duas Armas", FIGHTING_STYLE,
         "Ao fazer o ataque extra com uma arma Leve, você soma seu modificador de atributo ao dano desse ataque, se "
         "ainda não o somar.", needs=NEEDS_FIGHTING_STYLE),
    Feat("Dádiva de Prontidão em Combate", EPIC_BOON,
         _BOON_ASI + "Mira Inigualável: ao errar uma jogada de ataque, você pode acertar em vez disso (uma vez até o "
         "início do seu próximo turno).", min_level=19, **_BOON),
    Feat("Dádiva de Viagem Dimensional", EPIC_BOON,
         _BOON_ASI + "Logo após usar a ação Atacar ou Magia, teletransporte-se até 9 m para um espaço desocupado "
         "que você veja.", min_level=19, **_BOON),
    Feat("Dádiva do Destino", EPIC_BOON,
         _BOON_ASI + "Quando você ou outra criatura a até 18 m passar ou falhar num Teste de d20, role 2d4 e aplique "
         "o total como bônus ou penalidade. Recarrega ao rolar Iniciativa ou em Descanso Curto/Longo.", min_level=19,
         **_BOON),
    Feat("Dádiva de Ofensiva Irresistível", EPIC_BOON,
         "Aumente Força ou Destreza em 1 (máximo 30). Seu dano Contundente, Perfurante e Cortante ignora Resistência. "
         "Ao tirar 20 no d20 de um ataque, causa dano extra igual ao atributo aumentado por esta dádiva.",
         min_level=19, asi=("strength", "dexterity"), asi_shapes=((1,),), asi_cap=30),
    Feat("Dádiva de Recordação de Magias", EPIC_BOON,
         "Aumente Inteligência, Sabedoria ou Carisma em 1 (máximo 30). Ao conjurar com espaço de nível 1–4, role 1d4: "
         "se for igual ao nível do espaço, ele não é gasto.", min_level=19, needs=NEEDS_SPELLCASTING,
         asi=("intelligence", "wisdom", "charisma"), asi_shapes=((1,),), asi_cap=30),
    Feat("Dádiva do Espírito da Noite", EPIC_BOON,
         _BOON_ASI + "Em Penumbra ou Escuridão, fique Invisível com uma Ação Bônus (termina ao agir) e tenha "
         "Resistência a todo dano exceto Psíquico e Radiante.", min_level=19, **_BOON),
    Feat("Dádiva da Visão Verdadeira", EPIC_BOON,
         _BOON_ASI + "Você tem Visão Verdadeira com alcance de 18 m.", min_level=19, **_BOON),
)

FEAT_BY_NAME = {f.name: f for f in FEATS_2024}


def find_feat(name: str | None) -> Feat | None:
    return FEAT_BY_NAME.get(name or "")
