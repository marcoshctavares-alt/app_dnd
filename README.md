# APP_DND (Python)

App desktop de fichas de D&D 5e (Python + PySide6). O núcleo não depende da interface.

```
src/app_dnd/
├── ui/        # interface desktop (PySide6): lista de fichas, ficha, painel de dados
├── pdf/       # preenchimento da ficha oficial em PDF (mapa de campos + exportador)
├── services/  # regras sem Qt: dano/cura, testes, gerador, imagem, magias, equipamento/CA/ataques
├── data/      # dados do SRD: classes, raças/espécies e sub-raças, armas e armaduras, amostra de magias
├── models/    # Character (Pydantic): atributos, PV, modificadores, bônus de proficiência
├── dice/      # rolagem: 2d6+3, 4d6kh3, vantagem/desvantagem
├── storage/   # SQLite (fichas em JSON, imagens em BLOB)
└── backup/    # exportar/importar JSON validado (atômico)
tests/
```

## Rodar

```
python -m venv .venv
.venv\Scripts\activate        # Windows (Linux/Mac: source .venv/bin/activate)
pip install -e ".[dev,ui,pdf]"
pytest            # testa o núcleo (não abre janela)
python -m app_dnd # abre o app desktop
```

## Uso

```python
from app_dnd.dice import roll, roll_d20, Advantage
print(roll("4d6kh3"))
print(roll_d20(modifier=5, advantage=Advantage.ADVANTAGE))
```

Magias: o app traz as 339 magias do SRD 5.2.1 (regras de 2024) com o texto completo, traduzido para português (não oficial). O original em inglês
fica a um clique na janela de detalhes. Nível, escola, classes, tempo, alcance e duração também estão em português, e 31 magias têm nome em português. Para acrescentar magias suas, importe um
pacote JSON (aba Magias > Importar pacote…); veja `examples/pacote_magias_exemplo.json`.

Para regerar o catálogo a partir do texto do SRD: `python tools/import_srd_spells.py SRD.txt src/app_dnd/data/srd_spells.json`.

Conteúdo de regras (classes, raças, magias): usar apenas SRD 5.1/5.2 (CC-BY-4.0) ou conteúdo cadastrado pelo usuário.

## Exportar a ficha em PDF

Menu **Arquivo > Exportar ficha em PDF…**. O app preenche a ficha oficial de D&D 5e **que você fornece**
(PDF com campos de formulário, 6 páginas, versão 2014); ele guarda o caminho do arquivo para as próximas vezes.

- O PDF é da Wizards of the Coast ("Permission is granted to photocopy this document for personal use"):
  **não faz parte deste projeto e não deve ser redistribuído junto com o app.**
- O modelo costuma vir preenchido com um personagem de exemplo; o exportador apaga tudo e escreve só os dados da ficha.
- As páginas extras do modelo (continuação de características e cartas de magia) são removidas: saem 3 páginas.
- O retrato vai na página 2. Magias fora do catálogo ou além das linhas disponíveis geram um aviso.
- Perícias, salvaguardas e características de texto livre (traços, ideais, história) são editadas na aba Ficha.

Testes de preenchimento real: `APP_DND_TEMPLATE=caminho/ficha.pdf pytest` (sem a variável, esses testes são ignorados).

## Licenças

Copyright (C) 2026 Marcos Tavares.

O código do app está sob a **GPL-3.0 ou posterior** (arquivo `LICENSE`): uso e modificação livres, e versões distribuídas devem ficar abertas sob a mesma licença. A GPL não impede a venda; ela exige a entrega do código-fonte.

Este app inclui material do SRD 5.2.1 sob CC-BY-4.0. O texto de atribuição obrigatório está em `NOTICE.md` e no menu Ajuda > Licenças e créditos.

## Executável para testadores

**Gerar (precisa de Python 3.11+ e internet, na máquina de cada sistema):**
- Windows: dê dois cliques em `packaging\build.bat`
- macOS/Linux: `./packaging/build.sh`
- Ou, sem instalar nada: suba o projeto no GitHub e rode a ação **build-executaveis** (aba Actions); ela gera ZIPs para Windows, macOS e Linux.

O resultado fica em `dist/APP_DND/`. Compacte a pasta inteira em ZIP e envie; quem receber extrai e abre `APP_DND.exe` (ou `APP_DND`). Não precisa instalar Python.

**Avisos para quem testa:**
- O executável não é assinado: o Windows (SmartScreen) mostra "Mais informações → Executar assim mesmo"; no macOS, clique com o botão direito → Abrir.
- Para exportar PDF, cada pessoa precisa ter o PDF oficial da WotC (não é distribuído junto).
- `APP_DND --selftest` verifica dados e janela sem abrir a interface.
- Bibliotecas incluídas: PySide6 (LGPL), pydantic (MIT), pypdf (BSD), Pillow (HPND).

## Tema

Menu **Exibir → Tema**: Padrão do sistema, Claro ou Escuro. A escolha fica salva para a próxima abertura.

## Antecedentes (2024)

Na aba Ficha, **Aplicar antecedente (2024)…** oferece os 4 antecedentes do SRD 5.2.1 (Acólito, Criminoso, Sábio, Soldado): aplica +2/+1 ou +1/+1/+1 nos atributos, as duas perícias e anota talento e ferramenta nos Traços. Fichas aleatórias de 2024 já vêm com um antecedente.

## Talentos (2024)

Aba **Talentos**: catálogo dos 19 talentos do SRD 5.2.1 (Origem, Geral, Estilo de Luta e Dádivas Épicas) com checagem de pré-requisitos (nível, atributo, Estilo de Luta, Conjuração). O talento do antecedente entra automaticamente. Talentos com aumento de atributo (Aumento de Atributo, Agarrador, Dádivas) aplicam o aumento ao serem adicionados, respeitando o limite (20, ou 30 nas Dádivas); remover o talento não desfaz o aumento. Os textos são resumos não oficiais em português.

## Subclasses (2024)

Aba **Características**: lista, por nível, as características de classe (nomes e resumos em português, a partir do SRD 5.2.1) e as de subclasse (com resumo), com as ainda não liberadas marcadas como bloqueadas. O PDF lista as liberadas. As características de classe têm um resumo em português (não oficial) e podem omitir detalhes; confira o SRD ou o livro para o texto completo. O SRD traz só uma subclasse por classe; outras subclasses exigiriam conteúdo de outros livros. Os textos são resumos não oficiais em português (`tools/import_srd_subclass_features.py` extrai o texto em inglês do SRD para conferência).

## Descansos e recursos de classe (2024)

Aba **Descanso**: Dados de Vida (gastar para curar), descanso curto e longo, e contadores de usos por classe (Fúrias, Inspiração de Bardo, Canalizar Divindade, Forma Selvagem, Retomar o Fôlego, Surto de Ação, Indomável, Pontos de Foco, Mãos Consagradas, Inimigo Favorito, Pontos de Feitiçaria, Feitiçaria Inata, Astúcia Mágica, Recuperação Arcana). O descanso longo restaura PV, metade dos Dados de Vida (mínimo 1), espaços de magia e todos os recursos; o curto recupera cada recurso conforme a regra dele. Os botões de descanso da aba Magias fazem o mesmo. O PDF lista os usos restantes dos recursos em Características e Traços. Pontos de Feitiçaria e Inspiração de Bardo só voltam por descanso; conversões e recuperações parciais (como Restauração Feiticeira) são manuais.

### Executável único (Windows)

`packaging\build_onefile.bat` gera `dist\FichasDnD.exe` (arquivo único, sem console, com ícone) usando `requirements-build.txt`; o mesmo build roda na ação **build-executaveis** (job `windows-onefile`). O arquivo único é mais lento para abrir (extrai para uma pasta temporária a cada execução) e mais propenso a falso positivo de antivírus que a versão em pasta (`build.bat`). O ícone vem de `tools/make_icon.py`.
