# QA Final — financials-sales (Contoso Finance)

## Resultado geral
**Aprovado com ressalvas**: nenhum item crítico aberto; ressalvas em `pendencias.md`.

## Validação mecânica

| Passo | Comando | Resultado |
|---|---|---|
| Arquivos obrigatórios | `financials-sales.pbip`, `definition.pbir`, `report.json`, `pages.json`, `model.tmdl`, `database.tmdl` | ✅ presentes |
| JSON do relatório | parse de todos os `.json` | ✅ |
| `definition.pbir` | `byPath` → `../financials-sales.SemanticModel` | ✅ |
| Validação PBIR | `powerbi-report-author validate financials-sales.Report` | ✅ 0 erros (1 aviso: schema sem acesso à internet) |
| TMDL | MCP `ConnectFolder` na pasta `definition` | ✅ 10 tabelas, 13 medidas, 5 relacionamentos |
| Desktop abre | `powerbi-desktop open` + `status` | ✅ 2 páginas carregadas |
| Refresh | MCP `RefreshWithXMLA Full` | ✅ sem erro |
| Nomenclatura | `python .github/scripts/validar_nomenclatura.py` | ✅ 0 erros, 0 avisos |
| Vínculos PBIR × TMDL | script de cruzamento Entity/Property | ✅ 0 órfãos |
| Screenshots | `powerbi-desktop screenshot` (Contoso Finance, Página 1) | ✅ todos os visuais com dados, sem cortes nem sobreposição |

## Conferência de valores (DAX contra o modelo atualizado)

| Ano | Receita Líquida | Lucro | Margem | Meta Lucro | Atingimento |
|---|---|---|---|---|---|
| 2013 | $26.415.256 | $3.878.465 | 14,7% | $3.800.000 | 102,1% |
| 2014 | $92.311.095 | $13.015.238 | 14,1% | $14.000.000 | 93,0% |

Mesmos totais do modelo anterior à padronização: a refatoração não alterou valores.

Integridade: 700 linhas na fato, 0 `fk_` vazias, 0 datas sem calendário; 730 dias contínuos no calendário.

## Itens críticos
Nenhum.

## Itens importantes
Ver `pendencias.md` (P01–P03).

## Melhorias futuras
Ver `pendencias.md` (P04–P05).

## Pendências do cliente
Fonte oficial das metas de lucro (P02).

## Checklist de publicação
Não se aplica nesta etapa: projeto de estudo, sem publicação no Fabric.
