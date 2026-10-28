#!/usr/bin/env python3
"""Valida a convenção de nomenclatura de modelos semânticos PBIP (TMDL).

Lê as regras de .github/pbip/convencao-nomenclatura.yml, percorre todas as
pastas *.SemanticModel/definition do repositório e reporta as violações
como anotações do GitHub Actions + resumo em Markdown.

Uso:
    python validar_nomenclatura.py --config convencao-nomenclatura.yml --raiz .
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Nome TMDL: 'Com Espaço' (aspas simples, '' escapa) ou NomeSimples
NOME = r"(?:'(?:[^']|'')+'|[^\s='.]+)"
RE_OBJETO = re.compile(rf"^(measure|column|partition|calculationGroup|hierarchy)\b\s*({NOME})?")
RE_PROPRIEDADE = re.compile(
    r"^(isHidden|formatString|displayFolder|dataCategory|dataType|precedence|extendedProperty|"
    r"mode|queryGroup|source)\b\s*[:=]?\s*(.*)$"
)
RE_ITEM_CALCULO = re.compile(rf"^calculationItem\s+({NOME})")
RE_REFERENCIA = re.compile(rf"^({NOME})\.({NOME})$")
# Etapa do M: "nomeEtapa = ..." ou #"Nome Com Espaço" = ...
RE_ETAPA_M = re.compile(r'^(#"(?:[^"]|"")*"|[A-Za-z_][A-Za-z0-9_]*)\s*=(?![=>])')

ROTULOS = {
    "medidas": "medidas",
    "parametro_campo": "parâmetro de campo",
    "parametro_numerico": "parâmetro numérico",
    "grupo_calculo": "grupo de cálculo",
}


def sem_aspas(nome: str) -> str:
    nome = nome.strip()
    if len(nome) >= 2 and nome[0] == nome[-1] == "'":
        return nome[1:-1].replace("''", "'")
    return nome


def nivel(linha: str) -> int:
    return len(linha) - len(linha.lstrip("\t"))


@dataclass
class Coluna:
    nome: str
    linha: int
    oculta: bool = False
    parametro_campo: bool = False
    tipo: str | None = None


@dataclass
class Medida:
    nome: str
    linha: int
    format_string: bool = False
    display_folder: bool = False


@dataclass
class Tabela:
    nome: str
    arquivo: Path
    linha: int
    colunas: list[Coluna] = field(default_factory=list)
    medidas: list[Medida] = field(default_factory=list)
    itens_calculo: list[tuple[str, int]] = field(default_factory=list)
    grupo_calculo: bool = False
    precedencia: int | None = None
    data_category: str | None = None
    codigo_m: list[tuple[int, str]] = field(default_factory=list)
    particao_m: bool = False
    particao_calculada: bool = False
    query_group: str | None = None


@dataclass
class Expressao:
    nome: str
    arquivo: Path
    linha: int
    codigo: list[tuple[int, str]] = field(default_factory=list)
    query_group: str | None = None

    @property
    def texto(self) -> str:
        return "\n".join(t for _, t in self.codigo)

    @property
    def parametro(self) -> bool:
        return "IsParameterQuery=true" in self.texto.replace(" ", "")

    @property
    def funcao(self) -> bool:
        return bool(re.match(r"\s*\(.*?\)\s*(as\s+[\w.]+\s*)?=>", self.texto, re.S))


@dataclass
class Relacionamento:
    arquivo: Path
    linha: int
    de: tuple[str, str] | None = None
    para: tuple[str, str] | None = None
    de_cardinalidade: str = "many"
    para_cardinalidade: str = "one"


@dataclass
class Violacao:
    severidade: str
    regra: str
    arquivo: Path
    linha: int
    mensagem: str


# ============================================================== leitura TMDL
def ler_tabela(caminho: Path) -> Tabela | None:
    tabela: Tabela | None = None
    atual: object = None
    em_bloco = False  # dentro de ``` ... ```
    for n, linha in enumerate(caminho.read_text(encoding="utf-8-sig").splitlines(), 1):
        texto = linha.strip()
        if em_bloco:
            if atual == "partition":
                tabela.codigo_m.append((n, texto))
            if texto.startswith("```"):
                em_bloco = False
            continue
        if texto.count("```") == 1:
            em_bloco = True
        if not texto or texto.startswith("//"):
            continue

        profundidade = nivel(linha)
        if profundidade == 0:
            m = re.match(rf"^table\s+({NOME})", texto)
            if m:
                tabela = Tabela(sem_aspas(m.group(1)), caminho, n)
            continue
        if tabela is None:
            continue

        if profundidade == 1:
            atual = None
            m = RE_OBJETO.match(texto)
            if not m:
                prop = RE_PROPRIEDADE.match(texto)
                if prop and prop.group(1) == "dataCategory":
                    tabela.data_category = prop.group(2).strip()
                continue
            tipo, nome = m.group(1), sem_aspas(m.group(2) or "")
            if tipo == "column":
                atual = Coluna(nome, n)
                tabela.colunas.append(atual)
            elif tipo == "measure":
                atual = Medida(nome, n)
                tabela.medidas.append(atual)
            elif tipo == "calculationGroup":
                tabela.grupo_calculo = True
                atual = "calculationGroup"
            elif tipo == "partition":
                tabela.particao_calculada = texto.endswith("= calculated")
                tabela.particao_m = texto.endswith("= m")
                atual = "partition"
            continue

        if atual == "partition":
            prop = RE_PROPRIEDADE.match(texto) if profundidade == 2 else None
            if prop and prop.group(1) == "queryGroup":
                tabela.query_group = sem_aspas(prop.group(2))
            elif prop and prop.group(1) == "source":
                if prop.group(2).strip():
                    tabela.codigo_m.append((n, prop.group(2).strip()))
            elif not prop:
                tabela.codigo_m.append((n, texto))
            continue
        if profundidade != 2:
            continue

        if atual == "calculationGroup":
            item = RE_ITEM_CALCULO.match(texto)
            if item:
                tabela.itens_calculo.append((sem_aspas(item.group(1)), n))
                continue
        prop = RE_PROPRIEDADE.match(texto)
        if not prop:
            continue
        chave, valor = prop.group(1), prop.group(2).strip()
        if isinstance(atual, Coluna):
            if chave == "isHidden":
                atual.oculta = valor.lower() != "false"
            elif chave == "dataType":
                atual.tipo = valor
            elif chave == "extendedProperty" and "ParameterMetadata" in valor:
                atual.parametro_campo = True
        elif isinstance(atual, Medida):
            if chave == "formatString":
                atual.format_string = True
            elif chave == "displayFolder":
                atual.display_folder = True
        elif atual == "calculationGroup" and chave == "precedence":
            tabela.precedencia = int(valor)
    return tabela


def ler_expressoes(definicao: Path) -> list[Expressao]:
    arquivo = definicao / "expressions.tmdl"
    if not arquivo.exists():
        return []
    expressoes: list[Expressao] = []
    atual: Expressao | None = None
    em_bloco = False
    for n, linha in enumerate(arquivo.read_text(encoding="utf-8-sig").splitlines(), 1):
        texto = linha.strip()
        if em_bloco:
            atual.codigo.append((n, texto))
            if texto.startswith("```"):
                em_bloco = False
            continue
        if not texto:
            continue
        profundidade = nivel(linha)
        if profundidade == 0:
            m = re.match(rf"^expression\s+({NOME})\s*=\s*(.*)$", texto)
            atual = Expressao(sem_aspas(m.group(1)), arquivo, n) if m else None
            if atual:
                expressoes.append(atual)
                if m.group(2):
                    atual.codigo.append((n, m.group(2)))
                    em_bloco = m.group(2).count("```") == 1
            continue
        if atual is None:
            continue
        if profundidade == 1:
            prop = RE_PROPRIEDADE.match(texto)
            if prop and prop.group(1) == "queryGroup":
                atual.query_group = sem_aspas(prop.group(2))
            continue
        atual.codigo.append((n, texto))
    return expressoes


def ler_relacionamentos(definicao: Path) -> list[Relacionamento]:
    arquivo = definicao / "relationships.tmdl"
    if not arquivo.exists():
        return []
    resultado: list[Relacionamento] = []
    for n, linha in enumerate(arquivo.read_text(encoding="utf-8-sig").splitlines(), 1):
        texto = linha.strip()
        if texto.startswith("relationship "):
            resultado.append(Relacionamento(arquivo, n))
            continue
        if not resultado or ":" not in texto:
            continue
        chave, valor = (p.strip() for p in texto.split(":", 1))
        rel = resultado[-1]
        if chave in ("fromColumn", "toColumn"):
            m = RE_REFERENCIA.match(valor)
            if m:
                ref = (sem_aspas(m.group(1)), sem_aspas(m.group(2)))
                if chave == "fromColumn":
                    rel.de = ref
                else:
                    rel.para = ref
        elif chave == "fromCardinality":
            rel.de_cardinalidade = valor
        elif chave == "toCardinality":
            rel.para_cardinalidade = valor
    return resultado


# ================================================================ validação
class Validador:
    def __init__(self, config: dict):
        self.cfg = config
        self.violacoes: list[Violacao] = []
        cfg_t = config["tabelas"]
        self.re_tabela = {
            tipo: re.compile("^" + re.escape(c["prefixo"]) + cfg_t["sufixo"])
            for tipo, c in cfg_t["prefixos"].items()
        }
        for tipo in ("parametro_campo", "parametro_numerico", "grupo_calculo"):
            cfg_t[tipo]["padrao"] = "^" + re.escape(cfg_t[tipo]["prefixo"]) + cfg_t["sufixo"]

    def reportar(self, sev: str, regra: str, arquivo: Path, linha: int, msg: str):
        self.violacoes.append(Violacao(sev, regra, arquivo, linha, msg))

    def checar_geral(self, nome: str, rotulo: str, arquivo: Path, linha: int):
        g = self.cfg["geral"]
        if nome != nome.strip() or "  " in nome or re.search(r"[\t\r\n]", nome):
            self.reportar(g["proibir_espacos_irregulares"]["severidade"], "GER001", arquivo, linha,
                          f"{rotulo} tem espaço no início/fim, espaço duplo ou quebra de linha.")
        proibidos = [c for c in g["caracteres_proibidos"]["lista"] if c in nome]
        if proibidos:
            self.reportar(g["caracteres_proibidos"]["severidade"], "GER002", arquivo, linha,
                          f"{rotulo} contém caracteres proibidos: {' '.join(proibidos)}")
        for padrao in g["nomes_genericos"]["padroes"]:
            if re.match(padrao, nome, re.IGNORECASE):
                self.reportar(g["nomes_genericos"]["severidade"], "GER003", arquivo, linha,
                              f"{rotulo} tem nome genérico gerado pelo Power BI. Renomeie.")
                break

    def checar_padrao(self, nome: str, regra_cfg: dict, regra: str, rotulo: str,
                      arquivo: Path, linha: int) -> bool:
        if re.match(regra_cfg["padrao"], nome):
            return True
        self.reportar(regra_cfg.get("severidade", "erro"), regra, arquivo, linha,
                      f"{rotulo} fora do padrão. Exemplo: '{regra_cfg['exemplo']}' "
                      f"(regex: {regra_cfg['padrao']})")
        return False

    # ----------------------------------------------------------- tabelas
    def classificar(self, t: Tabela) -> str | None:
        if t.grupo_calculo:
            return "grupo_calculo"
        if any(c.parametro_campo for c in t.colunas):
            return "parametro_campo"
        if t.particao_calculada and any("GENERATESERIES" in x.upper() for _, x in t.codigo_m):
            return "parametro_numerico"
        if t.medidas and all(c.oculta for c in t.colunas):
            return "medidas"
        for tipo, regex in self.re_tabela.items():
            if regex.match(t.nome):
                return tipo
        return None

    def validar_modelo(self, definicao: Path) -> int:
        cfg_t = self.cfg["tabelas"]
        tabelas = [t for t in (ler_tabela(p) for p in sorted((definicao / "tables").glob("*.tmdl"))) if t]
        tabelas = [t for t in tabelas if t.nome not in (cfg_t.get("ignorar") or [])]
        expressoes = ler_expressoes(definicao)
        usa_grupos = any(t.query_group for t in tabelas) or any(e.query_group for e in expressoes)
        por_nome = {t.nome: t for t in tabelas}

        for t in tabelas:
            tipo = self.classificar(t)
            if t.nome.startswith(("LocalDateTable_", "DateTableTemplate_")):
                self.reportar(cfg_t["proibir_data_automatica"]["severidade"], "TAB002", t.arquivo, t.linha,
                              f"Tabela '{t.nome}' indica 'Data/hora automática' ligada. Desative em "
                              "Opções > Carregamento de dados e use uma dim_calendario.")
                continue

            self.checar_geral(t.nome, f"Tabela '{t.nome}'", t.arquivo, t.linha)
            if t.nome.startswith(tuple(cfg_t["nao_carregar"]["prefixos"])):
                self.reportar(cfg_t["nao_carregar"]["severidade"], "TAB004", t.arquivo, t.linha,
                              f"Tabela '{t.nome}' é camada intermediária (src_/stg_) e está carregada. "
                              "Desmarque 'Habilitar carga' no Power Query.")
            elif tipo is None:
                exemplos = ", ".join(c["exemplo"] for c in cfg_t["prefixos"].values())
                self.reportar(cfg_t["sem_classificacao"]["severidade"], "TAB001", t.arquivo, t.linha,
                              f"Tabela '{t.nome}' não segue a convenção snake_case com prefixo "
                              f"(ex.: {exemplos}).")
            elif tipo in ROTULOS:
                self.checar_padrao(t.nome, cfg_t[tipo], "TAB003", f"Tabela de {ROTULOS[tipo]} '{t.nome}'",
                                   t.arquivo, t.linha)

            if tipo == "grupo_calculo":
                self.validar_grupo_calculo(t)
            elif tipo == "parametro_campo":
                self.validar_parametro_campo(t)
            elif tipo not in ("medidas", "parametro_numerico"):
                self.validar_colunas(t)
            if tipo != "parametro_numerico":
                self.validar_medidas(t, tipo)

            if t.particao_m:
                grupo = cfg_t["prefixos"].get(tipo, {}).get("grupo") if tipo else None
                self.validar_grupo_query(t.nome, t.query_group, grupo, usa_grupos, t.arquivo, t.linha)
                self.validar_etapas(t.nome, t.codigo_m, t.arquivo)

        self.validar_expressoes(expressoes, usa_grupos)
        self.validar_precedencias([t for t in tabelas if t.grupo_calculo])
        self.validar_relacionamentos(definicao, por_nome)
        self.validar_calendario(por_nome)
        return len(tabelas)

    # ----------------------------------------------------------- colunas
    def validar_colunas(self, t: Tabela):
        cfg_c = self.cfg["colunas"]
        regras_tipo = cfg_c["tipos"]["regras"]
        # Tipos exclusivos de um prefixo (dateTime -> dt_, boolean -> fl_)
        exclusivos = {tipos[0]: prefixo for prefixo, tipos in regras_tipo.items() if len(tipos) == 1}
        for c in t.colunas:
            rotulo = f"Coluna {t.nome}[{c.nome}]"
            self.checar_geral(c.nome, rotulo, t.arquivo, c.linha)
            if not self.checar_padrao(c.nome, cfg_c, "COL001", rotulo, t.arquivo, c.linha) or not c.tipo:
                continue
            prefixo = c.nome.split("_", 1)[0] + "_"
            permitidos = regras_tipo.get(prefixo)
            if permitidos and c.tipo not in permitidos:
                self.reportar(cfg_c["tipos"]["severidade"], "COL002", t.arquivo, c.linha,
                              f"{rotulo} usa '{prefixo}' mas o tipo é '{c.tipo}' "
                              f"(esperado: {', '.join(permitidos)}).")
            esperado = exclusivos.get(c.tipo)
            if esperado and prefixo not in (esperado, "pk_", "fk_"):
                self.reportar(cfg_c["tipos"]["severidade"], "COL002", t.arquivo, c.linha,
                              f"{rotulo} é do tipo '{c.tipo}' e deveria usar o prefixo '{esperado}'.")

    def validar_relacionamentos(self, definicao: Path, tabelas: dict[str, Tabela]):
        sev = self.cfg["colunas"]["chaves"]["severidade"]
        for rel in ler_relacionamentos(definicao):
            for lado, card in ((rel.de, rel.de_cardinalidade), (rel.para, rel.para_cardinalidade)):
                if not lado or lado[0] not in tabelas:
                    continue
                tabela = tabelas[lado[0]]
                coluna = next((c for c in tabela.colunas if c.nome == lado[1]), None)
                if coluna is None:
                    continue
                esperado = "fk_" if card == "many" else "pk_"
                rotulo = f"{tabela.nome}[{coluna.nome}]"
                if not coluna.nome.startswith(esperado):
                    self.reportar(sev, "COL003", tabela.arquivo, coluna.linha,
                                  f"Chave {rotulo} está no lado '{card}' do relacionamento e deve "
                                  f"usar o prefixo '{esperado}'.")
                if esperado == "fk_" and not coluna.oculta:
                    self.reportar(sev, "COL004", tabela.arquivo, coluna.linha,
                                  f"Chave estrangeira {rotulo} deve estar oculta (isHidden).")

    def validar_calendario(self, tabelas: dict[str, Tabela]):
        cfg_cal = self.cfg["colunas"]["calendario"]
        for nome in cfg_cal["tabelas"]:
            t = tabelas.get(nome)
            if not t:
                continue
            if (t.data_category or "").lower() != "time":
                self.reportar(cfg_cal["severidade"], "COL005", t.arquivo, t.linha,
                              f"Tabela '{nome}' não está marcada como tabela de datas.")
            if not any(c.nome == cfg_cal["coluna_chave"] for c in t.colunas):
                self.reportar(cfg_cal["severidade"], "COL005", t.arquivo, t.linha,
                              f"Tabela '{nome}' não tem a coluna '{cfg_cal['coluna_chave']}' "
                              "(base da inteligência de tempo).")

    # ------------------------------------------------- grupo de cálculo
    def validar_grupo_calculo(self, t: Tabela):
        cfg_g = self.cfg["grupo_calculo"]
        for c in t.colunas:
            if c.nome == "Ordinal" and c.oculta:
                continue
            rotulo = f"Coluna do grupo de cálculo {t.nome}[{c.nome}]"
            self.checar_geral(c.nome, rotulo, t.arquivo, c.linha)
            self.checar_padrao(c.nome, cfg_g["coluna"], "GC001", rotulo, t.arquivo, c.linha)
        for nome, linha in t.itens_calculo:
            rotulo = f"Item de cálculo '{nome}' ({t.nome})"
            self.checar_geral(nome, rotulo, t.arquivo, linha)
            self.checar_padrao(nome, cfg_g["itens"], "GC002", rotulo, t.arquivo, linha)

    def validar_precedencias(self, grupos: list[Tabela]):
        sev = self.cfg["grupo_calculo"]["precedencia_unica"]["severidade"]
        vistos: dict[int, str] = {}
        for t in grupos:
            p = t.precedencia or 0
            if p in vistos:
                self.reportar(sev, "GC003", t.arquivo, t.linha,
                              f"Grupo de cálculo '{t.nome}' tem a mesma precedência ({p}) de "
                              f"'{vistos[p]}'. Defina precedências diferentes.")
            vistos.setdefault(p, t.nome)

    # ------------------------------------------------ parâmetro de campo
    def validar_parametro_campo(self, t: Tabela):
        cfg_p = self.cfg["parametro_campo"]["coluna"]
        for c in t.colunas:
            if not c.oculta:
                self.checar_padrao(c.nome, cfg_p, "PC001", f"Coluna do parâmetro de campo {t.nome}[{c.nome}]",
                                   t.arquivo, c.linha)

    # ----------------------------------------------------------- medidas
    def validar_medidas(self, t: Tabela, tipo: str | None):
        cfg_m = self.cfg["medidas"]
        for m in t.medidas:
            rotulo = f"Medida [{m.nome}]"
            self.checar_geral(m.nome, rotulo, t.arquivo, m.linha)
            if re.match(cfg_m["proibir_cara_de_coluna"]["padrao"], m.nome):
                self.reportar(cfg_m["proibir_cara_de_coluna"]["severidade"], "MED005", t.arquivo, m.linha,
                              f"{rotulo} parece nome de coluna. Medidas usam nome de negócio com "
                              f"espaço (ex.: '{cfg_m['exemplo']}').")
            else:
                self.checar_padrao(m.nome, cfg_m, "MED001", rotulo, t.arquivo, m.linha)
            if tipo not in ("medidas", "grupo_calculo"):
                self.reportar(cfg_m["exigir_tabela_medidas"]["severidade"], "MED002", t.arquivo, m.linha,
                              f"{rotulo} está na tabela '{t.nome}'. Mova para a tabela 'Medidas'.")
            if not m.format_string:
                self.reportar(cfg_m["exigir_format_string"]["severidade"], "MED003", t.arquivo, m.linha,
                              f"{rotulo} sem formatString definido.")
            if not m.display_folder:
                self.reportar(cfg_m["exigir_display_folder"]["severidade"], "MED004", t.arquivo, m.linha,
                              f"{rotulo} sem displayFolder (pasta de exibição).")

    # ---------------------------------------------------- Power Query (M)
    def validar_expressoes(self, expressoes: list[Expressao], usa_grupos: bool):
        cfg_q = self.cfg["queries"]
        for e in expressoes:
            self.checar_geral(e.nome, f"Query '{e.nome}'", e.arquivo, e.linha)
            if e.parametro:
                regra, rotulo, codigo = cfg_q["parametro"], "Parâmetro", "PQ001"
            elif e.funcao:
                regra, rotulo, codigo = cfg_q["funcao"], "Função", "PQ002"
            else:
                regra, rotulo, codigo = cfg_q["outras"], "Query", "PQ003"
            if e.nome not in (regra.get("excecoes") or []) and not re.match(
                    "^(" + "|".join(map(re.escape, regra["prefixos"])) + ")" + self.cfg["tabelas"]["sufixo"],
                    e.nome):
                self.reportar(regra["severidade"], codigo, e.arquivo, e.linha,
                              f"{rotulo} '{e.nome}' deve ser snake_case com prefixo "
                              f"{' / '.join(regra['prefixos'])} (ex.: '{regra['exemplo']}').")
            prefixo = next((p for p in cfg_q["grupos"]["por_prefixo"] if e.nome.startswith(p)), None)
            esperado = cfg_q["grupos"]["por_prefixo"].get(prefixo)
            self.validar_grupo_query(e.nome, e.query_group, esperado, usa_grupos, e.arquivo, e.linha)
            if not e.parametro:
                self.validar_etapas(e.nome, e.codigo, e.arquivo)

    def validar_grupo_query(self, nome: str, atual: str | None, esperado: str | None,
                            usa_grupos: bool, arquivo: Path, linha: int):
        sev = self.cfg["queries"]["grupos"]["severidade"]
        if not usa_grupos or not esperado:
            return
        if atual is None:
            self.reportar(sev, "PQ004", arquivo, linha, f"Query '{nome}' está fora de pasta. "
                                                        f"Mova para o grupo '{esperado}'.")
        elif atual != esperado:
            self.reportar(sev, "PQ004", arquivo, linha, f"Query '{nome}' está no grupo '{atual}'; "
                                                        f"o esperado é '{esperado}'.")

    def validar_etapas(self, query: str, codigo: list[tuple[int, str]], arquivo: Path):
        cfg_e = self.cfg["queries"]["etapas"]
        for n, texto in codigo:
            m = RE_ETAPA_M.match(texto)
            if not m or m.group(1) in ("let", "in"):
                continue
            etapa = m.group(1)
            if etapa in cfg_e["excecoes"] or re.match(cfg_e["padrao"], etapa):
                continue
            self.reportar(cfg_e["severidade"], "PQ005", arquivo, n,
                          f"Etapa {etapa} da query '{query}' não está em camelCase descritivo "
                          f"(ex.: '{cfg_e['exemplo']}').")


# ===================================================================== saída
def escapar_anotacao(texto: str) -> str:
    return texto.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--raiz", default=".", type=Path)
    parser.add_argument("--estrito", action="store_true", help="avisos também reprovam")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    raiz = args.raiz.resolve()
    validador = Validador(config)

    modelos = sorted(p for p in raiz.rglob("*.SemanticModel") if p.is_dir())
    if not modelos:
        print("Nenhuma pasta *.SemanticModel encontrada. Nada a validar.")
        return 0

    for modelo in modelos:
        definicao = modelo / "definition"
        if not definicao.is_dir():
            validador.reportar("aviso", "MOD001", modelo, 1,
                               f"'{modelo.name}' não está em TMDL. Ative 'Armazenar modelo semântico "
                               "usando o formato TMDL' nas opções de visualização do Power BI Desktop.")
            continue
        qtd = validador.validar_modelo(definicao)
        print(f"{modelo.relative_to(raiz)}: {qtd} tabela(s) analisada(s)")

    erros = [v for v in validador.violacoes if v.severidade == "erro"]
    avisos = [v for v in validador.violacoes if v.severidade != "erro"]
    no_actions = os.getenv("GITHUB_ACTIONS") == "true"

    for v in sorted(validador.violacoes, key=lambda v: (str(v.arquivo), v.linha)):
        rel = v.arquivo.relative_to(raiz).as_posix()
        if no_actions:
            nivel_gh = "error" if v.severidade == "erro" else "warning"
            print(f"::{nivel_gh} file={rel},line={v.linha},title={v.regra}::{escapar_anotacao(v.mensagem)}")
        else:
            print(f"[{v.severidade.upper()}] {v.regra} {rel}:{v.linha} - {v.mensagem}")

    resumo = os.getenv("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as f:
            f.write("## Convenção de nomenclatura PBIP\n\n")
            f.write(f"**{len(erros)}** erro(s) · **{len(avisos)}** aviso(s)\n\n")
            if validador.violacoes:
                f.write("| Severidade | Regra | Arquivo | Mensagem |\n|---|---|---|---|\n")
                for v in validador.violacoes:
                    rel = v.arquivo.relative_to(raiz).as_posix()
                    msg = v.mensagem.replace("|", "\\|")
                    f.write(f"| {v.severidade} | {v.regra} | `{rel}:{v.linha}` | {msg} |\n")

    print(f"\nResultado: {len(erros)} erro(s), {len(avisos)} aviso(s).")
    return 1 if erros or (args.estrito and avisos) else 0


if __name__ == "__main__":
    sys.exit(main())
