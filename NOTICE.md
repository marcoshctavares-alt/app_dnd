# Créditos e licenças

## SRD 5.2.1

This work includes material from the System Reference Document 5.2.1 (“SRD 5.2.1”) by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative Commons Attribution 4.0 International License, available at https://creativecommons.org/licenses/by/4.0/legalcode.

Alterações: os campos mecânicos das magias (nível, escola, classes, tempo de conjuração, alcance, duração) foram convertidos para português e 31 magias receberam nome em português. Os componentes materiais permanecem em inglês. As descrições têm tradução para português em `src/app_dnd/data/srd_spells_pt.json`, feita para este projeto a partir do texto do SRD 5.2.1; o texto original em inglês continua em `srd_spells.json` e pode ser exibido na janela de detalhes. A tradução não é oficial e pode conter imprecisões. Os dados vêm de `src/app_dnd/data/srd_spells.json`, gerado por `tools/import_srd_spells.py`.

## Ficha em PDF

A ficha oficial em PDF usada na exportação é da Wizards of the Coast e **não** está incluída neste projeto (uso pessoal; o usuário informa o próprio arquivo).

A tabela de truques conhecidos, magias preparadas e espaços de magia por nível das oito classes conjuradoras (regras 2024) vem das tabelas de classe do SRD 5.2.1 e está em `src/app_dnd/data/spellcasting_2024.json`, gerada por `tools/import_srd_spellcasting.py`. Os nomes das classes foram traduzidos para português; os números não foram alterados.

As espécies e linhagens de 2024 (deslocamento, características, ancestralidades do Draconato, Golias, Elfo, Gnomo e Tiefling) foram resumidas e traduzidas para português a partir das “Species Descriptions” do SRD 5.2.1, em `src/app_dnd/data/races.py`. Os resumos não substituem o texto original.

Os antecedentes (`data/backgrounds.py`), talentos (`data/feats.py`) e características de subclasse (`data/subclass_features_2024.json`) de 2024 foram resumidos e traduzidos para português a partir do SRD 5.2.1. Os resumos não são oficiais, não substituem o texto original e podem conter imprecisões.

Os usos de recursos de classe (`data/class_resources.py`) foram transcritos das tabelas de características de classe do SRD 5.2.1.

Os nomes das características de classe (`data/class_features_2024.json`) vêm das tabelas do SRD 5.2.1, traduzidos para este projeto; a tradução não é oficial. `tools/import_srd_class_features.py` extrai os títulos do SRD.

Os resumos das características de classe em `class_features_2024.json` foram escritos para este projeto a partir do SRD 5.2.1; são simplificações não oficiais.

## Licença do programa

Copyright (C) 2026 Marcos Tavares.

O código-fonte do APP_DND é distribuído sob a GNU General Public License, versão 3 ou posterior (arquivo `LICENSE`). A GPL permite usar, modificar e redistribuir, inclusive com cobrança, desde que as versões distribuídas mantenham a mesma licença e entreguem o código-fonte; ela não permite proibir a venda.

Os arquivos de dados derivados do SRD 5.2.1 (`src/app_dnd/data/*.json` e as tabelas em `data/*.py` transcritas do SRD) continuam sob a CC BY 4.0, com a atribuição acima, e os resumos e traduções neles contidos não são oficiais.

Bibliotecas de terceiros usadas: PySide6/Qt (LGPL-3.0), pydantic (MIT), pypdf (BSD-3-Clause) e Pillow (MIT-CMU/HPND). Elas mantêm as próprias licenças.
