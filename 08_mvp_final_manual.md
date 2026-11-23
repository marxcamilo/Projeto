# Documentação Final do MVP e Manual do Usuário

**Projeto Aplicado I — AV 04**
**Empresa parceira:** Schulz S.A.
**Sistema:** Schulz Calibração — Ingestão Automatizada de Planilhas e Emissão de Certificados

**Equipe:** Marx Braga Camilo, Gladson Goulart, Carla Tayna, Yorman Hernandez
**Docentes:** Prof. MSc. Hugo Menezes Barra e Prof. Rodrigo Losina
**Data de entrega:** 30/11/2026

---

## Sumário

1. [Visão Geral do Projeto](#1-visão-geral-do-projeto)
2. [Arquitetura Final Integrada](#2-arquitetura-final-integrada)
3. [Estrutura de Arquivos](#3-estrutura-de-arquivos)
4. [Guia de Geração do Executável (Build)](#4-guia-de-geração-do-executável-build)
5. [Manual do Usuário](#5-manual-do-usuário)
6. [Plano de Testes](#6-plano-de-testes)
7. [Resultados Obtidos](#7-resultados-obtidos)
8. [Conclusões](#8-conclusões)
9. [Anexos](#9-anexos)

---

## 1. Visão Geral do Projeto

### 1.1 Contexto

O laboratório de metrologia da Schulz S.A. registrava os ensaios de calibração de dispositivos de controle em planilhas Excel preenchidas manualmente. O processo apresentava três gargalos:

- **Inconsistência de nomenclatura:** acentos, espaços e caracteres inválidos nos parâmetros, impedindo qualquer análise automatizada.
- **Cálculo manual de status:** o técnico comparava cada medição com a tolerância à mão, gerando erros de julgamento.
- **Ausência de histórico consultável:** cada ensaio ficava isolado na sua planilha, sem rastreabilidade por instrumento.

### 1.2 Solução entregue

O sistema **Schulz Calibração** automatiza o ciclo completo:

1. **Ingestão e saneamento** — lê a planilha de registro do ensaio, normaliza os dados segundo as regras da AV01 e grava no banco SQLite.
2. **Motor de classificação** — calcula média, desvio padrão e erro de cada parâmetro, classificando cada um como APROVADO ou REPROVADO.
3. **Emissão de certificado** — consulta relacional com JOIN, consolida o status do dispositivo e gera o certificado em texto e os resultados em CSV.

### 1.3 Resultado operacional

| Indicador | Antes | Depois |
|---|---|---|
| Tempo de emissão do certificado | ~40 min (manual) | < 5 s (automático) |
| Erros de cálculo de status | Frequentes | Zero (regra determinística) |
| Rastreabilidade por instrumento | Inexistente | Histórico completo no SQLite |
| Padronização de nomenclatura | Manual | Automática (24 correções no ensaio real) |

---

## 2. Arquitetura Final Integrada

### 2.1 Diagrama de fluxo ponta a ponta

┌─────────────────────────────────────────────────────────────────────────┐
│                         ENTRADA — PLANILHA EXCEL                        │
│                    Registro_MMC.xlsx (aba "Registro")                   │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Linha 1-12: cabeçalho (técnico, equipamento, padrão, procedimento)│  │
│  │ Linha 13: cabeçalho da tabela (Characteristic, Nominal, Tol, ...) │  │
│  │ Linha 14-27: 14 parâmetros do ensaio                              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────┐
│              MÓDULO 1 — INGESTÃO E SANEAMENTO (ETL)                     │
│                     07_gerador_certificado.py                           │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │ Leitor OpenPyXL  │→ │ Motor de         │→ │ Validação de domínio │  │
│  │ (read_only)      │  │ saneamento       │  │ (04_classes.py)      │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
│                                                                         │
│  Regras aplicadas:                                                      │
│   • Acentuação normalizada      → 24 ocorrências no ensaio real         │
│   • Tolerância normalizada (abs)→ 6 ocorrências no ensaio real          │
│   • Placeholders → None         → "---", "N/A", "00/00/0000"           │
│   • Vírgula decimal → ponto     → "6,0787295" → 6.0787295              │
│   • Data BR → ISO               → "26/08/2026" → "2026-08-26"          │
└────────────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MÓDULO 2 — PERSISTÊNCIA (SQLite)                     │
│                          schulz_calibracao.db                           │
│                                                                         │
│   ┌───────────┐      ┌──────────────┐      ┌──────────┐                │
│   │  tecnico  │◄─────│  certificado │─────►│medicao   │                │
│   │           │      │              │      │          │                │
│   │ id_tecnico│      │id_certificado│      │id_medicao│                │
│   │ nome      │      │numero        │      │id_certif.│                │
│   │ papel     │      │id_equipamento│      │parametro │                │
│   │ nome_setor│      │id_tecnico    │      │media     │                │
│   │ matricula │      │id_solicitante│      │status    │                │
│   └───────────┘      │data_calibracao│     └──────────┘                │
│         ▲            │status        │            ▲                     │
│         │            └──────────────┘            │                     │
│         │                   ▲                    │                     │
│         │                   │                    │                     │
│   ┌─────┴───────────────────┴────────────────────┴─────┐               │
│   │              equipamento                          │               │
│   │  id_equipamento | codigo | denominacao | modelo   │               │
│   └───────────────────────────────────────────────────┘               │
│                                                                         │
│   PRAGMA foreign_keys = ON  (integridade referencial ativa)             │
└────────────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────┐
│              MÓDULO 3 — MOTOR DE EMISSÃO DE CERTIFICADOS                │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  CertificadoDAO.certificado_completo(id)                          │  │
│  │                                                                   │  │
│  │  SELECT ... FROM certificado c                                    │  │
│  │    INNER JOIN equipamento e ON e.id_equipamento = c.id_equipamento│  │
│  │    INNER JOIN tecnico     t ON t.id_tecnico     = c.id_tecnico    │  │
│  │    LEFT  JOIN tecnico     s ON s.id_tecnico     = c.id_solicitante│  │
│  │  WHERE c.id_certificado = ?                                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                 │                                       │
│                                 ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Regra metrológica de consolidação:                               │  │
│  │                                                                   │  │
│  │  APROVADO  se TODOS os parâmetros estiverem APROVADOS             │  │
│  │  REPROVADO se QUALQUER parâmetro estiver REPROVADO                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          SAÍDA — ARTEFATOS                              │
│                                                                         │
│   certificados/certificado_20261121205501.txt   (certificado completo)  │
│   certificados/resultados_20261121205501.csv    (tabela de resultados)  │
│   Console: RESULTADO FINAL: REPROVADO                                   │
└─────────────────────────────────────────────────────────────────────────┘


### 2.2 Camadas do sistema

| Camada | Arquivo | Responsabilidade |
|---|---|---|
| Apresentação | `07_gerador_certificado.py` | CLI, leitura da planilha, orquestração, emissão dos artefatos |
| Domínio | `04_classes.py` | Entidades, validação, regras metrológicas |
| Persistência | `04_classes.py` (DAOs) | Acesso ao SQLite, mapeamento objeto-relacional |
| Esquema | `03_banco.sql` | DDL, chaves estrangeiras, índices |
| Demonstração | `05_main.py` | Prova das 11 operações CRUD + JOIN (AV03) |
| Build | `build.sh` / `build.bat` | Empacotamento com PyInstaller |
| Evidência | `evidencia_build.py` | Relatório de build e testes |

### 2.3 Decisões de projeto

**Por que SQLite e não um servidor de banco?**
O técnico da Schulz opera em estações Windows sem infraestrutura de TI dedicada. O SQLite é um arquivo único, não exige instalação e mantém a integridade referencial com `PRAGMA foreign_keys = ON`.

**Por que separar `certificado` de `medicao`?**
Um ensaio de calibração tem um cabeçalho (número, data, técnico, padrão utilizado) e N parâmetros avaliados. Modelar o cabeçalho separadamente permite que o status consolidado seja derivado das medições filhas, sem duplicar dados.

**Por que o status é calculado e não informado?**
A classe `Medicao` recebe apenas as leituras brutas (`medida1`, `medida2`) e o `Certificado` recebe apenas os `status` das filhas. Nenhum dos dois aceita o resultado pronto — isso elimina a possibilidade de um status inconsistente entrar no banco.

**Por que `tol_menos` é sempre absoluto?**
A planilha da Schulz traz a tolerância inferior como valor negativo (`-0,05`) em algumas linhas e positivo (`0,05`) em outras. Normalizar para absoluto no construtor elimina a ambiguidade e garante que `limite_inferior = nominal - tol_menos` funcione sempre.

---

## 3. Estrutura de Arquivos

### 3.1 Árvore do projeto

Entrega 02 - Projeto Aplicado I/
│
├── 03_banco.sql                      # DDL — 4 tabelas, 4 índices, FKs
├── 04_classes.py                     # Domínio + DAOs (Tecnico, Equipamento,
│                                     #   Medicao, Certificado + 4 DAOs)
├── 05_main.py                        # Demonstração AV03 — 11 etapas
├── 07_gerador_certificado.py         # ETL + emissão de certificados (AV04)
├── 08_mvp_final_manual.md            # Este documento
├── README.md                         # Visão geral do repositório
├── build.bat                         # Build script Windows
├── evidencia_build.py                # Gerador do relatório de evidência
├── evidencia_build.txt               # Evidência gerada (saída)
│
├── Registro MMC.xlsx                 # Planilha de entrada (ensaio real)
├── planilha MMC.xlsx                 # Planilha de referência AV01
│
├── schulz_calibracao.db              # Banco SQLite (gerado em runtime)
│
├── certificados/                     # Artefatos gerados
│   ├── certificado_20261121205501.txt
│   └── resultados_20261121205501.csv
│
└── dist/                             # Executável gerado pelo PyInstaller
└── Schulz_Calibracao.exe


### 3.2 Dependências

| Dependência | Versão mínima | Uso |
|---|---|---|
| Python | 3.10 | `match`, type hints `X \| None` |
| openpyxl | 3.1 | Leitura das planilhas `.xlsx` |
| PyInstaller | 6.0 | Empacotamento do executável |
| sqlite3 | stdlib | Persistência |
| statistics | stdlib | `stdev` (desvio padrão amostral) |
| decimal | stdlib | Comparações sem ruído binário |

Todas as dependências de terceiros são instaladas pelo `build.sh` / `build.bat`. O usuário final não precisa instalar nada.

---

## 4. Guia de Geração do Executável (Build)

### 4.1 Pré-requisitos

**Windows:**
- Python 3.10 ou superior instalado com "Add Python to PATH" marcado
- Acesso à internet para o `pip install`

### 4.2 Build no Windows

Abra o Prompt de Comando na pasta do projeto:

```bat
cd "C:\caminho\da\pasta\Entrega 02 - Projeto Aplicado I"
build.bat
O script executa seis etapas:

[1/6] Verificando arquivos de origem...
  [OK] 03_banco.sql
  [OK] 04_classes.py
  [OK] 07_gerador_certificado.py
[2/6] Verificando Python...
  Python 3.12.1
[3/6] Instalando dependencias...
  [OK] pyinstaller e openpyxl instalados
[4/6] Limpando builds anteriores...
[5/6] Gerando executavel com PyInstaller...
[6/6] Validando o executavel...
  [OK] dist\Schulz_Calibracao.exe (12456789 bytes)

======================================================
 BUILD CONCLUIDO
======================================================

================================================================================
## 5. MANUAL DO USUÁRIO
================================================================================

### 5.1 Para quem é este manual
--------------------------------------------------------------------------------

Técnico de metrologia da Schulz S.A. que precisa calibrar um dispositivo de
controle e emitir o certificado. Não é necessário saber programar.

### 5.2 Primeira execução
--------------------------------------------------------------------------------

  1. Copie o Schulz_Calibracao.exe para uma pasta de trabalho (por exemplo,
     C:\Metrologia\).
  2. Copie a planilha de ensaio para a mesma pasta.
  3. Dê duplo clique no executável.

Na primeira execução, o programa cria:

  - schulz_calibracao.db — o banco de dados
  - certificados/ — a pasta onde os certificados serão salvos

### 5.3 Modo interativo
--------------------------------------------------------------------------------

Ao abrir sem argumentos, o programa pergunta:

  Planilha de entrada [Registro MMC.xlsx]:

Pressione Enter para usar a planilha padrão, ou digite o nome de outra
planilha.

### 5.4 Modo linha de comando
--------------------------------------------------------------------------------

Para uso em lote ou automação:

  Schulz_Calibracao.exe --cli --planilha "Registro MMC.xlsx"

  Argumento            Função
  --------------------------------------------------------------------------
  --cli                Roda sem interação
  --planilha NOME      Define a planilha de entrada
  --selftest           Roda os 12 casos de teste internos
  --recriar            Apaga o banco antes de rodar (se disponível)

### 5.5 Lendo o certificado
--------------------------------------------------------------------------------

O programa gera dois arquivos na pasta certificados/:

certificado_<numero>.txt — o documento formatado, pronto para impressão.
Contém:

  1. Descrição do instrumento calibrado
  2. Padrão utilizado
  3. Procedimento de calibração
  4. Responsáveis
  5. Tabela de resultados (14 parâmetros)
  6. Resultado final (APROVADO / REPROVADO)
  7. Observações sobre a incerteza expandida

resultados_<numero>.csv — os dados brutos em formato de planilha, para
conferência ou importação em outro sistema.

### 5.6 Interpretando o resultado
--------------------------------------------------------------------------------

  Status      Significado                        Ação
  --------------------------------------------------------------------------
  APROVADO    Todos os parâmetros dentro da      Dispositivo liberado
              tolerância                         para uso

  REPROVADO   Um ou mais parâmetros fora da      Dispositivo bloqueado;
              tolerância                         avaliar ajuste ou descarte

No certificado, cada parâmetro mostra nominal, tolerância, valor obtido, erro
e status individual. O técnico identifica rapidamente qual parâmetro reprovou.

### 5.7 Mensagens de erro comuns
--------------------------------------------------------------------------------

  Mensagem                          Causa / Solução
  --------------------------------------------------------------------------
  Arquivo não encontrado            Planilha fora da pasta. Copie a
                                    planilha para a pasta do executável.

  Cabeçalho da tabela não           Planilha sem a tabela de medição.
  encontrado                        Confira se é a planilha correta.

  Nenhum parâmetro válido           Todos os dados são placeholders.
                                    Preencha a planilha antes de rodar.

  FOREIGN KEY constraint failed     Tentativa de excluir registro com
                                    dependências. Exclua as medições antes
                                    do certificado.

### 5.8 Boas práticas
--------------------------------------------------------------------------------

  - Mantenha o banco em backup antes de rodar com --recriar.
  - Use nomes de planilha descritivos (Registro_MMC_2026-11.xlsx).
  - Confira o cabeçalho da planilha antes de rodar: técnico, equipamento,
    padrão e procedimento preenchidos geram um certificado completo.
  - Guarde os certificados emitidos: eles são o registro formal do ensaio.

================================================================================
## 6. PLANO DE TESTES REALIZADOS
================================================================================

### 6.1 Casos de teste automatizados (autoteste)
--------------------------------------------------------------------------------

O comando --selftest executa 12 casos que cobrem saneamento, classificação e
consolidação.

  ID     Caso                          Entrada              Resultado
  --------------------------------------------------------------------------
  CT01   Acento removido               62P_DIÂMETRO 1       OK
  CT02   Placeholder vira vazio        ---                  OK
  CT03   Vírgula decimal               6,0787295            OK
  CT04   tol_menos absoluto            -0,01                OK
  CT05   Data BR -> ISO                26/08/2026           OK
  CT06   Data placeholder rejeitada    00/00/0000           OK
  CT07   Limite superior exato         media 50,05 tol 0,05 OK
  CT08   Acima do limite               media 50,06 tol 0,05 OK
  CT09   Consolidado com 1 reprovado   [APROV, REPROV]      OK
  CT10   Consolidado todos aprovados   [APROV, APROV]       OK
  CT11   Consolidar vazio              []                   OK
  CT12   Medida vazia bloqueada        medida2 = " "        OK

Resultado: 12 casos, 0 falhas.

### 6.2 Casos de teste do núcleo (05_main.py)
--------------------------------------------------------------------------------

O 05_main.py executa 11 etapas que demonstram o comportamento do domínio e da
persistência.

  Etapa   O que testa                            Resultado esperado
  --------------------------------------------------------------------------
  [1]     Recriação do banco a partir do DDL     Banco criado
  [2]     INSERT de técnicos e equipamentos      4 registros
  [3]     Criação do certificado                 id=1, status provisório
  [4]     INSERT de medições com classificação   3 medições
  [5]     Bloqueio de medição incompleta (RN01)  Erro de validação
  [6]     Rejeição de FK inexistente             Erro de persistência
  [7]     UPDATE com recálculo                   Status muda
  [8]     JOIN triplo                            Relatório completo
  [9]     Consolidação do certificado            Status consolidado
  [10]    Histórico por equipamento              Lista de medições
  [11]    DELETE com proteção de FK              Bloqueio correto

### 6.3 Teste com a planilha real
--------------------------------------------------------------------------------

Entrada: Registro MMC.xlsx (14 parâmetros do dispositivo de controle)

Saneamento aplicado:
  - 24 ocorrências de acentuação normalizadas
  - 6 ocorrências de tolerância convertidas para absoluto

Resultado:

  Parâmetro            Nominal   Tol +    Obtido      Erro        Status
  ----------------------------------------------------------------------------
  PLANICIDADE_REF      0,0000    0,0500   0,002217    +0,002217   APROVADO
  ENTRE CENTROS_REF    0,0000    0,0400   0,027415    +0,027415   APROVADO
  62P_DIAMETRO 1       6,0750    0,0100   6,078729    +0,003729   APROVADO
  62P_POSICAO 1        0,0000    0,1000   0,429552    +0,429552   REPROVADO
  62P_DIAMETRO 2       6,0750    0,0100   6,078081    +0,003081   APROVADO
  62P_POSICAO 2        0,0000    0,1000   0,244611    +0,244611   REPROVADO
  13P_DIAMETRO 1       16,9640   0,0100   16,968448   +0,004448   APROVADO
  13P_POSICAO 1        0,0000    0,1000   0,959044    +0,959044   REPROVADO
  13P_DIAMETRO 2       16,9640   0,0100   16,969826   +0,005826   APROVADO
  13P_POSICAO 2        0,0000    0,1000   0,235575    +0,235575   REPROVADO
  106P_DIAMETRO 1      6,3450    0,0100   6,346313    +0,001314   APROVADO
  106P_POSICAO 1       0,0000    0,1000   0,132190    +0,132190   REPROVADO
  106P_DIAMETRO 2      6,3450    0,0100   6,348562    +0,003562   APROVADO
  106P_POSICAO 2       0,0000    0,1000   0,867758    +0,867758   REPROVADO

Consolidação: 14 parâmetros, 8 aprovados, 6 reprovados -> REPROVADO

Análise: todos os diâmetros passaram (erro máximo de 0,006 mm contra
tolerância de 0,010 mm). Todas as posições reprovaram — a maior é a
13P_POSICAO 1 com 0,959 mm, quase 10x o limite de 0,1 mm. Isso indica
desalinhamento geométrico do dispositivo, não erro de medição.

### 6.4 Teste do executável
--------------------------------------------------------------------------------

  Teste           Comando                                    Resultado
  --------------------------------------------------------------------------
  Autoteste       Schulz_Calibracao.exe --selftest           12/12
  Processamento   Schulz_Calibracao.exe --cli                Certificado
                  --planilha "Registro MMC.xlsx"             gerado
  Persistência    Verificar schulz_calibracao.db ao lado     Banco criado
                  do .exe
  Saídas          Verificar certificados/                    2 arquivos

================================================================================
## 7. RESULTADOS OBTIDOS
================================================================================

### 7.1 Objetivos alcançados
--------------------------------------------------------------------------------

  Objetivo                            Status       Evidência
  --------------------------------------------------------------------------
  Ingestão automatizada de            Alcançado    14 parâmetros lidos
  planilhas                                        e saneados

  Aplicação das regras de             Alcançado    24 acentos + 6
  higienização                                     tolerâncias corrigidos

  Gravação segura no SQLite           Alcançado    Certificado id=1 com
                                                   14 medições

  Consulta relacional (JOIN)          Alcançado    Certificado completo
                                                   com técnico e equipamento

  Emissão de certificado              Alcançado    .txt e .csv gerados

  Consolidação de status              Alcançado    REPROVADO com 8/14

  Executável sem dependências         Alcançado    Schulz_Calibracao.exe
                                                   funcional

### 7.2 Ganhos operacionais
--------------------------------------------------------------------------------

Redução de erro de cálculo.
Média, desvio e classificação são calculados pela classe, nunca à mão. O
técnico não precisa mais conferir fórmula.

Rastreabilidade completa.
Cada certificado vincula equipamento, técnico executante, solicitante, data e
os 14 parâmetros. O histórico fica no banco e pode ser consultado por
equipamento.

Padronização de nomenclatura.
A normalização de acentos e espaços garante que DIÂMETRO e DIAMETRO sejam o
mesmo parâmetro em qualquer planilha.

Eliminação de dependência de IDE.
O técnico roda o .exe com duplo clique. Não precisa de Python, VS Code ou
terminal.

================================================================================
## 8. CONCLUSÕES
================================================================================

### 8.1 O que funcionou bem
--------------------------------------------------------------------------------

A separação em camadas provou seu valor durante o desenvolvimento. Quando o
DDL mudou para incluir a tabela certificado, apenas o 04_classes.py e o
03_banco.sql precisaram de ajuste — o 05_main.py e o 07 continuaram
funcionando com pequenas adaptações.

O cálculo no domínio, com Decimal em vez de float, eliminou os erros de
arredondamento que apareciam nos testes iniciais. Uma média de 50,05 com
tolerância 0,05 agora é classificada corretamente como APROVADO, sem depender
de comparação de ponto flutuante.

O fallback seguro para dados ausentes evitou que planilhas incompletas
quebrassem o fluxo. O certificado sai com NAO INFORMADO no técnico, mas o
ensaio é registrado e pode ser corrigido depois.

### 8.2 Limitações conhecidas
--------------------------------------------------------------------------------

Cabeçalho da planilha incompleto.
A Registro MMC.xlsx não traz técnico, código do equipamento, padrão nem
procedimento preenchidos. O certificado emitido mostra esses campos como
"não informado". A solução definitiva é preencher o cabeçalho na planilha ou
passar os dados por parâmetro no 07.

Sem interface gráfica.
O executável roda em modo interativo de terminal ou por linha de comando.
Para o técnico da Schulz, uma interface com botões reduziria a curva de
aprendizado.

Sem assinatura digital.
O certificado é um .txt formatado. Não há assinatura criptográfica nem hash de
integridade. Para uso formal, seria necessário um PDF assinado.

Sem validação de incerteza.
O certificado declara a incerteza expandida e o fator k, mas não calcula a
incerteza combinada a partir das fontes (repetitividade, resolução, padrão).
Isso ficaria para uma versão futura.

### 8.3 Trabalhos futuros
--------------------------------------------------------------------------------

  - Interface gráfica com Tkinter ou PyQt para o técnico.
  - Exportação em PDF com assinatura digital.
  - Cálculo completo da incerteza de medição conforme EA-4/02.
  - Dashboard de acompanhamento com taxa de aprovação por equipamento.
  - Integração com o sistema de manutenção da Schulz via API.

================================================================================
## 9. ANEXOS
================================================================================

### 9.1 Comandos de referência
--------------------------------------------------------------------------------

  # Demonstração do núcleo (11 etapas)
  python3 05_main.py

  # Autoteste do gerador
  python3 07_gerador_certificado.py --selftest

  # Processar planilha real
  python3 07_gerador_certificado.py --cli --planilha "Registro MMC.xlsx"

  # Gerar executável (Linux)
  ./build.sh

  # Gerar executável (Windows)
  build.bat

  # Gerar evidência de build
  python3 evidencia_build.py

### 9.2 Estrutura do banco
--------------------------------------------------------------------------------

  -- Consultar todos os certificados
  SELECT numero, data_calibracao, status FROM certificado;

  -- Consultar medições de um certificado
  SELECT parametro, media, status
  FROM medicao
  WHERE id_certificado = 1
  ORDER BY id_medicao;

  -- Resumo por equipamento
  SELECT e.codigo, e.denominacao,
         COUNT(c.id_certificado) AS total,
         SUM(CASE WHEN c.status = 'APROVADO' THEN 1 ELSE 0 END) AS aprovados
  FROM equipamento e
  LEFT JOIN certificado c ON c.id_equipamento = e.id_equipamento
  GROUP BY e.id_equipamento;

### 9.3 Glossário
--------------------------------------------------------------------------------

  Termo                  Definição
  --------------------------------------------------------------------------
  Calibração             Conjunto de operações que estabelece a relação
                         entre os valores indicados por um instrumento e os
                         valores de referência

  Certificado            Documento que registra o resultado de uma calibração

  Incerteza expandida    Incerteza de medição multiplicada pelo fator de
  (U)                    abrangência k

  Fator k                Multiplicador que define o nível de confiança da
                         incerteza (k=2 aprox. 95%)

  Tolerância             Faixa admissível de variação em torno do valor
                         nominal

  Valor nominal          Valor de referência especificado para o parâmetro

  Desvio padrão          Medida da dispersão entre as medições repetidas

  EA-4/02                Documento de referência europeu para expressão da
                         incerteza em calibração

================================================================================
FIM DO DOCUMENTO
================================================================================

Projeto Aplicado I — AV04 | Schulz S.A. | Novembro de 2026


