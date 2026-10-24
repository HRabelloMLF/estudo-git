---
name: tmdl
description: "Use esta skill sempre que for preciso ler, criar ou alterar objetos do modelo semântico Power BI em arquivos TMDL (pasta .SemanticModel/definition), incluindo tabelas, colunas, medidas, relacionamentos, partições, expressões M, roles (RLS), calculation groups, perspectivas, traduções, hierarquias, descrições, display folders, DAX UDFs e Direct Lake. Gatilhos: \"edita o TMDL\", \"cria a tabela no modelo\", \"adiciona a coluna\", \"marca a tabela de datas\", \"calculation group\", \"role de RLS\", \"model.tmdl\", \"database.tmdl\"."
metadata:
  version: '2026-09-03'
  last_reviewed: '2026-09-03'
  sources:
  - "Microsoft Learn: Tabular Model Definition Language"
  - "Microsoft Learn: TMDL View in Power BI Desktop"
  - "Microsoft Learn: Power BI Desktop project semantic model folder"
  - "Microsoft skills-for-fabric: semantic-model-authoring (tmdl-guidelines, direct-lake-guidelines)"
---

# Skill: TMDL para Power BI PBIP/PBIR

> **Leitura progressiva:** este arquivo traz só o essencial (segurança, estrutura, sintaxe de alta
> frequência). O conteúdo aprofundado fica em `references/` — carregue **somente** o arquivo
> relevante à tarefa em mãos:
>
> | Arquivo | Quando ler |
> |---|---|
> | `references/boas-praticas-modelo.md` | Nomenclatura (tabelas/colunas/medidas), boas práticas de medidas DAX, relacionamentos, descrições `///`, display folders |
> | `references/edicao-avancada.md` | `unappliedChanges.json`, renomear/excluir com rastreio de dependências, partições M, propriedades a preservar, impacto em PBIR, scripts TMDL |
> | `references/objetos-avancados.md` | Hierarquias, calculation groups, roles (RLS), traduções, perspectivas, objetos `calendar`, parâmetros do Power Query, DAX UDFs, Direct Lake |
> | `references/fluxo-de-trabalho.md` | Fluxo diagnóstico → validação, templates de diagnóstico e validação, checklist de revisão, critérios de qualidade |

Exemplos no modelo do curso, Aurora Varejo (`VendasAurora`: `ft_vendas`, `ft_metas`, `dim_cliente`,
`dim_produto`, `dim_vendedor`, `dim_calendario`, tabela `Medidas`).

## 1. Objetivo e quando usar

TMDL (Tabular Model Definition Language) é a representação textual do modelo tabular — otimizada
para leitura humana, versionamento e edição como código, com hierarquia por indentação (**TAB**).

Use esta skill sempre que for ler ou modificar qualquer item dentro de:

```text
<Projeto>.SemanticModel/definition/
├── database.tmdl        model.tmdl        relationships.tmdl
├── expressions.tmdl     functions.tmdl (opcional)
├── tables/*.tmdl        roles/            perspectives/        cultures/
└── TMDLScripts/ (scripts createOrReplace, fora de definition/)
```

## 2. Ferramentas

| Tarefa | Como |
|---|---|
| Validar a sintaxe | Abrir o PBIP no Power BI Desktop: `powerbi-desktop open <arquivo.pbip>` e `powerbi-desktop status`. Erro de parse aparece na abertura, com arquivo e linha. |
| Recarregar após editar TMDL | Reabrir o PBIP. O `powerbi-desktop reload` cobre só o relatório (PBIR); alteração no modelo exige reabertura. |
| Consultar o modelo | `pbi connect` (pbi-cli) no Desktop aberto e `pbi dax execute --file consulta.dax` (`EVALUATE INFO.VIEW.TABLES()`, `INFO.VIEW.MEASURES()`, `INFO.VIEW.RELATIONSHIPS()`), ou o MCP `powerbi-modeling-mcp`. |
| Editar com o MCP conectado | O modelo em memória é a fonte de verdade durante a sessão; o `.tmdl` em disco fica defasado. Ao terminar, salve no Desktop para serializar de volta em `definition/`. |

## 3. Regra central de segurança

Ninguém modifica TMDL sem executar este ciclo:

```text
1. Diagnosticar
2. Mapear dependências
3. Propor plano de alteração
4. Alterar o menor escopo possível
5. Validar impacto (abrir no Desktop, executar as medidas)
6. Atualizar documentação
7. Registrar a mudança (changelog ou README do modelo)
```

Antes de qualquer alteração, responder:

```text
- Qual objeto será alterado?
- Por que será alterado?
- Quais objetos dependem dele?
- Existe impacto em medidas, relacionamentos, visuais PBIR ou Power Query?
- A alteração exige aprovação de quem pediu?
```

## 4. Estrutura típica em PBIP

```text
Projeto.SemanticModel/
├── .platform                   # metadados do item (Fabric/Git) — não editar
├── definition.pbism            # obrigatório
├── .pbi/                       # localSettings.json e cache.abf não versionar;
│                               # unappliedChanges.json = alterações PQ pendentes (ver referência)
├── definition/
│   ├── database.tmdl           # obrigatório: declaração `database` + `compatibilityLevel` (§ 6.0)
│   ├── model.tmdl
│   ├── expressions.tmdl
│   ├── relationships.tmdl
│   ├── functions.tmdl          # DAX UDFs — opcional (exige compatibilityLevel 1702)
│   ├── tables/                 # ft_vendas.tmdl, dim_cliente.tmdl, dim_calendario.tmdl, Medidas.tmdl
│   ├── roles/  perspectives/  cultures/
└── TMDLScripts/
```

## 5. Regras mínimas de edição (valem sempre)

- **`unappliedChanges.json` existe?** Avisar o usuário e não alterar M sem confirmação
  (detalhes em `references/edicao-avancada.md` § 1).
- **Preservar indentação** com TAB (não misturar tabs e espaços no mesmo bloco); alterar apenas os
  blocos necessários; nunca reformatar o arquivo inteiro.
- **Nunca renomear ou excluir** sem buscar dependências no projeto inteiro (TMDL + PBIR + DAX +
  roles) — checklists em `references/edicao-avancada.md` §§ 2–3. Em dúvida, `isHidden: true` em vez
  de excluir.
- **Preservar propriedades existentes** (`lineageTag`, `sourceColumn`, `summarizeBy`,
  `formatString`, `sortByColumn`, `annotations`, …). Propriedade desconhecida = preservar.
- **Omitir `lineageTag` em objetos novos** — o Desktop gera no primeiro save.
- **Descrição com `///`** na linha acima do objeto — nunca `description:` como propriedade; TMDL
  não tem comentários `//` nem `/* */`.
- **Ordem dentro da tabela:** medidas antes de colunas; depois hierarquias e partições.
- **Não autorar anotações `PBI_*`** nem `dataType` em medidas (o engine infere).
- **Relacionamentos:** `fromColumn` = lado muitos (fato), `toColumn` = lado um (dimensão);
  `isActive: false` quando inativo.
- **Menor escopo possível** — relatar "alterei apenas: <arquivo>: <bloco>".
- Chaves de relacionamento: `pk_` no lado 1 (`toColumn`) e `fk_` no lado muitos (`fromColumn`), mesmo
  sufixo; toda `fk_` com `isHidden`.
- Nomenclatura (convenção do curso): tabelas em snake_case com prefixo (`ft_vendas`, `dim_cliente`,
  `aux_`, `rls_`, `pc_`, `gc_`), colunas em snake_case com prefixo de natureza (`vl_liquido`,
  `dt_emissao`), medidas com espaço, variáveis DAX `__` — tabela completa em
  `references/boas-praticas-modelo.md` § 1.

## 6. Sintaxe de alta frequência

### 6.0 Arquivos de raiz (`database.tmdl` e `model.tmdl`)

`database.tmdl` mínimo, exatamente como o Desktop grava. A declaração `database` (sem nome) é
obrigatória — `compatibilityLevel:` solto no arquivo gera `InvalidLineType: Property!`:

```tmdl
database
	compatibilityLevel: 1600
```

- `1600` é o que o Desktop grava por padrão (projetos mais recentes podem vir com `1606`). `1702` só é
  necessário para DAX UDFs (`functions.tmdl`) ou objetos `calendar`. Copie o valor do Desktop; não
  invente.

`model.tmdl` mínimo (modelo Import):

```tmdl
model Model
	culture: pt-BR
	defaultPowerBIDataSourceVersion: powerBI_V3
	sourceQueryCulture: pt-BR

ref table ft_vendas
ref table dim_calendario
ref table Medidas
```

- `defaultPowerBIDataSourceVersion: powerBI_V3` é obrigatório em modelos Import.
- Cada tabela em `tables/` tem sua linha `ref table <Nome>` (idem `ref role`, `ref perspective`,
  `ref cultureInfo`); ao criar uma tabela nova, adicione o `ref` correspondente.
- O Desktop acrescenta outras linhas (`dataAccessOptions`, `annotation PBI_QueryOrder`,
  `annotation __PBI_TimeIntelligenceEnabled`, …) — preservar quando existirem.

### 6.1 Medida (convenção do curso: sempre na tabela dedicada `Medidas`)

````tmdl
/// Receita líquida total considerando devoluções e descontos comerciais.
measure 'Receita Líquida' = ```
		SUMX ( ft_vendas, ft_vendas[vl_bruto] - ft_vendas[vl_desconto] )
		```
	formatString: R$ #,0.00
	displayFolder: 01. Vendas
````

- DAX multi-linha vai entre triple backticks (abertura na mesma linha do `=`, fechamento em linha
  própria); as propriedades (`formatString:`, `displayFolder:`) ficam **um** nível de indentação
  abaixo de `measure` — nunca no mesmo nível da expressão. O Desktop também aceita a forma sem
  backticks, com a expressão um nível **mais fundo** que as propriedades.
- `formatString` e `displayFolder` **sem aspas externas** (`R$ #,0.00`, `0.0%`, `#,0`,
  `01. Vendas`): as aspas viram parte do valor. Em format string, aspas delimitam texto literal —
  quando há literal, elas envolvem só o literal: `"R$"\ #,0.00;-"R$"\ #,0.00;"R$"\ #,0.00`.
- Medidas base antes de derivadas; `DIVIDE()` fora de iteradores; descrição `///` nas medidas
  relevantes. Sintaxe da tabela `Medidas` (tabela calculada vazia): skill `dax` § "Tabela dedicada
  de medidas".

### 6.2 Tabela de datas — marcação obrigatória

Toda tabela calendário (`dim_calendario`) deve ser **marcada como tabela de datas** imediatamente
após a criação. Se o modelo já vier com uma tabela calendário, **verificar** se está marcada e
marcar caso não esteja — nunca deixar um calendário sem marcação.

```tmdl
table dim_calendario
	dataCategory: Time

	column pk_data
		isKey
		dataType: dateTime
		formatString: Short Date
		summarizeBy: none
		sourceColumn: pk_data

	column nu_ano
		dataType: int64
		summarizeBy: none
		sourceColumn: nu_ano

	column nm_mes
		dataType: string
		sortByColumn: nu_mes
		summarizeBy: none
		sourceColumn: nm_mes
```

- `dataCategory: Time` na declaração da `table` (linha própria, indentada por tab, tipicamente
  após `lineageTag` quando ele existir).
- `isKey` na coluna de data, como primeira propriedade da coluna.
- Pré-requisito de runtime: a coluna de data deve ser única e contígua (sem lacunas) — o Desktop
  valida no refresh; se o intervalo tiver buracos, a marcação falha.
- A marcação é o que habilita `TOTALYTD`, `DATEADD`, `DATESINPERIOD` etc. sem depender do auto
  date/time do Desktop.
- Colunas de **tabela calculada** usam `sourceColumn: [Nome]` com colchetes (+ `isNameInferred`
  quando o nome TMDL é idêntico ao do DAX).

### 6.3 Partição com expressão M

```tmdl
partition ft_vendas = m
	mode: import
	source =
		let
			Fonte = Excel.Workbook ( File.Contents ( path_pasta_dados & "VendasAurora.xlsx" ), null, true ),
			tbVendas = Fonte{[Item = "tbVendas", Kind = "Table"]}[Data]
		in
			tbVendas
```

- Não alterar M sem usar também a skill `power-query-m`; regras completas em
  `references/edicao-avancada.md` § 4.
- Direct Lake usa `partition X = entity` / `mode: directLake`, sem M — sintaxe em
  `references/objetos-avancados.md` § 9.

### 6.4 Demais objetos

Hierarquias, calculation groups, roles (RLS), traduções, perspectivas, objetos `calendar`,
parâmetros do Power Query, DAX UDFs e Direct Lake têm exemplo mínimo em
`references/objetos-avancados.md`. Scripts TMDL só suportam `createOrReplace`
(`references/edicao-avancada.md` § 7).

## 7. Regra final

TMDL é **código-fonte crítico do modelo semântico**:

```text
Não edite como texto solto.
Edite como contrato de dados, regra de negócio e camada semântica do Power BI.
```
