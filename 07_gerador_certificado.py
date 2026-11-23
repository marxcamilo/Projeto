"""
07_gerador_certificado.py
Projeto Aplicado I — AV04 (MVP Final) | Empresa parceira: Schulz S.A.
Equipe: Marx Braga Camilo, Gladson Goulart, Carla Tayna, Yorman Hernandez

Módulo Integrado de Ingestão (ETL) e Gerador de Certificados.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional


def _pasta_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent

def _pasta_executavel() -> Path:
    """Pasta onde o .exe está — é onde o banco e os certificados devem ficar."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

PASTA = _pasta_base()         
PASTA_DADOS = _pasta_executavel()  

DB_PADRAO = str(PASTA_DADOS / "schulz_calibracao.db")
SQL_DDL = PASTA / "03_banco.sql"
PASTA_SAIDA = PASTA_DADOS / "certificados"

# ---------------------------------------------------------------------
# Carrega o 04_classes.py (nome começa com número: import direto falha)
# ---------------------------------------------------------------------

def _carregar_classes():
    caminho = PASTA / "04_classes.py"
    if not caminho.exists():
        raise SystemExit(
            f"[ERRO] 04_classes.py não encontrado em {PASTA}.\n"
            "Coloque este arquivo na mesma pasta do 04_classes.py."
        )
    spec = importlib.util.spec_from_file_location("classes_04", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo

_classes = _carregar_classes()

ConexaoSQLite = _classes.ConexaoSQLite
Tecnico = _classes.Tecnico
Equipamento = _classes.Equipamento
Medicao = _classes.Medicao
Certificado = _classes.Certificado
TecnicoDAO = _classes.TecnicoDAO
EquipamentoDAO = _classes.EquipamentoDAO
MedicaoDAO = _classes.MedicaoDAO
CertificadoDAO = _classes.CertificadoDAO
ErroValidacao = _classes.ErroValidacao
ErroPersistencia = _classes.ErroPersistencia

DB_PADRAO = str(PASTA / "schulz_calibracao.db")
SQL_DDL = PASTA / "03_banco.sql"
PASTA_SAIDA = PASTA / "certificados"

# =====================================================================
# 1. LOG DE SANEAMENTO
# =====================================================================
@dataclass
class LogSaneamento:
    """
    Registra cada correção aplicada. É a evidência do plano de testes:
    o relatório final mostra quantas linhas foram corrigidas e por quê.
    """
    eventos: list[dict] = field(default_factory=list)

    def registrar(self, regra: str, campo: str, original, corrigido, linha: int = 0):
        self.eventos.append({
            "regra": regra,
            "campo": campo,
            "original": original,
            "corrigido": corrigido,
            "linha": linha,
        })

    def resumo(self) -> dict:
        contagem: dict[str, int] = {}
        for e in self.eventos:
            contagem[e["regra"]] = contagem.get(e["regra"], 0) + 1
        return contagem

    def imprimir(self) -> None:
        if not self.eventos:
            print("    Nenhuma correção necessária — planilha já estava limpa.")
            return
        for regra, qtd in sorted(self.resumo().items()):
            print(f"    {regra:<42} {qtd:>3} ocorrência(s)")


# =====================================================================
# 2. REGRAS DE SANEAMENTO (AV01)
# =====================================================================
PLACEHOLDERS = {"", " ", "-", "--", "---", "----", "-----", "???", "00/00/0000",
                "00/00/00", "n/a", "na", "null", "none", "#n/d", "#value!",
                "#ref!", "#name?", "******"}

def limpar_texto(valor, campo: str, log: LogSaneamento, linha: int = 0) -> Optional[str]:
    """
    Remove espaços, normaliza acentos e rejeita placeholders.
    Retorna None quando o valor é inútil.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if texto.lower() in PLACEHOLDERS:
        if texto:
            log.registrar("Placeholder descartado", campo, texto, None, linha)
        return None
    # Remove acentos: DIÂMETRO -> DIAMETRO (regra de padronização AV01)
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    if sem_acento != texto:
        log.registrar("Acentuação normalizada", campo, texto, sem_acento, linha)
    # Colapsa espaços múltiplos
    sem_acento = re.sub(r"\s+", " ", sem_acento).strip()
    return sem_acento or None


def limpar_numero(valor, campo: str, log: LogSaneamento, linha: int = 0) -> Optional[float]:
    """
    Converte para float aceitando vírgula decimal, texto numérico e
    notação científica. Rejeita placeholders e valores não finitos.
    """
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        numero = float(valor)
    else:
        texto = str(valor).strip()
        if texto.lower() in PLACEHOLDERS:
            log.registrar("Placeholder numérico descartado", campo, texto, None, linha)
            return None
        # Remove separador de milhar e troca vírgula por ponto
        texto = texto.replace(" ", "").replace("\u00a0", "")
        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", ".")
        try:
            numero = float(texto)
        except ValueError:
            log.registrar("Número inválido descartado", campo, texto, None, linha)
            return None
    if numero != numero or numero in (float("inf"), float("-inf")):
        log.registrar("Número não finito descartado", campo, valor, None, linha)
        return None
    return numero


def normalizar_tolerancia(valor: float, campo: str, log: LogSaneamento,
                          linha: int = 0) -> float:
    """
    REGRA CRÍTICA: tol_menos vem com sinal negativo na planilha da Schulz
    (ex.: -0,01). O banco guarda sempre em valor absoluto.
    Sem isso, classificar() inverte os limites e reprova tudo.
    """
    absoluto = abs(valor)
    if valor < 0:
        log.registrar("Tolerância normalizada (abs)", campo, valor, absoluto, linha)
    return absoluto


def normalizar_data(valor, log: LogSaneamento, linha: int = 0) -> Optional[str]:
    """Converte date/datetime/string para ISO AAAA-MM-DD. Rejeita placeholders."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor).strip()
    if texto.lower() in PLACEHOLDERS:
        log.registrar("Data placeholder descartada", "data", texto, None, linha)
        return None
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    log.registrar("Data em formato desconhecido", "data", texto, None, linha)
    return None


# =====================================================================
# 3. LEITOR DAS PLANILHAS
# =====================================================================
@dataclass
class ParametroLido:
    """Um parâmetro avaliado, já saneado e pronto para virar Medicao."""
    parametro: str
    valor_nominal: float
    tol_mais: float
    tol_menos: float
    medida1: float
    medida2: float


@dataclass
class EnsaioLido:
    """Resultado completo da leitura de uma planilha."""
    numero_certificado: str
    data_calibracao: str
    temperatura: Optional[float]
    tecnico: str
    solicitante: Optional[str]
    codigo_equipamento: str
    denominacao: str
    fabricante: str
    modelo: str
    padrao_utilizado: Optional[str]
    procedimento: Optional[str]
    incerteza_u: Optional[float]
    fator_k: Optional[float]
    parametros: list[ParametroLido]


def _abrir_planilha(caminho: Path):
    """
    Abre o .xlsx. Tenta openpyxl; se falhar (Strict OOXML), avisa e para.
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise SystemExit(
            "[ERRO] openpyxl não instalado.\n"
            "Execute: pip install openpyxl"
        )
    try:
        return load_workbook(caminho, data_only=True)
    except Exception as exc:
        raise SystemExit(
            f"[ERRO] Não foi possível abrir {caminho.name}: {exc}\n"
            "Se for o template 'Dispositivo_de_controle_1_.xlsx', ele está em "
            "formato Strict OOXML e não é fonte de dados — use o arquivo "
            "preenchido (Planilha_do_Software_com_a_Calibracao_do_Dispositivo.xlsx)."
        )


def _valor_celula(ws, linha: int, coluna: int):
    """Lê uma célula com segurança, devolvendo None se estiver fora do range."""
    try:
        return ws.cell(row=linha, column=coluna).value
    except (IndexError, ValueError):
        return None


def _procurar_cabecalho(ws, alvos: tuple[str, ...], max_linhas: int = 60) -> Optional[int]:
    """
    Procura a linha que contém o cabeçalho da tabela de medição.
    A planilha da Schulz tem cabeçalho na linha 13, mas isso pode variar.
    """
    for linha in range(1, min(ws.max_row, max_linhas) + 1):
        for coluna in range(1, min(ws.max_column, 15) + 1):
            valor = _valor_celula(ws, linha, coluna)
            if valor and str(valor).strip().lower() in alvos:
                return linha
    return None


def _mapear_colunas(ws, linha_cabecalho: int) -> dict[str, int]:
    """
    Mapeia nome de coluna -> índice, tolerando variações de grafia.
    """
    sinonimos = {
        "parametro": ("characteristic", "parametro avaliado", "parametro", "titulo"),
        "nominal": ("nominal", "valor nominal"),
        "tol_mais": ("upper tol", "tol. +", "tol +", "+tol", "tol_mais"),
        "tol_menos": ("lower tol", "tol. -", "tol -", "-tol", "tol_menos"),
        "medida1": ("actual", "medida 1", "meas 1", "medida1"),
        "medida2": ("medida 2", "meas 2", "medida2"),
    }
    mapa: dict[str, int] = {}
    for coluna in range(1, min(ws.max_column, 20) + 1):
        valor = _valor_celula(ws, linha_cabecalho, coluna)
        if not valor:
            continue
        texto = str(valor).strip().lower()
        for chave, opcoes in sinonimos.items():
            if chave in mapa:
                continue
            if texto in opcoes:
                mapa[chave] = coluna
    return mapa


def _ler_cabecalho_ensaio(ws, log: LogSaneamento) -> dict:
    """
    Lê os campos de identificação do ensaio (topo da aba Registro/Report).
    Percorre as primeiras 30 linhas procurando rótulos conhecidos.
    """
    rotulos = {
        "data": ("data:", "date"),
        "temperatura": ("temperatura ambiente:", "temperatura"),
        "solicitante": ("cliente solicitante:", "cliente", "solicitante"),
        "tecnico": ("técnico executante:", "tecnico executante:", "metrologista"),
        "codigo": ("código:", "codigo:", "part no."),
        "denominacao": ("denominação:", "denominacao:", "measurement plan"),
        "fabricante": ("fabricante:",),
        "padrao": ("padrão utilizado:", "padrao utilizado:"),
        "procedimento": ("procedimento:",),
        "numero": ("certificado de calibração nº", "certificado nº", "nº"),
    }
    achados: dict = {}
    for linha in range(1, min(ws.max_row, 40) + 1):
        for coluna in range(1, min(ws.max_column, 15) + 1):
            valor = _valor_celula(ws, linha, coluna)
            if not valor:
                continue
            texto = str(valor).strip().lower()
            for chave, opcoes in rotulos.items():
                if chave in achados:
                    continue
                if any(texto.startswith(op) for op in opcoes):
                    # valor está na célula à direita
                    vizinho = _valor_celula(ws, linha, coluna + 1)
                    if vizinho is not None:
                        achados[chave] = vizinho
    return achados


def ler_planilha(caminho: Path, log: LogSaneamento) -> EnsaioLido:
    """
    Lê uma planilha de calibração da Schulz e devolve o ensaio saneado.

    Estratégia:
      1. Localiza o cabeçalho da tabela de medição (linha 13 no arquivo real).
      2. Lê os campos de identificação do topo.
      3. Lê os parâmetros. Se houver DOIS blocos (Medida 1 e Medida 2),
         combina-os por nome de parâmetro.
    """
    wb = _abrir_planilha(caminho)

    # Prefere a aba 'Registro'; cai para 'Report' se não existir
    aba = None
    for nome in ("Registro", "Report"):
        if nome in wb.sheetnames:
            aba = wb[nome]
            break
    if aba is None:
        raise SystemExit(
            f"[ERRO] {caminho.name} não tem aba 'Registro' nem 'Report'."
        )

    cabecalho_ensaio = _ler_cabecalho_ensaio(aba, log)

    linha_cab = _procurar_cabecalho(
        aba, ("characteristic", "parametro avaliado", "parâmetro avaliado")
    )
    if linha_cab is None:
        raise SystemExit(
            f"[ERRO] Cabeçalho da tabela de medição não encontrado em "
            f"{caminho.name}. Esperado 'Characteristic' ou 'Parâmetro avaliado'."
        )

    colunas = _mapear_colunas(aba, linha_cab)
    obrigatorias = ("parametro", "nominal", "tol_mais", "tol_menos")
    faltando = [c for c in obrigatorias if c not in colunas]
    if faltando:
        raise SystemExit(
            f"[ERRO] Colunas obrigatórias ausentes em {caminho.name}: {faltando}.\n"
            f"Colunas encontradas: {list(colunas)}"
        )

    # ---- Lê todas as linhas de dados, separando por bloco ----
    blocos: list[dict[str, dict]] = [{}]
    ultimo_parametro = None
    for linha in range(linha_cab + 1, aba.max_row + 1):
        nome = limpar_texto(
            _valor_celula(aba, linha, colunas["parametro"]),
            "parametro", log, linha,
        )
        if not nome:
            continue
        # Detecta reinício do bloco: parâmetro repetido
        if nome in blocos[-1]:
            blocos.append({})
        blocos[-1][nome] = {
            "linha": linha,
            "nominal": limpar_numero(
                _valor_celula(aba, linha, colunas["nominal"]), "nominal", log, linha),
            "tol_mais": limpar_numero(
                _valor_celula(aba, linha, colunas["tol_mais"]), "tol_mais", log, linha),
            "tol_menos": limpar_numero(
                _valor_celula(aba, linha, colunas["tol_menos"]), "tol_menos", log, linha),
            "medida": limpar_numero(
                _valor_celula(aba, linha, colunas.get("medida1", 0)),
                "medida", log, linha),
        }
        ultimo_parametro = nome

    if not blocos[0]:
        raise SystemExit(f"[ERRO] Nenhum parâmetro encontrado em {caminho.name}.")

    # ---- Combina os blocos em ParametroLido ----
    parametros: list[ParametroLido] = []
    for nome, dados in blocos[0].items():
        medida1 = dados["medida"]
        medida2 = None
        if len(blocos) > 1 and nome in blocos[1]:
            medida2 = blocos[1][nome]["medida"]

        # Se só há um bloco, tenta a coluna 'medida2' da mesma linha
        if medida2 is None and "medida2" in colunas:
            medida2 = limpar_numero(
                _valor_celula(aba, dados["linha"], colunas["medida2"]),
                "medida2", log, dados["linha"],
            )

        if None in (dados["nominal"], dados["tol_mais"], dados["tol_menos"],
                    medida1, medida2):
            log.registrar("Parâmetro descartado (dado essencial ausente)",
                          nome, None, None, dados["linha"])
            continue

        parametros.append(ParametroLido(
            parametro=nome,
            valor_nominal=dados["nominal"],
            tol_mais=normalizar_tolerancia(dados["tol_mais"], "tol_mais", log, dados["linha"]),
            tol_menos=normalizar_tolerancia(dados["tol_menos"], "tol_menos", log, dados["linha"]),
            medida1=medida1,
            medida2=medida2,
        ))

    if not parametros:
        raise SystemExit(
            f"[ERRO] Nenhum parâmetro válido após saneamento em {caminho.name}."
        )

    # ---- Campos de identificação ----
    data_iso = normalizar_data(cabecalho_ensaio.get("data"), log) or date.today().isoformat()
    tecnico = limpar_texto(cabecalho_ensaio.get("tecnico"), "tecnico", log) or "NAO INFORMADO"
    solicitante = limpar_texto(cabecalho_ensaio.get("solicitante"), "solicitante", log)
    codigo = limpar_texto(cabecalho_ensaio.get("codigo"), "codigo", log) or "SEM-CODIGO"
    denominacao = limpar_texto(
        cabecalho_ensaio.get("denominacao"), "denominacao", log
    ) or "Dispositivo de controle"
    fabricante = limpar_texto(
        cabecalho_ensaio.get("fabricante"), "fabricante", log
    ) or "Nao consta"

    # Número do certificado: usa o da planilha ou gera sequencial
    numero = limpar_texto(cabecalho_ensaio.get("numero"), "numero", log)
    if not numero:
        numero = f"{datetime.now():%Y%m%d%H%M%S}"

    return EnsaioLido(
        numero_certificado=numero,
        data_calibracao=data_iso,
        temperatura=limpar_numero(cabecalho_ensaio.get("temperatura"), "temperatura", log),
        tecnico=tecnico,
        solicitante=solicitante,
        codigo_equipamento=codigo,
        denominacao=denominacao,
        fabricante=fabricante,
        modelo=limpar_texto(cabecalho_ensaio.get("modelo"), "modelo", log) or "Nao consta",
        padrao_utilizado=limpar_texto(cabecalho_ensaio.get("padrao"), "padrao", log),
        procedimento=limpar_texto(cabecalho_ensaio.get("procedimento"), "procedimento", log),
        incerteza_u=None,   # preenchido pelo chamador, se disponível
        fator_k=None,
        parametros=parametros,
    )


# =====================================================================
# 4. PERSISTÊNCIA (ETL -> SQLite)
# =====================================================================
def _obter_ou_criar_tecnico(dao: TecnicoDAO, nome: str, papel: str,
                            setor: str) -> Tecnico:
    """Idempotência: reaproveita o técnico se já existir pelo nome."""
    for t in dao.listar():
        if t.nome.strip().lower() == nome.strip().lower():
            return t
    novo = Tecnico(nome=nome, papel=papel, nome_setor=setor)
    return dao.inserir(novo)


def _obter_ou_criar_equipamento(dao: EquipamentoDAO, codigo: str,
                                denominacao: str, fabricante: str,
                                modelo: str) -> Equipamento:
    existente = dao.buscar_por_codigo(codigo)
    if existente:
        return existente
    novo = Equipamento(
        codigo=codigo, denominacao=denominacao,
        fabricante=fabricante, modelo=modelo, categoria="Dimensional",
    )
    return dao.inserir(novo)


def gravar_ensaio(ensaio: EnsaioLido, caminho_db: str = DB_PADRAO) -> dict:
    """
    Grava o ensaio completo no SQLite dentro de UMA transação lógica:
    técnico -> equipamento -> certificado -> N medições -> status consolidado.
    """
    tecnico_dao = TecnicoDAO(caminho_db)
    equip_dao = EquipamentoDAO(caminho_db)
    cert_dao = CertificadoDAO(caminho_db)
    medicao_dao = MedicaoDAO(caminho_db)

    tecnico = _obter_ou_criar_tecnico(
        tecnico_dao, ensaio.tecnico, "TECNICO", "Metrologia"
    )
    solicitante = None
    if ensaio.solicitante:
        solicitante = _obter_ou_criar_tecnico(
            tecnico_dao, ensaio.solicitante, "SOLICITANTE", "Usinagem I"
        )

    equipamento = _obter_ou_criar_equipamento(
        equip_dao, ensaio.codigo_equipamento, ensaio.denominacao,
        ensaio.fabricante, ensaio.modelo,
    )

    certificado = Certificado(
        numero=ensaio.numero_certificado,
        id_equipamento=equipamento.id_equipamento,
        id_tecnico=tecnico.id_tecnico,
        id_solicitante=solicitante.id_tecnico if solicitante else None,
        data_calibracao=ensaio.data_calibracao,
        temperatura=ensaio.temperatura,
        padrao_utilizado=ensaio.padrao_utilizado,
        procedimento=ensaio.procedimento,
        incerteza_u=ensaio.incerteza_u,
        fator_k=ensaio.fator_k,
    )
    cert_dao.inserir(certificado)

    for p in ensaio.parametros:
        medicao = Medicao(
            id_certificado=certificado.id_certificado,
            id_equipamento=equipamento.id_equipamento,
            id_tecnico=tecnico.id_tecnico,
            parametro=p.parametro,
            valor_nominal=p.valor_nominal,
            tol_mais=p.tol_mais,
            tol_menos=p.tol_menos,
            medida1=p.medida1,
            medida2=p.medida2,
            data_medicao=ensaio.data_calibracao,
        )
        medicao_dao.inserir(medicao)

    status_final = cert_dao.recalcular_status(certificado.id_certificado)

    return {
        "id_certificado": certificado.id_certificado,
        "numero": certificado.numero,
        "status": status_final,
        "total_parametros": len(ensaio.parametros),
    }


# =====================================================================
# 5. EMISSÃO DO CERTIFICADO
# =====================================================================
def emitir_certificado(id_certificado: int, caminho_db: str = DB_PADRAO) -> Path:
    """
    Consulta o certificado consolidado (JOIN) e grava o documento .txt
    em /certificados. Devolve o caminho do arquivo gerado.
    """
    cert_dao = CertificadoDAO(caminho_db)
    dados = cert_dao.certificado_completo(id_certificado)
    cab = dados["cabecalho"]
    medicoes = dados["medicoes"]

    PASTA_SAIDA.mkdir(exist_ok=True)
    numero_arquivo = re.sub(r"[^0-9A-Za-z_-]", "_", cab["numero"])
    destino = PASTA_SAIDA / f"certificado_{numero_arquivo}.txt"

    largura = 96
    linhas: list[str] = []
    linhas.append("=" * largura)
    linhas.append("CERTIFICADO DE CALIBRAÇÃO".center(largura))
    linhas.append("SCHULZ S.A. — LABORATÓRIO DE METROLOGIA".center(largura))
    linhas.append("=" * largura)
    linhas.append(f"Certificado nº: {cab['numero']}")
    linhas.append(f"Data da calibração: {_data_br(cab['data_calibracao'])}")
    if cab.get("temperatura") is not None:
        linhas.append(f"Temperatura ambiente: {cab['temperatura']:.1f} °C")
    linhas.append("")
    linhas.append("1. DESCRIÇÃO DO INSTRUMENTO CALIBRADO")
    linhas.append(f"   Denominação : {cab['denominacao']}")
    linhas.append(f"   Código      : {cab['codigo']}")
    linhas.append(f"   Fabricante  : {cab['fabricante']}")
    linhas.append(f"   Modelo      : {cab['modelo']}")
    linhas.append("")
    linhas.append("2. PADRÃO UTILIZADO")
    linhas.append(f"   {cab.get('padrao_utilizado') or 'Não informado'}")
    linhas.append("")
    linhas.append("3. PROCEDIMENTO DE CALIBRAÇÃO")
    linhas.append(f"   {cab.get('procedimento') or 'Não informado'}")
    linhas.append("")
    linhas.append("4. RESPONSÁVEIS")
    linhas.append(f"   Técnico executante : {cab['tecnico']}")
    if cab.get("solicitante"):
        linhas.append(f"   Solicitante        : {cab['solicitante']}")
    linhas.append("")
    linhas.append("5. RESULTADOS (mm)")
    linhas.append("-" * largura)
    linhas.append(
        f"{'PARÂMETRO':<24}{'NOMINAL':>10}{'TOL +':>9}{'TOL -':>9}"
        f"{'OBTIDO':>12}{'ERRO':>12}{'STATUS':>12}"
    )
    linhas.append("-" * largura)
    for m in medicoes:
        erro = m["media"] - m["valor_nominal"]
        linhas.append(
            f"{m['parametro'][:23]:<24}"
            f"{m['valor_nominal']:>10.4f}"
            f"{m['tol_mais']:>9.4f}"
            f"{m['tol_menos']:>9.4f}"
            f"{m['media']:>12.6f}"
            f"{erro:>+12.6f}"
            f"{m['status']:>12}"
        )
    linhas.append("-" * largura)
    if cab.get("incerteza_u") is not None:
        linhas.append(
            f"Incerteza de medição: U = {cab['incerteza_u']:.4f} mm "
            f"(k = {cab.get('fator_k') or 2})"
        )
    linhas.append("")
    linhas.append("6. RESULTADO FINAL")
    linhas.append(f"   STATUS DO DISPOSITIVO: {cab['status_certificado']}")
    aprovados = sum(1 for m in medicoes if m["status"] == "APROVADO")
    linhas.append(
        f"   Parâmetros avaliados: {len(medicoes)} | "
        f"Aprovados: {aprovados} | Reprovados: {len(medicoes) - aprovados}"
    )
    linhas.append("")
    linhas.append("7. OBSERVAÇÕES")
    linhas.append(
        "   A incerteza expandida declarada é baseada em um fator de "
        "abrangência k, o que corresponde a uma probabilidade de\n"
        "   abrangência de aproximadamente 95% (EA-4/02). O resultado "
        "aprovado indica que todos os parâmetros avaliados estão\n"
        "   dentro das tolerâncias especificadas."
    )
    linhas.append("=" * largura)

    destino.write_text("\n".join(linhas), encoding="utf-8")
    return destino


def _data_br(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(iso)


def exportar_csv(id_certificado: int, caminho_db: str = DB_PADRAO) -> Path:
    """Exporta os resultados em CSV — evidência para o ZIP da AV04."""
    cert_dao = CertificadoDAO(caminho_db)
    dados = cert_dao.certificado_completo(id_certificado)
    PASTA_SAIDA.mkdir(exist_ok=True)
    numero = re.sub(r"[^0-9A-Za-z_-]", "_", dados["cabecalho"]["numero"])
    destino = PASTA_SAIDA / f"resultados_{numero}.csv"
    with destino.open("w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow([
            "parametro", "valor_nominal", "tol_mais", "tol_menos",
            "medida1", "medida2", "media", "desvio_padrao", "erro", "status",
        ])
        for m in dados["medicoes"]:
            escritor.writerow([
                m["parametro"], m["valor_nominal"], m["tol_mais"], m["tol_menos"],
                m["medida1"], m["medida2"], m["media"], m["desvio_padrao"],
                round(m["media"] - m["valor_nominal"], 6), m["status"],
            ])
    return destino


# =====================================================================
# 6. INICIALIZAÇÃO DO BANCO
# =====================================================================
def inicializar_banco(caminho_db: str = DB_PADRAO, recriar: bool = False) -> str:
    """
    Cria o banco a partir do 03_banco.sql.
    recriar=False preserva o histórico — comportamento correto do MVP final.
    """
    if not SQL_DDL.exists():
        raise SystemExit(f"[ERRO] 03_banco.sql não encontrado em {SQL_DDL}.")

    if recriar and Path(caminho_db).exists():
        Path(caminho_db).unlink()

    novo = not Path(caminho_db).exists()
    script = SQL_DDL.read_text(encoding="utf-8")
    with ConexaoSQLite(caminho_db) as conn:
        conn.executescript(script)

    return "banco criado" if novo else "banco já existia (histórico preservado)"


# =====================================================================
# 7. PIPELINE COMPLETO
# =====================================================================
def processar_planilha(caminho_planilha: Path, caminho_db: str = DB_PADRAO,
                       recriar: bool = False) -> dict:
    """
    Executa o pipeline completo para uma planilha e devolve o resumo.
    É a função que a interface e os testes chamam.
    """
    print(f"\n[1] Inicializando banco: {inicializar_banco(caminho_db, recriar)}")

    print(f"[2] Lendo planilha: {caminho_planilha.name}")
    log = LogSaneamento()
    ensaio = ler_planilha(caminho_planilha, log)
    print(f"    Parâmetros válidos: {len(ensaio.parametros)}")
    print(f"    Técnico: {ensaio.tecnico} | Equipamento: {ensaio.codigo_equipamento}")
    print("    Saneamento aplicado:")
    log.imprimir()

    print("[3] Gravando no SQLite (técnico, equipamento, certificado, medições)")
    resumo = gravar_ensaio(ensaio, caminho_db)
    print(f"    Certificado id={resumo['id_certificado']} | "
          f"nº {resumo['numero']} | {resumo['total_parametros']} medições")

    print("[4] Consolidando status e emitindo certificado")
    arquivo_txt = emitir_certificado(resumo["id_certificado"], caminho_db)
    arquivo_csv = exportar_csv(resumo["id_certificado"], caminho_db)
    print(f"    Certificado: {arquivo_txt.name}")
    print(f"    Resultados : {arquivo_csv.name}")

    resumo["arquivo_txt"] = str(arquivo_txt)
    resumo["arquivo_csv"] = str(arquivo_csv)
    resumo["saneamento"] = log.resumo()
    return resumo


# =====================================================================
# 8. INTERFACE GRÁFICA (tkinter — biblioteca padrão)
# =====================================================================
def abrir_interface(caminho_db: str = DB_PADRAO) -> None:
    """
    Interface simples para o técnico da Schulz: escolher planilha,
    processar, ver o resultado. Sem terminal, sem IDE.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext
    except ImportError:
        print("[AVISO] tkinter indisponível. Use o modo --cli.")
        return modo_cli(caminho_db)

    raiz = tk.Tk()
    raiz.title("Schulz Calibração — Gerador de Certificados")
    raiz.geometry("760x560")

    tk.Label(
        raiz, text="Gerador de Certificados de Calibração",
        font=("Segoe UI", 14, "bold"),
    ).pack(pady=10)

    quadro = tk.Frame(raiz)
    quadro.pack(fill="x", padx=16)

    var_caminho = tk.StringVar()
    tk.Label(quadro, text="Planilha de entrada:").pack(anchor="w")
    linha = tk.Frame(quadro)
    linha.pack(fill="x", pady=4)
    tk.Entry(linha, textvariable=var_caminho).pack(
        side="left", fill="x", expand=True
    )

    def escolher():
        arquivo = filedialog.askopenfilename(
            title="Selecione a planilha de calibração",
            filetypes=[("Planilhas Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")],
        )
        if arquivo:
            var_caminho.set(arquivo)

    tk.Button(linha, text="Procurar...", command=escolher).pack(side="left", padx=6)

    var_recriar = tk.BooleanVar(value=False)
    tk.Checkbutton(
        quadro, text="Recriar banco (apaga o histórico)",
        variable=var_recriar,
    ).pack(anchor="w", pady=4)

    saida = scrolledtext.ScrolledText(raiz, height=20, font=("Consolas", 9))
    saida.pack(fill="both", expand=True, padx=16, pady=10)

    def processar():
        caminho = var_caminho.get().strip()
        if not caminho:
            messagebox.showwarning("Atenção", "Selecione uma planilha primeiro.")
            return
        saida.delete("1.0", "end")
        try:
            resumo = processar_planilha(
                Path(caminho), caminho_db, recriar=var_recriar.get()
            )
            saida.insert("end", f"STATUS DO DISPOSITIVO: {resumo['status']}\n\n")
            saida.insert("end", Path(resumo["arquivo_txt"]).read_text(encoding="utf-8"))
            messagebox.showinfo(
                "Concluído",
                f"Certificado {resumo['numero']} emitido.\n"
                f"Status: {resumo['status']}",
            )
        except SystemExit as exc:
            messagebox.showerror("Erro", str(exc))
        except (ErroValidacao, ErroPersistencia) as exc:
            messagebox.showerror("Erro de domínio", str(exc))
        except Exception as exc:
            messagebox.showerror("Erro inesperado", f"{type(exc).__name__}: {exc}")

    tk.Button(
        raiz, text="Processar e emitir certificado",
        command=processar, bg="#1f6feb", fg="white",
        font=("Segoe UI", 10, "bold"), height=2,
    ).pack(fill="x", padx=16, pady=(0, 14))

    raiz.mainloop()


# =====================================================================
# 9. MODO CLI
# =====================================================================
def modo_cli(caminho_db: str = DB_PADRAO, planilha: Optional[str] = None,
             recriar: bool = False) -> int:
    if planilha:
        caminho = Path(planilha)
    else:
        print("Planilhas .xlsx encontradas nesta pasta:")
        candidatos = sorted(PASTA.glob("*.xlsx"))
        for i, c in enumerate(candidatos, 1):
            print(f"  {i}. {c.name}")
        if not candidatos:
            print("  (nenhuma)")
            return 1
        escolha = input("\nNúmero da planilha (ou caminho completo): ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(candidatos):
            caminho = candidatos[int(escolha) - 1]
        else:
            caminho = Path(escolha)

    if not caminho.exists():
        print(f"[ERRO] Arquivo não encontrado: {caminho}")
        return 1

    try:
        resumo = processar_planilha(caminho, caminho_db, recriar=recriar)
    except (ErroValidacao, ErroPersistencia) as exc:
        print(f"\n[ERRO DE DOMÍNIO] {exc}")
        return 1

    print("\n" + "=" * 70)
    print(f"RESULTADO FINAL: {resumo['status']}")
    print("=" * 70)
    print(Path(resumo["arquivo_txt"]).read_text(encoding="utf-8"))
    return 0


# =====================================================================
# 10. AUTOTESTE (evidência para o plano de testes do 08)
# =====================================================================
def autoteste() -> int:
    """
    Executa os casos de teste do plano de testes e imprime o resultado.
    Não depende de planilha externa: usa dados sintéticos.
    """
    print("=" * 70)
    print("AUTOTESTE — 07_gerador_certificado.py")
    print("=" * 70)
    falhas = 0

    def checar(nome: str, condicao: bool, detalhe: str = ""):
        nonlocal falhas
        marca = "OK  " if condicao else "FALHA"
        print(f"[{marca}] {nome}" + (f" — {detalhe}" if detalhe else ""))
        if not condicao:
            falhas += 1

    log = LogSaneamento()

    # CT01 — acentuação normalizada
    r = limpar_texto("62P_DIÂMETRO 1", "parametro", log)
    checar("CT01 acento removido", r == "62P_DIAMETRO 1", repr(r))

    # CT02 — placeholder descartado
    r = limpar_texto("???", "campo", log)
    checar("CT02 placeholder vira None", r is None, repr(r))

    # CT03 — vírgula decimal
    r = limpar_numero("6,0787295", "medida", log)
    checar("CT03 vírgula decimal", r == 6.0787295, repr(r))

    # CT04 — tolerância negativa normalizada
    r = normalizar_tolerancia(-0.01, "tol_menos", log)
    checar("CT04 tol_menos absoluto", r == 0.01, repr(r))

    # CT05 — data ISO
    r = normalizar_data("26/08/2026", log)
    checar("CT05 data BR -> ISO", r == "2026-08-26", repr(r))

    # CT06 — data placeholder rejeitada
    r = normalizar_data("00/00/0000", log)
    checar("CT06 data placeholder rejeitada", r is None, repr(r))

    # CT07 — classificação no limite exato (APROVADO)
    m = Medicao(
        id_equipamento=1, id_tecnico=1, parametro="TESTE",
        valor_nominal=50.0, tol_mais=0.05, tol_menos=0.05,
        medida1=50.05, medida2=50.05,
    )
    checar("CT07 limite superior exato = APROVADO", m.status == "APROVADO", m.status)

    # CT08 — classificação acima do limite (REPROVADO)
    m = Medicao(
        id_equipamento=1, id_tecnico=1, parametro="TESTE",
        valor_nominal=50.0, tol_mais=0.05, tol_menos=0.05,
        medida1=50.06, medida2=50.06,
    )
    checar("CT08 acima do limite = REPROVADO", m.status == "REPROVADO", m.status)

    # CT09 — consolidação: uma reprovação reprova o dispositivo
    r = Certificado.consolidar_status(["APROVADO", "APROVADO", "REPROVADO"])
    checar("CT09 consolidado com 1 reprovado", r == "REPROVADO", r)

    # CT10 — consolidação: todos aprovados
    r = Certificado.consolidar_status(["APROVADO"] * 14)
    checar("CT10 consolidado todos aprovados", r == "APROVADO", r)

    # CT11 — consolidação sem medições é erro
    try:
        Certificado.consolidar_status([])
        checar("CT11 consolidar vazio levanta erro", False, "não levantou")
    except ErroValidacao:
        checar("CT11 consolidar vazio levanta erro", True)

    # CT12 — medição incompleta bloqueada (RN01)
    try:
        Medicao(
            id_equipamento=1, id_tecnico=1, parametro="TESTE",
            valor_nominal=50.0, tol_mais=0.05, tol_menos=0.05,
            medida1=50.0, medida2=" ",
        )
        checar("CT12 medida vazia bloqueada", False, "não levantou")
    except ErroValidacao:
        checar("CT12 medida vazia bloqueada", True)

    print("-" * 70)
    print(f"Total: 12 casos | Falhas: {falhas}")
    print("=" * 70)
    return 0 if falhas == 0 else 1


# =====================================================================
# 11. PONTO DE ENTRADA
# =====================================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gerador de Certificados de Calibração — Schulz S.A."
    )
    parser.add_argument("--cli", action="store_true", help="modo terminal")
    parser.add_argument("--planilha", help="caminho da planilha .xlsx")
    parser.add_argument("--db", default=DB_PADRAO, help="caminho do banco SQLite")
    parser.add_argument("--recriar", action="store_true",
                        help="apaga o banco antes de processar")
    parser.add_argument("--selftest", action="store_true",
                        help="executa os testes automáticos")
    args = parser.parse_args()

    if args.selftest:
        return autoteste()
    if args.cli or args.planilha:
        return modo_cli(args.db, args.planilha, args.recriar)
    abrir_interface(args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
