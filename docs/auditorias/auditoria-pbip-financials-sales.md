# Auditoria — financials-sales (Contoso Finance)

Data: 2026-10-28 · Escopo: modelo semântico completo (nomenclatura, modelagem, Power Query, DAX, BPA) e relatório PBIR.
Skills aplicadas: `power-query-m` (convenção e camadas M), `dimensional-modeling`, `power-bi-best-practices` (BPA), `dax`, `tmdl`, `pbir`, `qa-validation`.

## Resumo executivo

| Indicador | Antes | Depois |
|---|---|---|
| Validador de nomenclatura (`validar_nomenclatura.py`) | 41 erros · 6 avisos | **0 erros · 0 avisos** |
| BPA (Tabular Editor 2, regras Microsoft) | 88 violações (2 de severidade 3) | ver execução do CI no PR |
| `powerbi-report-author validate` | 1 erro | **0 erros** |
| Desenho do modelo | 1 tabela larga + 5 tabelas de apoio | **Modelo estrela**: 2 fatos, 5 dimensões |

Top 3 correções: (1) modelo estrela com chaves inteiras `pk_`/`fk_`; (2) Power Query em camadas Fonte → Staging → Modelo, com parâmetro de caminho; (3) moeda em decimal fixo e colunas da fato ocultas, com medidas formatadas e documentadas.

## Modelo antes × depois

| Antes | Depois | O que mudou |
|---|---|---|
| `financials` (16 colunas em inglês, texto/double) | `ft_financeiro` | Fato com grão declarado (produto × país × segmento × mês), 5 `fk_` ocultas, valores em `decimal` |
| — | `dim_produto`, `dim_pais`, `dim_segmento`, `dim_faixa_desconto` | Dimensões geradas no Power Query a partir da fonte, chave `pk_` inteira |
| `dCalendario` (DAX `CALENDAR`) | `dim_calendario` | Gerado pela função `fx_gera_calendario` no Power Query; `pk_data` marcada como chave, tabela de datas, meses em português com `sortByColumn` |
| `Metas Anuais` (tabela calculada) | `ft_metas` | Metas são fato (grão: ano); ligadas por `TREATAS` ao calendário |
| `_Medidas` | `Medidas` | 13 medidas com `formatString`, `displayFolder` e descrição |
| `cgTempo` (`Período`, `var_aa`) | `gc_inteligencia_tempo` | Coluna `ct_periodo`, item `Var % AA` |
| `Parametro Dimensao` | `pc_dimensao_analise` | Coluna `ct_dimensao_analise`, colunas técnicas `ct_campo_dimensao`/`nu_ordem_dimensao` |

```
                     dim_calendario (pk_data)
                              │ 1
                              │ *
dim_produto ──1───*──  ft_financeiro  ──*───1── dim_pais
dim_segmento ─1───*──  (fk_data_venda, fk_produto, fk_pais,
dim_faixa_desconto 1─*  fk_segmento, fk_faixa_desconto)

ft_metas (nu_ano) ··· TREATAS ··· dim_calendario[nu_ano]
```

Relacionamentos: 5, todos 1:* com filtro único (dimensão → fato), todos ativos.

## Power Query (skill `power-query-m`)

| Query | Grupo | Carrega | Papel |
|---|---|---|---|
| `path_arquivo_financeiro` | Caminhos | não | Parâmetro com o caminho do Excel (antes: caminho fixo dentro da query) |
| `fx_gera_calendario` | Funções | não | Gera calendário diário contínuo |
| `src_financeiro` | Fontes | não | Tabela bruta do Excel |
| `stg_financeiro` | Staging | não | Renomeia para a convenção, tipa logo após a fonte e limpa espaços (`Text.Trim`) |
| `dim_*` | Dimensões | sim | Distintos + chave inteira |
| `ft_financeiro`, `ft_metas` | Fatos | sim | Merge com as dimensões para trocar texto por `fk_` |

- Etapas renomeadas em camelCase (`colunasRenomeadas`, `tiposAjustados`…); variáveis internas com `__` (`__DataInicial`, `__listaOrdemFaixas`). Saíram `financials_Table` e `#"Tipo Alterado"`.
- Query folding: não se aplica (fonte Excel não dobra).

## BPA — violações tratadas

| Regra (ID) | Sev. | Antes | Correção |
|---|---|---|---|
| `DO_NOT_USE_FLOATING_POINT_DATA_TYPES` | 🟡 | 9 colunas `double` | `Currency.Type` no M → `decimal` no modelo |
| `PROVIDE_FORMAT_STRING_FOR_MEASURES` | 🔴 | `Unidades Vendidas` | `#,0` em todas as medidas |
| `DO_NOT_SUMMARIZE_NUMERIC_COLUMNS` | 🔴 | `Meta Lucro` e outras | `summarizeBy: none` em todas as colunas |
| `HIDE_FOREIGN_KEYS` | 🟡 | `financials[Date]` visível | Todas as `fk_` com `isHidden` |
| `MARK_PRIMARY_KEYS` | 🔵 | — | `isKey` nas `pk_` |
| `SET_ISAVAILABLEINMDX_TO_FALSE_ON_NON-ATTRIBUTE_COLUMNS` | 🟡 | colunas ocultas | `isAvailableInMdx: false` nas ocultas sem ordenação |
| `REDUCE_USAGE_OF_CALCULATED_TABLES` | 🟡 | 4 tabelas | Calendário e metas foram para o Power Query; ficaram só `Medidas` e `pc_` (exigidas pelo recurso) |
| `VISIBLE_OBJECTS_WITH_NO_DESCRIPTION` | 🔵 | tabelas e medidas | Descrição `///` em tabelas, colunas visíveis e medidas |
| `PERCENTAGES_SHOULD_BE_FORMATTED…` | 🔵 | `0.0%` | `#,0.0%` |
| `MONTH_(AS_A_STRING)_MUST_BE_SORTED` | 🔵 | — | `nm_mes`, `ct_mes_ano`, `ct_trimestre` com `sortByColumn` |

### Exceções aceitas (não corrigir)

| Regra | Objeto | Motivo |
|---|---|---|
| `ENSURE_TABLES_HAVE_RELATIONSHIPS` | `Medidas`, `pc_dimensao_analise` | Tabela de medidas e parâmetro de campo são desconectados por definição |
| `ENSURE_TABLES_HAVE_RELATIONSHIPS` | `ft_metas` | Grão anual; a ligação é feita por `TREATAS` na medida `[Meta Lucro]` |
| `REMOVE_UNNECESSARY_COLUMNS` | `pc_dimensao_analise[ct_campo_dimensao]` | Coluna exigida pelo parâmetro de campo |
| `FIRST_LETTER_OF_OBJECTS_MUST_BE_CAPITALIZED` | colunas e tabelas | Conflita com a convenção snake_case do curso; a convenção prevalece |

## DAX (skill `dax`)

- Todas as medidas na tabela `Medidas`, agrupadas em 5 pastas (01. Receita … 05. Metas).
- `DIVIDE` em todas as divisões; variáveis com `__` em `Var % Receita AA` e no item `Var % AA` do grupo de cálculo.
- Inteligência de tempo sempre sobre `dim_calendario[pk_data]`.
- Renomeadas: `total_lucro` → `Lucro`, `med_preco_medio` → `Preço Médio Unitário`, `Receita  por Pais` → `Receita Média por País` (agora `AVERAGEX` por país), `Var % AA` → `Var % Receita AA`. Removida: `Dias no Periodo` (sem uso).

## Relatório (skill `pbir`)

- Todos os vínculos dos visuais atualizados e cruzados com o TMDL: 0 referências órfãs.
- Títulos narrativos com o achado de cada gráfico (picos de out/dez 2014; França lidera o lucro; Paseo lidera a receita).
- Matriz da "Página 1" corrigida: tinha linhas sem nenhum valor; agora mostra receita por país.

## Regras verificadas e aprovadas
Nomenclatura do curso · modelo estrela sem bidirecional nem muitos-para-muitos · calendário contínuo e marcado · chaves inteiras · sem `LocalDateTable` · sem tabelas `src_`/`stg_` carregadas · `discourageImplicitMeasures` · grupos de query na ordem da convenção · format string em todas as medidas.
