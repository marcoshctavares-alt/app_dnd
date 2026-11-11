from app_dnd.data.srd import CLASS_BY_NAME


def test_subclass_names_and_levels_by_ruleset():
    sorcerer, wizard, fighter = CLASS_BY_NAME["Feiticeiro"], CLASS_BY_NAME["Mago"], CLASS_BY_NAME["Guerreiro"]
    assert sorcerer.subclass_for("dnd-5e-2014") == ("Linhagem Dracônica", 1)
    assert sorcerer.subclass_for("dnd-5e-2024") == ("Feitiçaria Dracônica", 3)
    assert wizard.subclass_for("dnd-5e-2014") == ("Escola de Evocação", 2)
    assert wizard.subclass_for("dnd-5e-2024") == ("Evocador", 3)
    assert fighter.subclass_for("dnd-5e-2014") == ("Campeão", 3)
    assert fighter.subclass_for("dnd-5e-2024") == ("Campeão", 3)
