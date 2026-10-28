# Pendências — financials-sales

| ID | Descrição | Checklist de origem | Responsável | Prazo |
|---|---|---|---|---|
| P01 | `path_arquivo_financeiro` aponta para a pasta de instalação do Power BI Desktop (versão 2.159.883.0). Ao atualizar o Desktop o caminho muda: copiar o Excel para uma pasta do projeto e ajustar o parâmetro | Power Query | Henrique | Próxima entrega |
| P02 | Metas de lucro (`ft_metas`) estão digitadas no M com `#table`. Trazer de uma planilha ou sistema de metas | Requisitos | Cliente | A definir |
| P03 | `Var % Receita AA` de 2014 (+249%) é distorcida: 2013 só tem dados de set a dez. Avaliar comparação por período equivalente ou ocultar o KPI quando o ano anterior estiver incompleto | DAX | Henrique | Próxima entrega |
| P04 | Valores de faixa de desconto e países em inglês (dado de origem). Traduzir com um `dic_` DE-PARA se o público exigir | Power Query | Henrique | Melhoria futura |
| P05 | Slicer "Analisar por" abre filtrado em Segmento, mas o rótulo exibe "Todos" até a primeira interação | PBIR/DataViz | Henrique | Melhoria futura |
