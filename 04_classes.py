"""
04_classes.py
Projeto Aplicado I — AV03 (MVP Parte 1) | Empresa parceira: Schulz S.A.
Equipe: Marx Braga Camilo, Gladson Goulart, Carla Tayna, Yorman Hernandez

Camadas deste módulo:
  1. Exceções de domínio
  2. Classes de domínio (Tecnico, Equipamento, Medicao)
  3. Conexão e persistência (ConexaoSQLite, DAOs, migração da matrícula)
"""

from __future__ import annotations

import math
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from statistics import stdev
from typing import Optional

# Espelham as restrições CHECK do 03_banco.sql
PAPEIS_VALIDOS = ("TECNICO", "SOLICITANTE")
STATUS_VALIDOS = ("APROVADO", "REPROVADO")


# =====================================================================
# 1. Exceções de domínio
# =====================================================================
class ErroValidacao(Exception):
    """Regra de negócio violada na camada de domínio."""


class ErroPersistencia(Exception):
    """Falha na comunicação com o banco SQLite."""


# =====================================================================
# Funções de validação compartilhadas pelas classes de domínio
# =====================================================================
def _texto_obrigatorio(valor, campo: str) -> str:
    if valor is None or not str(valor).strip():
        raise ErroValidacao(f"O campo '{campo}' é obrigatório.")
    return str(valor).strip()


def _texto_opcional(valor) -> Optional[str]:
    """Texto nullable: vazio ou None vira None."""
    if valor is None or not str(valor).strip():
        return None
    return str(valor).strip()


def _inteiro(valor, campo: str) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ErroValidacao(
            f"'{campo}' deve ser um número inteiro. Recebido: {valor!r}."
        ) from exc


def _numero_finito(valor, campo: str) -> float:
    try:
        numero = float(str(valor).replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise ErroValidacao(
            f"'{campo}' deve ser numérico. Recebido: {valor!r}."
        ) from exc
    if not math.isfinite(numero):
        raise ErroValidacao(f"'{campo}' deve ser um número finito. Recebido: {valor!r}.")
    return numero


def _dec(valor: float) -> Decimal:
    """Converte float em Decimal (6 casas) para comparações sem ruído binário."""
    return Decimal(str(round(valor, 6)))


# =====================================================================
# 2.1 CLASSE TECNICO
# =====================================================================
class Tecnico:
    """
    Representa a tabela `tecnico`: metrologistas executantes e
    solicitantes (clientes internos dos setores da Schulz).

    Encapsulamento: atributos privados, acesso por @property. A validação
    ocorre no construtor e nos setters, então o objeto nunca fica inválido.
    """

    def __init__(
        self,
        nome: str,
        papel: str,
        nome_setor: str,
        id_tecnico: Optional[int] = None,
        matricula: Optional[str] = None,
    ):
        self._id_tecnico = id_tecnico
        self._nome = _texto_obrigatorio(nome, "nome")
        self._papel = self._validar_papel(papel)
        self._nome_setor = _texto_obrigatorio(nome_setor, "nome_setor")
        self._matricula = _texto_opcional(matricula)

    @staticmethod
    def _validar_papel(papel) -> str:
        papel = str(papel or "").strip().upper()
        if papel not in PAPEIS_VALIDOS:
            raise ErroValidacao(
                f"O papel deve ser um de {PAPEIS_VALIDOS}. Recebido: '{papel}'."
            )
        return papel

    # ------------------------- encapsulamento -------------------------
    @property
    def id_tecnico(self) -> Optional[int]:
        return self._id_tecnico

    @id_tecnico.setter
    def id_tecnico(self, valor):
        if self._id_tecnico is not None:
            raise ErroValidacao("id_tecnico já definido e não pode ser alterado.")
        self._id_tecnico = _inteiro(valor, "id_tecnico")

    @property
    def nome(self) -> str:
        return self._nome

    @nome.setter
    def nome(self, valor):
        self._nome = _texto_obrigatorio(valor, "nome")

    @property
    def papel(self) -> str:
        return self._papel

    @property
    def nome_setor(self) -> str:
        return self._nome_setor

    @nome_setor.setter
    def nome_setor(self, valor):
        self._nome_setor = _texto_obrigatorio(valor, "nome_setor")

    @property
    def setor(self) -> str:
        """Alias de nome_setor (o roteiro da AV03 cita 'setor')."""
        return self._nome_setor

    @property
    def matricula(self) -> Optional[str]:
        return self._matricula

    @matricula.setter
    def matricula(self, valor):
        self._matricula = _texto_opcional(valor)

    def __repr__(self) -> str:
        return (
            f"Tecnico(id={self._id_tecnico}, nome='{self._nome}', "
            f"matricula={self._matricula!r}, papel='{self._papel}', "
            f"setor='{self._nome_setor}')"
        )


# =====================================================================
# 2.2 CLASSE EQUIPAMENTO
# =====================================================================
class Equipamento:
    """Representa a tabela `equipamento`: dispositivos de controle."""

    def __init__(
        self,
        codigo: str,
        denominacao: str,
        fabricante: str,
        modelo: str,
        categoria: Optional[str] = None,
        id_equipamento: Optional[int] = None,
    ):
        self._id_equipamento = id_equipamento
        self._codigo = _texto_obrigatorio(codigo, "codigo")
        self._denominacao = _texto_obrigatorio(denominacao, "denominacao")
        self._fabricante = _texto_obrigatorio(fabricante, "fabricante")
        self._modelo = _texto_obrigatorio(modelo, "modelo")
        self._categoria = _texto_opcional(categoria)  # nullable no DDL

    @property
    def id_equipamento(self) -> Optional[int]:
        return self._id_equipamento

    @id_equipamento.setter
    def id_equipamento(self, valor):
        if self._id_equipamento is not None:
            raise ErroValidacao("id_equipamento já definido e não pode ser alterado.")
        self._id_equipamento = _inteiro(valor, "id_equipamento")

    @property
    def codigo(self) -> str:
        return self._codigo

    @codigo.setter
    def codigo(self, valor):
        self._codigo = _texto_obrigatorio(valor, "codigo")

    @property
    def denominacao(self) -> str:
        return self._denominacao

    @denominacao.setter
    def denominacao(self, valor):
        self._denominacao = _texto_obrigatorio(valor, "denominacao")

    @property
    def fabricante(self) -> str:
        return self._fabricante

    @property
    def modelo(self) -> str:
        return self._modelo

    @property
    def categoria(self) -> Optional[str]:
        return self._categoria

    # ---- aliases de compatibilidade com o roteiro da AV03 ----
    @property
    def codigo_tag(self) -> str:
        return self._codigo

    @property
    def descricao(self) -> str:
        return self._denominacao

    def __repr__(self) -> str:
        return (
            f"Equipamento(id={self._id_equipamento}, codigo='{self._codigo}', "
            f"denominacao='{self._denominacao}')"
        )


# =====================================================================
# 2.3 CLASSE MEDICAO — coração das regras metrológicas
# =====================================================================
class Medicao:
    """
    Encapsula o ensaio de calibração. Média, desvio padrão, erro e status
    são sempre CALCULADOS pela classe, nunca informados de fora.
    """

    def __init__(
        self,
        id_equipamento: int,
        id_tecnico: int,
        parametro: str,
        valor_nominal: float,
        tol_mais: float,
        tol_menos: float,
        medida1: float,
        medida2: float,
        id_certificado: Optional[int] = None,
        data_medicao=None,
        id_medicao: Optional[int] = None,
    ):
        self._id_medicao = id_medicao
        self._id_certificado = (_inteiro(id_certificado, "id_certificado")
            if id_certificado is not None else None
        )
        self._id_equipamento = _inteiro(id_equipamento, "id_equipamento")
        self._id_tecnico = _inteiro(id_tecnico, "id_tecnico")
        self._parametro = _texto_obrigatorio(parametro, "parametro")
        self._valor_nominal = _numero_finito(valor_nominal, "valor_nominal")    
        self._tol_mais = abs(_numero_finito(tol_mais, "tol_mais"))
        self._tol_menos = abs(_numero_finito(tol_menos, "tol_menos"))
        self._medida1 = self._validar_medida(medida1, "medida1")
        self._medida2 = self._validar_medida(medida2, "medida2")
        self._data_medicao = self._validar_data(data_medicao)

        # -------- campos derivados (calculados, nunca informados) --------
        self._media = (self._medida1 + self._medida2) / 2
        # stdev = desvio padrão AMOSTRAL (n-1), convenção da planilha da AV01
        self._desvio_padrao = stdev([self._medida1, self._medida2])
        self._status = self.classificar()

    # ------------------------- validações -------------------------
    @staticmethod
    def _validar_medida(valor, campo: str) -> float:
        if valor is None or not str(valor).strip():
            raise ErroValidacao(
                f"Medição pendente: '{campo}' é obrigatória e não pode ser vazia."
            )
        return _numero_finito(valor, campo)

    @staticmethod
    def _validar_data(valor) -> str:
        if valor is None or str(valor).strip() == "":
            return date.today().isoformat()
        if isinstance(valor, (date, datetime)):
            return valor.strftime("%Y-%m-%d")
        texto = str(valor).strip()
        if texto in ("00/00/0000", "???"):
            raise ErroValidacao(f"Data inválida recebida: {texto!r}.")
        try:
            return datetime.strptime(texto, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError as exc:
            raise ErroValidacao(
                f"Data deve estar no formato ISO (AAAA-MM-DD). Recebido: {texto!r}."
            ) from exc

    # ------------------------- regra de negócio -------------------------
    def classificar(self) -> str:
        """APROVADO se a média está no intervalo FECHADO [nominal-tol-, nominal+tol+]."""
        limite_inferior = _dec(self._valor_nominal) - _dec(abs(self._tol_menos))
        limite_superior = _dec(self._valor_nominal) + _dec(abs(self._tol_mais))
        return (
            "APROVADO"
            if limite_inferior <= _dec(self._media) <= limite_superior
            else "REPROVADO"
        )

    # ------------------------- encapsulamento -------------------------
    @property
    def id_medicao(self) -> Optional[int]:
        return self._id_medicao

    @id_medicao.setter
    def id_medicao(self, valor):
        if self._id_medicao is not None:
            raise ErroValidacao("id_medicao já definido e não pode ser alterado.")
        self._id_medicao = _inteiro(valor, "id_medicao")

    @property
    def id_certificado(self) -> Optional[int]:
        return self._id_certificado

    @property
    def id_equipamento(self) -> int:
        return self._id_equipamento

    @property
    def id_tecnico(self) -> int:
        return self._id_tecnico

    @property
    def parametro(self) -> str:
        return self._parametro

    @property
    def valor_nominal(self) -> float:
        return self._valor_nominal

    @property
    def tol_mais(self) -> float:
        return self._tol_mais

    @property
    def tol_menos(self) -> float:
        return self._tol_menos

    @property
    def medida1(self) -> float:
        return self._medida1

    @property
    def medida2(self) -> float:
        return self._medida2

    @property
    def media(self) -> float:
        """Valor obtido do ensaio."""
        return self._media

    @property
    def valor_obtido(self) -> float:
        """Alias de media, conforme redação do roteiro da AV03."""
        return self._media

    @property
    def erro(self) -> float:
        """Erro de medição (RN07): valor obtido menos valor nominal."""
        return self._media - self._valor_nominal

    @property
    def desvio_padrao(self) -> float:
        return self._desvio_padrao

    @property
    def status(self) -> str:
        return self._status

    @property
    def data_medicao(self) -> str:
        return self._data_medicao

    @property
    def data_medicao_br(self) -> str:
        return datetime.strptime(self._data_medicao, "%Y-%m-%d").strftime("%d/%m/%Y")

    def __repr__(self) -> str:
        return (
            f"Medicao(id={self._id_medicao}, parametro='{self._parametro}', "
            f"media={self._media:.3f}, status='{self._status}')"
        )


# =====================================================================
# 3.1 CONEXÃO COM O SQLITE
# =====================================================================
class ConexaoSQLite:
    """Gerenciador de contexto: commit em sucesso, rollback em exceção."""

    def __init__(self, caminho_db: str = "schulz_calibracao.db"):
        self.caminho_db = caminho_db
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        try:
            self._conn = sqlite3.connect(self.caminho_db)
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.row_factory = sqlite3.Row
        except sqlite3.Error as exc:
            if self._conn is not None:
                self._conn.close()
            raise ErroPersistencia(
                f"Não foi possível abrir o banco '{self.caminho_db}': {exc}"
            ) from exc
        return self._conn

    def __exit__(self, tipo_exc, valor_exc, traceback):
        try:
            if tipo_exc is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        except sqlite3.Error as exc:
            raise ErroPersistencia(f"Falha ao finalizar a transação: {exc}") from exc
        finally:
            self._conn.close()
        return False  # não suprime a exceção


def garantir_coluna_matricula(caminho_db: str = "schulz_calibracao.db") -> bool:
    
    try:
        with ConexaoSQLite(caminho_db) as conn:
            colunas = [l["name"] for l in conn.execute("PRAGMA table_info(tecnico);")]
            if not colunas:
                raise ErroPersistencia("Tabela 'tecnico' não encontrada no banco.")
            criada = "matricula" not in colunas
            if criada:
                conn.execute("ALTER TABLE tecnico ADD COLUMN matricula TEXT;")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_tecnico_matricula "
                "ON tecnico(matricula);"
            )
            return criada
    except sqlite3.Error as exc:
        raise ErroPersistencia(f"Erro SQL em MIGRACAO matricula: {exc}") from exc


# =====================================================================
# 3.2 DAO BASE — todo acesso ao banco (escrita e leitura) passa por aqui
# =====================================================================
class _DAOBase:

    def __init__(self, caminho_db: str = "schulz_calibracao.db"):
        self.caminho_db = caminho_db

    def _conectar(self) -> ConexaoSQLite:
        return ConexaoSQLite(self.caminho_db)

    @staticmethod
    def _erro(exc: sqlite3.Error, contexto: str) -> ErroPersistencia:
        return ErroPersistencia(f"Erro SQL em {contexto}: {exc}")

    def _executar(self, sql: str, parametros: tuple, contexto: str) -> tuple[int, int]:
        """INSERT/UPDATE/DELETE. Retorna (lastrowid, rowcount)."""
        try:
            with self._conectar() as conn:
                cur = conn.execute(sql, parametros)
                return cur.lastrowid, cur.rowcount
        except sqlite3.Error as exc:
            raise self._erro(exc, contexto) from exc

    def _consultar(self, sql: str, parametros: tuple, contexto: str) -> list[sqlite3.Row]:
        """SELECT. Qualquer falha do SQLite vira ErroPersistencia."""
        try:
            with self._conectar() as conn:
                return conn.execute(sql, parametros).fetchall()
        except sqlite3.Error as exc:
            raise self._erro(exc, contexto) from exc


# ---------------------------------------------------------------------
# DAO de Tecnico
# ---------------------------------------------------------------------
class TecnicoDAO(_DAOBase):

    @staticmethod
    def _linha_para_objeto(linha: sqlite3.Row) -> Tecnico:
        chaves = linha.keys()
        return Tecnico(
            nome=linha["nome"],
            papel=linha["papel"],
            nome_setor=linha["nome_setor"],
            id_tecnico=linha["id_tecnico"],
            matricula=linha["matricula"] if "matricula" in chaves else None,
        )

    def inserir(self, tecnico: Tecnico) -> Tecnico:
        sql = (
            "INSERT INTO tecnico (nome, papel, nome_setor, matricula) "
            "VALUES (?, ?, ?, ?);"
        )
        novo_id, _ = self._executar(
            sql,
            (tecnico.nome, tecnico.papel, tecnico.nome_setor, tecnico.matricula),
            "INSERT tecnico",
        )
        tecnico.id_tecnico = novo_id
        return tecnico

    def buscar_por_id(self, id_tecnico: int) -> Optional[Tecnico]:
        linhas = self._consultar(
            "SELECT * FROM tecnico WHERE id_tecnico = ?;",
            (id_tecnico,), "SELECT tecnico por id",
        )
        return self._linha_para_objeto(linhas[0]) if linhas else None

    def listar(self) -> list[Tecnico]:
        linhas = self._consultar(
            "SELECT * FROM tecnico ORDER BY nome;", (), "SELECT tecnico (listar)"
        )
        return [self._linha_para_objeto(l) for l in linhas]

    def atualizar(self, tecnico: Tecnico) -> int:
        if tecnico.id_tecnico is None:
            raise ErroValidacao("Não é possível atualizar um técnico sem id.")
        sql = (
            "UPDATE tecnico SET nome = ?, papel = ?, nome_setor = ?, matricula = ? "
            "WHERE id_tecnico = ?;"
        )
        _, linhas_afetadas = self._executar(
            sql,
            (tecnico.nome, tecnico.papel, tecnico.nome_setor,
             tecnico.matricula, tecnico.id_tecnico),
            "UPDATE tecnico",
        )
        return linhas_afetadas

    def excluir(self, id_tecnico: int) -> int:
        """
        DELETE. Com PRAGMA foreign_keys=ON, o banco recusa excluir técnico
        que possua medições (vira ErroPersistencia), preservando o histórico.
        """
        _, linhas_afetadas = self._executar(
            "DELETE FROM tecnico WHERE id_tecnico = ?;",
            (id_tecnico,), "DELETE tecnico",
        )
        return linhas_afetadas


# ---------------------------------------------------------------------
# DAO de Equipamento
# ---------------------------------------------------------------------
class EquipamentoDAO(_DAOBase):

    @staticmethod
    def _linha_para_objeto(linha: sqlite3.Row) -> Equipamento:
        return Equipamento(
            codigo=linha["codigo"],
            denominacao=linha["denominacao"],
            fabricante=linha["fabricante"],
            modelo=linha["modelo"],
            categoria=linha["categoria"],
            id_equipamento=linha["id_equipamento"],
        )

    def inserir(self, equipamento: Equipamento) -> Equipamento:
        sql = (
            "INSERT INTO equipamento (codigo, denominacao, fabricante, modelo, "
            "categoria) VALUES (?, ?, ?, ?, ?);"
        )
        novo_id, _ = self._executar(
            sql,
            (equipamento.codigo, equipamento.denominacao, equipamento.fabricante,
             equipamento.modelo, equipamento.categoria),
            "INSERT equipamento",
        )
        equipamento.id_equipamento = novo_id
        return equipamento

    def buscar_por_id(self, id_equipamento: int) -> Optional[Equipamento]:
        linhas = self._consultar(
            "SELECT * FROM equipamento WHERE id_equipamento = ?;",
            (id_equipamento,), "SELECT equipamento por id",
        )
        return self._linha_para_objeto(linhas[0]) if linhas else None

    def buscar_por_codigo(self, codigo: str) -> Optional[Equipamento]:
        linhas = self._consultar(
            "SELECT * FROM equipamento WHERE codigo = ?;",
            (codigo,), "SELECT equipamento por codigo",
        )
        return self._linha_para_objeto(linhas[0]) if linhas else None

    def listar(self) -> list[Equipamento]:
        linhas = self._consultar(
            "SELECT * FROM equipamento ORDER BY codigo;", (),
            "SELECT equipamento (listar)",
        )
        return [self._linha_para_objeto(l) for l in linhas]

    def atualizar(self, equipamento: Equipamento) -> int:
        if equipamento.id_equipamento is None:
            raise ErroValidacao("Não é possível atualizar um equipamento sem id.")
        sql = (
            "UPDATE equipamento SET codigo = ?, denominacao = ?, fabricante = ?, "
            "modelo = ?, categoria = ? WHERE id_equipamento = ?;"
        )
        _, linhas_afetadas = self._executar(
            sql,
            (equipamento.codigo, equipamento.denominacao, equipamento.fabricante,
             equipamento.modelo, equipamento.categoria, equipamento.id_equipamento),
            "UPDATE equipamento",
        )
        return linhas_afetadas

    def excluir(self, id_equipamento: int) -> int:
        """DELETE. Recusado pelo banco se o equipamento tiver medições (FK)."""
        _, linhas_afetadas = self._executar(
            "DELETE FROM equipamento WHERE id_equipamento = ?;",
            (id_equipamento,), "DELETE equipamento",
        )
        return linhas_afetadas


# ---------------------------------------------------------------------
# DAO de Medicao
# ---------------------------------------------------------------------
class MedicaoDAO(_DAOBase):

    @staticmethod
    def _linha_para_objeto(linha: sqlite3.Row) -> Medicao:
        return Medicao(
            id_equipamento=linha["id_equipamento"],
            id_tecnico=linha["id_tecnico"],
            parametro=linha["parametro"],
            valor_nominal=linha["valor_nominal"],
            tol_mais=linha["tol_mais"],
            tol_menos=linha["tol_menos"],
            medida1=linha["medida1"],
            medida2=linha["medida2"],
            id_certificado=linha["id_certificado"],
            data_medicao=linha["data_medicao"],
            id_medicao=linha["id_medicao"],
        )

    def inserir(self, medicao: Medicao) -> Medicao:
        sql = (
            "INSERT INTO medicao (id_certificado, id_equipamento, id_tecnico, data_medicao, "
            "parametro, valor_nominal, tol_mais, tol_menos, medida1, medida2, "
            "media, desvio_padrao, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
        )
        novo_id, _ = self._executar(
            sql,
            (
                medicao.id_certificado, medicao.id_equipamento, medicao.id_tecnico, 
                medicao.data_medicao,medicao.parametro, medicao.valor_nominal, 
                medicao.tol_mais, medicao.tol_menos, medicao.medida1, medicao.medida2,
                medicao.media, medicao.desvio_padrao, medicao.status,
            ),
            "INSERT medicao",
        )
        medicao.id_medicao = novo_id
        return medicao

    def buscar_por_id(self, id_medicao: int) -> Optional[Medicao]:
        linhas = self._consultar(
            "SELECT * FROM medicao WHERE id_medicao = ?;",
            (id_medicao,), "SELECT medicao por id",
        )
        return self._linha_para_objeto(linhas[0]) if linhas else None

    def listar(self) -> list[Medicao]:
        linhas = self._consultar(
            "SELECT * FROM medicao ORDER BY data_medicao DESC, id_medicao;", (),
            "SELECT medicao (listar)",
        )
        return [self._linha_para_objeto(l) for l in linhas]

    def atualizar_medidas(self, id_medicao: int, medida1: float,
                          medida2: float) -> Medicao:
        """
        Reescreve as leituras e RECALCULA média, desvio padrão e status.
        A regra de negócio permanece na classe Medicao.
        """
        original = self.buscar_por_id(id_medicao)
        if original is None:
            raise ErroValidacao(f"Medição {id_medicao} não encontrada.")

        recalculada = Medicao(
            id_equipamento=original.id_equipamento,
            id_tecnico=original.id_tecnico,
            parametro=original.parametro,
            valor_nominal=original.valor_nominal,
            tol_mais=original.tol_mais,
            tol_menos=original.tol_menos,
            medida1=medida1,
            medida2=medida2,
            data_medicao=original.data_medicao,
            id_medicao=original.id_medicao,
        )

        sql = (
            "UPDATE medicao SET medida1 = ?, medida2 = ?, media = ?, "
            "desvio_padrao = ?, status = ? WHERE id_medicao = ?;"
        )
        _, linhas_afetadas = self._executar(
            sql,
            (recalculada.medida1, recalculada.medida2, recalculada.media,
             recalculada.desvio_padrao, recalculada.status, recalculada.id_medicao),
            "UPDATE medicao",
        )
        if linhas_afetadas == 0:
            raise ErroPersistencia(
                f"Erro SQL em UPDATE medicao: nenhuma linha afetada (id={id_medicao})."
            )
        return recalculada

    def excluir(self, id_medicao: int) -> int:
        """DELETE de uma medição. Retorna o número de linhas removidas."""
        _, linhas_afetadas = self._executar(
            "DELETE FROM medicao WHERE id_medicao = ?;",
            (id_medicao,), "DELETE medicao",
        )
        return linhas_afetadas

    def relatorio_calibracoes(self) -> list[sqlite3.Row]:
        """JOIN triplo: medicao + equipamento + tecnico."""
        sql = """
            SELECT
                m.id_medicao,
                e.codigo             AS codigo,
                e.denominacao        AS denominacao,
                t.nome               AS tecnico,
                t.nome_setor         AS setor,
                m.parametro          AS parametro,
                m.valor_nominal      AS valor_nominal,
                m.tol_mais           AS tol_mais,
                m.tol_menos          AS tol_menos,
                m.medida1            AS medida1,
                m.medida2            AS medida2,
                m.media              AS media,
                m.desvio_padrao      AS desvio_padrao,
                m.status             AS status,
                m.data_medicao       AS data_medicao
            FROM medicao AS m
            INNER JOIN equipamento AS e ON e.id_equipamento = m.id_equipamento
            INNER JOIN tecnico     AS t ON t.id_tecnico     = m.id_tecnico
            ORDER BY m.data_medicao DESC, e.codigo, m.id_medicao;
        """
        return self._consultar(sql, (), "SELECT relatorio (JOIN)")

    def historico_por_equipamento(self, id_equipamento: int) -> list[sqlite3.Row]:
        """Histórico pesquisável por instrumento (RF07/RF12 da AV01)."""
        sql = """
            SELECT m.id_medicao, m.parametro, m.media, m.status, m.data_medicao,
                   t.nome AS tecnico
            FROM medicao AS m
            INNER JOIN tecnico AS t ON t.id_tecnico = m.id_tecnico
            WHERE m.id_equipamento = ?
            ORDER BY m.data_medicao DESC;
        """
        return self._consultar(sql, (id_equipamento,), "SELECT historico (JOIN)")


# =====================================================================
# CLASSE CERTIFICADO (domínio)
# =====================================================================
class Certificado:
    """
    Cabeçalho do ensaio de calibração. Agrupa N medições de um mesmo
    dispositivo. O status consolidado NÃO é informado de fora: é
    derivado das medições filhas (ver `consolidar_status`).
    """

    def __init__(
        self,
        numero: str,
        id_equipamento: int,
        id_tecnico: int,
        data_calibracao=None,
        id_solicitante: Optional[int] = None,
        temperatura: Optional[float] = None,
        padrao_utilizado: Optional[str] = None,
        procedimento: Optional[str] = None,
        incerteza_u: Optional[float] = None,
        fator_k: Optional[float] = None,
        observacoes: Optional[str] = None,
        id_certificado: Optional[int] = None,
        status: Optional[str] = None,
    ):
        self._id_certificado = id_certificado
        self._numero = _texto_obrigatorio(numero, "numero")
        self._id_equipamento = _inteiro(id_equipamento, "id_equipamento")
        self._id_tecnico = _inteiro(id_tecnico, "id_tecnico")
        self._id_solicitante = (
            _inteiro(id_solicitante, "id_solicitante")
            if id_solicitante is not None else None
        )
        self._data_calibracao = self._validar_data(data_calibracao)
        self._temperatura = (
            _numero_finito(temperatura, "temperatura")
            if temperatura is not None else None
        )
        self._padrao_utilizado = _texto_opcional(padrao_utilizado)
        self._procedimento = _texto_opcional(procedimento)
        self._incerteza_u = (
            _numero_finito(incerteza_u, "incerteza_u")
            if incerteza_u is not None else None
        )
        self._fator_k = (
            _numero_finito(fator_k, "fator_k") if fator_k is not None else None
        )
        self._observacoes = _texto_opcional(observacoes)
        # status pode vir do banco (leitura) ou ser consolidado depois
        self._status = self._validar_status(status) if status else None

    @staticmethod
    def _validar_data(valor) -> str:
        """Aceita date, datetime ou string ISO/BR. Rejeita placeholders."""
        if valor is None:
            return date.today().isoformat()
        if isinstance(valor, datetime):
            return valor.date().isoformat()
        if isinstance(valor, date):
            return valor.isoformat()
        texto = str(valor).strip()
        if texto in ("", "00/00/0000", "???", "----", "-----"):
            raise ErroValidacao(
                f"Data inválida ou placeholder não permitido: {valor!r}."
            )
        for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(texto, formato).date().isoformat()
            except ValueError:
                continue
        raise ErroValidacao(f"Data em formato não reconhecido: {valor!r}.")

    @staticmethod
    def _validar_status(valor) -> str:
        valor = str(valor or "").strip().upper()
        if valor not in STATUS_VALIDOS:
            raise ErroValidacao(
                f"Status deve ser um de {STATUS_VALIDOS}. Recebido: '{valor}'."
            )
        return valor

    # ------------------------- regra de negócio -------------------------
    @staticmethod
    def consolidar_status(statuses: list[str]) -> str:
        """
        Regra metrológica da Schulz: o dispositivo só é APROVADO se
        TODOS os parâmetros avaliados estiverem aprovados.
        Lista vazia é erro — não existe certificado sem medição.
        """
        if not statuses:
            raise ErroValidacao(
                "Não é possível consolidar status sem medições."
            )
        return (
            "APROVADO"
            if all(s == "APROVADO" for s in statuses)
            else "REPROVADO"
        )

    # ------------------------- encapsulamento -------------------------
    @property
    def id_certificado(self) -> Optional[int]:
        return self._id_certificado

    @id_certificado.setter
    def id_certificado(self, valor):
        if self._id_certificado is not None:
            raise ErroValidacao("id_certificado já definido e não pode ser alterado.")
        self._id_certificado = _inteiro(valor, "id_certificado")

    @property
    def numero(self) -> str:
        return self._numero

    @property
    def id_equipamento(self) -> int:
        return self._id_equipamento

    @property
    def id_tecnico(self) -> int:
        return self._id_tecnico

    @property
    def id_solicitante(self) -> Optional[int]:
        return self._id_solicitante

    @property
    def data_calibracao(self) -> str:
        return self._data_calibracao

    @property
    def data_calibracao_br(self) -> str:
        return datetime.strptime(
            self._data_calibracao, "%Y-%m-%d"
        ).strftime("%d/%m/%Y")

    @property
    def temperatura(self) -> Optional[float]:
        return self._temperatura

    @property
    def padrao_utilizado(self) -> Optional[str]:
        return self._padrao_utilizado

    @property
    def procedimento(self) -> Optional[str]:
        return self._procedimento

    @property
    def incerteza_u(self) -> Optional[float]:
        return self._incerteza_u

    @property
    def fator_k(self) -> Optional[float]:
        return self._fator_k

    @property
    def observacoes(self) -> Optional[str]:
        return self._observacoes

    @property
    def status(self) -> Optional[str]:
        return self._status

    @status.setter
    def status(self, valor):
        """Só o DAO define o status, após consolidar as medições."""
        self._status = self._validar_status(valor)

    def __repr__(self) -> str:
        return (
            f"Certificado(id={self._id_certificado}, numero='{self._numero}', "
            f"data='{self._data_calibracao}', status={self._status!r})"
        )


# =====================================================================
# DAO de Certificado
# =====================================================================
class CertificadoDAO(_DAOBase):
    """
    Persistência do cabeçalho do certificado e consolidação do status
    a partir das medições filhas.
    """

    @staticmethod
    def _linha_para_objeto(linha: sqlite3.Row) -> Certificado:
        return Certificado(
            numero=linha["numero"],
            id_equipamento=linha["id_equipamento"],
            id_tecnico=linha["id_tecnico"],
            data_calibracao=linha["data_calibracao"],
            id_solicitante=linha["id_solicitante"],
            temperatura=linha["temperatura"],
            padrao_utilizado=linha["padrao_utilizado"],
            procedimento=linha["procedimento"],
            incerteza_u=linha["incerteza_u"],
            fator_k=linha["fator_k"],
            observacoes=linha["observacoes"],
            id_certificado=linha["id_certificado"],
            status=linha["status"],
        )

    # ------------------------- INSERT -------------------------
    def inserir(self, certificado: Certificado) -> Certificado:
        """
        Insere o cabeçalho. O status inicial é consolidado a partir das
        medições já gravadas para este certificado; se ainda não houver
        nenhuma, grava REPROVADO como estado provisório seguro e o
        `recalcular_status` corrige depois.
        """
        status_inicial = self._status_das_medicoes(certificado.id_certificado) \
            if certificado.id_certificado else []
        status = (
            Certificado.consolidar_status(status_inicial)
            if status_inicial else "REPROVADO"
        )

        sql = (
            "INSERT INTO certificado (numero, id_equipamento, id_tecnico, "
            "id_solicitante, data_calibracao, temperatura, padrao_utilizado, "
            "procedimento, incerteza_u, fator_k, status, observacoes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
        )
        novo_id, _ = self._executar(
            sql,
            (
                certificado.numero,
                certificado.id_equipamento,
                certificado.id_tecnico,
                certificado.id_solicitante,
                certificado.data_calibracao,
                certificado.temperatura,
                certificado.padrao_utilizado,
                certificado.procedimento,
                certificado.incerteza_u,
                certificado.fator_k,
                status,
                certificado.observacoes,
            ),
            "INSERT certificado",
        )
        certificado.id_certificado = novo_id
        certificado.status = status
        return certificado

    # ------------------------- SELECT -------------------------
    def buscar_por_id(self, id_certificado: int) -> Optional[Certificado]:
        linhas = self._consultar(
            "SELECT * FROM certificado WHERE id_certificado = ?;",
            (id_certificado,), "SELECT certificado por id",
        )
        return self._linha_para_objeto(linhas[0]) if linhas else None

    def buscar_por_numero(self, numero: str) -> Optional[Certificado]:
        linhas = self._consultar(
            "SELECT * FROM certificado WHERE numero = ?;",
            (numero,), "SELECT certificado por numero",
        )
        return self._linha_para_objeto(linhas[0]) if linhas else None

    def listar(self) -> list[Certificado]:
        linhas = self._consultar(
            "SELECT * FROM certificado ORDER BY data_calibracao DESC, numero;",
            (), "SELECT certificado (listar)",
        )
        return [self._linha_para_objeto(l) for l in linhas]

    # ------------------------- UPDATE -------------------------
    def atualizar(self, certificado: Certificado) -> int:
        if certificado.id_certificado is None:
            raise ErroValidacao("Não é possível atualizar certificado sem id.")
        sql = (
            "UPDATE certificado SET numero = ?, id_equipamento = ?, "
            "id_tecnico = ?, id_solicitante = ?, data_calibracao = ?, "
            "temperatura = ?, padrao_utilizado = ?, procedimento = ?, "
            "incerteza_u = ?, fator_k = ?, status = ?, observacoes = ? "
            "WHERE id_certificado = ?;"
        )
        _, linhas_afetadas = self._executar(
            sql,
            (
                certificado.numero,
                certificado.id_equipamento,
                certificado.id_tecnico,
                certificado.id_solicitante,
                certificado.data_calibracao,
                certificado.temperatura,
                certificado.padrao_utilizado,
                certificado.procedimento,
                certificado.incerteza_u,
                certificado.fator_k,
                certificado.status,
                certificado.observacoes,
                certificado.id_certificado,
            ),
            "UPDATE certificado",
        )
        return linhas_afetadas

    def recalcular_status(self, id_certificado: int) -> str:
        """
        Relê as medições filhas, consolida o status e grava no cabeçalho.
        Chamado ao final do ETL, depois de inserir todas as medições.
        """
        statuses = self._status_das_medicoes(id_certificado)
        if not statuses:
            raise ErroValidacao(
                f"Certificado {id_certificado} não possui medições."
            )
        novo_status = Certificado.consolidar_status(statuses)
        self._executar(
            "UPDATE certificado SET status = ? WHERE id_certificado = ?;",
            (novo_status, id_certificado),
            "UPDATE status do certificado",
        )
        return novo_status

    # ------------------------- DELETE -------------------------
    def excluir(self, id_certificado: int) -> int:
        """
        DELETE. Com PRAGMA foreign_keys=ON, o banco recusa excluir um
        certificado que ainda tenha medições vinculadas.
        """
        _, linhas_afetadas = self._executar(
            "DELETE FROM certificado WHERE id_certificado = ?;",
            (id_certificado,), "DELETE certificado",
        )
        return linhas_afetadas

    # ------------------------- apoio interno -------------------------
    def _status_das_medicoes(self, id_certificado: int) -> list[str]:
        linhas = self._consultar(
            "SELECT status FROM medicao WHERE id_certificado = ?;",
            (id_certificado,), "SELECT status das medições",
        )
        return [l["status"] for l in linhas]

    # ------------------------- consulta do certificado -------------------------
    def certificado_completo(self, id_certificado: int) -> dict:
        """
        JOIN triplo + agregação: devolve o cabeçalho, os dados do
        equipamento, do técnico executante, do solicitante e a lista
        de medições. É a consulta que alimenta o emissor do certificado.
        """
        cabecalho = self._consultar(
            """
            SELECT
                c.id_certificado, c.numero, c.data_calibracao, c.temperatura,
                c.padrao_utilizado, c.procedimento, c.incerteza_u, c.fator_k,
                c.status AS status_certificado, c.observacoes,
                e.codigo, e.denominacao, e.fabricante, e.modelo, e.categoria,
                t.nome AS tecnico, t.matricula AS matricula_tecnico,
                t.nome_setor AS setor_tecnico,
                s.nome AS solicitante, s.nome_setor AS setor_solicitante
            FROM certificado AS c
            INNER JOIN equipamento AS e ON e.id_equipamento = c.id_equipamento
            INNER JOIN tecnico     AS t ON t.id_tecnico     = c.id_tecnico
            LEFT  JOIN tecnico     AS s ON s.id_tecnico     = c.id_solicitante
            WHERE c.id_certificado = ?;
            """,
            (id_certificado,), "SELECT certificado completo (JOIN)",
        )
        if not cabecalho:
            raise ErroValidacao(f"Certificado {id_certificado} não encontrado.")

        medicoes = self._consultar(
            """
            SELECT
                m.id_medicao, m.parametro, m.valor_nominal,
                m.tol_mais, m.tol_menos, m.medida1, m.medida2,
                m.media, m.desvio_padrao, m.status, m.data_medicao
            FROM medicao AS m
            WHERE m.id_certificado = ?
            ORDER BY m.id_medicao;
            """,
            (id_certificado,), "SELECT medições do certificado",
        )

        return {
            "cabecalho": dict(cabecalho[0]),
            "medicoes": [dict(m) for m in medicoes],
        }

    def resumo_por_equipamento(self) -> list[sqlite3.Row]:
        """
        Painel de acompanhamento: quantos certificados e qual a taxa de
        aprovação por dispositivo. Útil no manual do usuário.
        """
        sql = """
            SELECT
                e.codigo,
                e.denominacao,
                COUNT(c.id_certificado) AS total_certificados,
                SUM(CASE WHEN c.status = 'APROVADO' THEN 1 ELSE 0 END) AS aprovados,
                SUM(CASE WHEN c.status = 'REPROVADO' THEN 1 ELSE 0 END) AS reprovados,
                MAX(c.data_calibracao) AS ultima_calibracao
            FROM equipamento AS e
            LEFT JOIN certificado AS c ON c.id_equipamento = e.id_equipamento
            GROUP BY e.id_equipamento, e.codigo, e.denominacao
            ORDER BY e.codigo;
        """
        return self._consultar(sql, (), "SELECT resumo por equipamento")
