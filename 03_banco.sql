-- =====================================================================
-- 03_banco.sql — Script DDL de criação do banco de calibrações (SQLite)
-- Projeto Aplicado I — Entregas 02 e 04 | Empresa parceira: Schulz S.A.
-- Equipe: Marx Braga Camilo, Gladson Goulart, Carla Tayna, Yorman Hernandez

-- =====================================================================

-- O SQLite só verifica chaves estrangeiras com esta opção ligada
PRAGMA foreign_keys = ON;

-- Ordem de DROP respeita as dependências (filhas primeiro)
DROP TABLE IF EXISTS medicao;
DROP TABLE IF EXISTS certificado;
DROP TABLE IF EXISTS equipamento;
DROP TABLE IF EXISTS tecnico;

-- ---------------------------------------------------------------------
-- Tabela 1: tecnico (Técnicos executantes e solicitantes)
-- ---------------------------------------------------------------------
CREATE TABLE tecnico (
    id_tecnico   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT    NOT NULL,
    papel        TEXT    NOT NULL CHECK (papel IN ('TECNICO', 'SOLICITANTE')),
    nome_setor   TEXT    NOT NULL,
    matricula    TEXT    UNIQUE
);

-- ---------------------------------------------------------------------
-- Tabela 2: equipamento (Instrumentos e dispositivos de controle)
-- ---------------------------------------------------------------------
CREATE TABLE equipamento (
    id_equipamento  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT    NOT NULL UNIQUE,
    denominacao     TEXT    NOT NULL,
    fabricante      TEXT    NOT NULL,
    modelo          TEXT    NOT NULL,
    categoria       TEXT
);

-- ---------------------------------------------------------------------
-- Tabela 3: certificado (NOVO na AV04)
-- Cabeçalho do ensaio: um certificado agrupa N medições de 1 equipamento,
-- executadas por 1 técnico, para 1 solicitante.
-- ---------------------------------------------------------------------
CREATE TABLE certificado (
    id_certificado   INTEGER PRIMARY KEY AUTOINCREMENT,
    numero           TEXT    NOT NULL UNIQUE,   -- ex.: '00091/2026'
    id_equipamento   INTEGER NOT NULL,
    id_tecnico       INTEGER NOT NULL,          -- executante
    id_solicitante   INTEGER,                   -- cliente interno (opcional)
    data_calibracao  TEXT    NOT NULL DEFAULT CURRENT_DATE,  -- ISO AAAA-MM-DD
    temperatura      REAL,                      -- °C no momento do ensaio
    padrao_utilizado TEXT,                      -- ex.: 'MMC 500.011 - Carl Zeiss'
    procedimento     TEXT,                      -- ex.: 'ITL-0026'
    incerteza_u      REAL,                      -- U expandida (mm)
    fator_k          REAL,                      -- fator de abrangência
    status           TEXT    NOT NULL CHECK (status IN ('APROVADO', 'REPROVADO')),
    observacoes      TEXT,
    FOREIGN KEY (id_equipamento) REFERENCES equipamento (id_equipamento),
    FOREIGN KEY (id_tecnico)     REFERENCES tecnico (id_tecnico),
    FOREIGN KEY (id_solicitante) REFERENCES tecnico (id_tecnico)
);

-- ---------------------------------------------------------------------
-- Tabela 4: medicao (Registro das calibrações / ensaios)
-- Cada medição pertence a 1 certificado, 1 equipamento e 1 técnico.
-- ---------------------------------------------------------------------
CREATE TABLE medicao (
    id_medicao      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_certificado  INTEGER NOT NULL,
    id_equipamento  INTEGER NOT NULL,
    id_tecnico      INTEGER NOT NULL,
    data_medicao    TEXT    NOT NULL DEFAULT CURRENT_DATE,
    parametro       TEXT    NOT NULL,
    valor_nominal   REAL    NOT NULL,
    tol_mais        REAL    NOT NULL,
    tol_menos       REAL    NOT NULL,   -- sempre em valor ABSOLUTO
    medida1         REAL    NOT NULL,
    medida2         REAL    NOT NULL,
    media           REAL,
    desvio_padrao   REAL,
    status          TEXT    NOT NULL CHECK (status IN ('APROVADO', 'REPROVADO')),
    FOREIGN KEY (id_certificado) REFERENCES certificado (id_certificado),
    FOREIGN KEY (id_equipamento) REFERENCES equipamento (id_equipamento),
    FOREIGN KEY (id_tecnico)     REFERENCES tecnico (id_tecnico)
);

-- ---------------------------------------------------------------------
-- Índices de apoio às consultas do gerador de certificados
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_medicao_certificado ON medicao (id_certificado);
CREATE INDEX IF NOT EXISTS ix_medicao_equipamento ON medicao (id_equipamento);
CREATE INDEX IF NOT EXISTS ix_certificado_equip  ON certificado (id_equipamento);
CREATE INDEX IF NOT EXISTS ix_certificado_data   ON certificado (data_calibracao);
