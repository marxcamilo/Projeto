# Schulz Calibração — Sistema de Gestão Metrológica

**Projeto Aplicado I — Entregas AV01 a AV04**
**Empresa parceira:** Schulz S.A. — Laboratório de Metrologia
**Equipe:** Marx Braga Camilo, Gladson Goulart, Carla Tayna, Yorman Hernandez
**Docentes:** Prof. MSc. Hugo Menezes Barra e Prof. Rodrigo Losina

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![openpyxl](https://img.shields.io/badge/openpyxl-3.1-217346?logo=microsoftexcel&logoColor=white)](https://openpyxl.readthedocs.io/)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-6.0+-yellow)](https://pyinstaller.org/)

---

## Sobre o projeto

O Laboratório de Metrologia da Schulz S.A. controla centenas de dispositivos de medição — paquímetros, micrômetros, relógios comparadores e dispositivos de controle dedicados — por meio de planilhas eletrônicas. O processo manual gerava três problemas recorrentes:

- **Nomenclatura inconsistente** — o mesmo parâmetro escrito de formas diferentes entre planilhas, impedindo comparação histórica.
- **Falta de rastreabilidade** — nenhum vínculo formal entre ensaio, técnico executante e solicitante.
- **Risco de erro de cálculo** — média, desvio padrão e classificação feitos à mão.

Este repositório entrega o MVP que resolve os três: uma aplicação executável que lê a planilha de ensaio, aplica as regras de higienização, grava em banco SQLite relacional e emite o certificado de calibração com o status consolidado do dispositivo.

---

## Estrutura do repositório

Entrega 02 - Projeto Aplicado I/
Entrega 02 - Projeto Aplicado I/
├── 03_banco.sql                  DDL do banco SQLite
├── 04_classes.py                 Domínio + persistência (POO)
├── 05_main.py                    Demonstração das 11 etapas da AV03
├── 07_gerador_certificado.py     Ingestão ETL + emissão de certificado
├── 08_mvp_final_manual.md        Documentação final e manual do usuário
├── build.bat                     Script de build (Windows)
├── evidencia_build.py            Gerador da evidência de build
├── evidencia_build.txt           Evidência gerada
├── README.md                     Este arquivo
├── Registro MMC.xlsx             Planilha de entrada da Schulz
├── dist/
│   └── Schulz_Calibracao.exe     Executável gerado
├── certificados/
│   ├── certificado_.txt
│   └── resultados_.csv
└── schulz_calibracao.db          Banco populado


---

## Início rápido

### Pré-requisitos

| Item | Versão mínima |
|---|---|
| Python | 3.10 |
| pip | 23.0 |
| openpyxl | 3.1 |
| PyInstaller | 6.0 (apenas para gerar o executável) |

### Instalação

```bash
git clone https://github.com/<usuario>/projeto-aplicado-schulz.git
cd projeto-aplicado-schulz
pip install openpyxl pyinstaller

Executar a demonstração do núcleo

codigo-gerado.shCódigo bash

Roda as 11 etapas da AV03: criação do banco, INSERT, bloqueio de regra de negócio, rejeição de FK, UPDATE com recálculo, JOIN triplo, consolidação de status e DELETE com proteção.

Executar o autoteste

codigo-gerado.shCódigo bash

Executa os 12 casos de teste que cobrem saneamento, classificação e consolidação.

Processar a planilha real

codigo-gerado.shCódigo bash

Gera o certificado em certificados/ e grava os dados no SQLite.

Gerar o executável

Windows:

codigo-gerado.batCódigo bat

Evolução das entregas

AV01 — Requisitos e regras de higienização

Levantamento dos gargalos operacionais da Schulz e formalização das regras de negócio. Definiu as regras RN01 a RN12, que orientam toda a implementação posterior.

Regra	Descrição
RN01	Medição incompleta é bloqueada antes de qualquer SQL
RN02	Média aritmética de duas leituras
RN03	Desvio padrão amostral (n−1)
RN04	Classificação em intervalo fechado
RN07	Erro = valor obtido − valor nominal
RN08	Normalizar acentuação
RN09	Descartar placeholders
RN10	Converter vírgula decimal
RN11	Normalizar tolerância para absoluto
RN12	Converter data BR para ISO

AV02 — Modelagem e banco SQLite

Implementação do DDL relacional em 03_banco.sql, com quatro tabelas: tecnico, equipamento, certificado e medicao.

codigo-gerado.sqlCódigo sql

O PRAGMA foreign_keys = ON é executado em toda abertura de conexão, garantindo que medições órfãs sejam rejeitadas.

AV03 — Núcleo em POO com persistência

Implementação do domínio em 04_classes.py com encapsulamento completo: atributos privados, acesso por @property, validação no construtor e nos setters.

Classes de domínio:

• Tecnico — executantes e solicitantes
• Equipamento — dispositivos de controle
• Medicao — cálculos derivados (média, desvio, erro, status)
• Certificado — cabeçalho do ensaio e consolidação de status

Camada de persistência:

• ConexaoSQLite — gerenciador de contexto com commit/rollback
• _DAOBase — base comum com _executar e _consultar
• TecnicoDAO, EquipamentoDAO, MedicaoDAO, CertificadoDAO

O 05_main.py demonstra as 11 etapas do ciclo completo.

AV04 — Ingestão, certificado e executável

Integração ponta a ponta em 07_gerador_certificado.py:

1. Localiza o cabeçalho da tabela de medição na planilha (até 60 linhas)
2. Lê os parâmetros com openpyxl
3. Aplica as regras de higienização da AV01
4. Grava no SQLite via DAOs
5. Consulta relacional com JOIN triplo
6. Consolida o status e emite o certificado

Empacotamento com PyInstaller via build.sh e build.bat.

Arquitetura

┌─────────────────────────────────────────────────────────────┐
│  ENTRADA                                                    │
│  Registro MMC.xlsx                                          │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  INGESTÃO E SANEAMENTO  (07_gerador_certificado.py)         │
│  Localiza cabeçalho → lê parâmetros → aplica RN08-RN12      │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  DOMÍNIO  (04_classes.py)                                   │
│  Tecnico + Equipamento + Certificado + Medicao              │
│  Medicao calcula; Certificado consolida                     │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PERSISTÊNCIA  (ConexaoSQLite + DAOs)                       │
│  schulz_calibracao.db                                       │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  EMISSÃO DE CERTIFICADO                                     │
│  JOIN triplo → consolidação → .txt + .csv                   │
└─────────────────────────────────────────────────────────────┘

Decisões de arquitetura:

• Separação em camadas — o domínio não conhece planilhas nem SQL; a ingestão não conhece SQL.
• Cálculos no domínio — média, desvio, erro e status sempre na classe Medicao, nunca no banco.
• Status derivado — o Certificado consolida a partir das medições filhas, nunca recebe status de fora.
• Fallback seguro — dados ausentes viram NAO INFORMADO em vez de quebrar o fluxo.
• Caminhos em runtime — PASTA e PASTA_DADOS distintas, para funcionar tanto no script quanto no .exe.

Regras metrológicas

Grandeza	Fórmula	Regra
Média	(m1 + m2) / 2	RN02
Desvio padrão	√[(m1−x̄)² + (m2−x̄)²] / (n−1)	RN03
Erro	x̄ − valor_nominal	RN07
Status	APROVADO se nominal − tol_menos ≤ x̄ ≤ nominal + tol_mais	RN04

O intervalo é fechado: uma média exatamente no limite é aprovada. O cálculo usa Decimal com 6 casas para evitar ruído binário.

Consolidação do certificado:

APROVADO  se TODAS as medições filhas forem APROVADO
REPROVADO se qualquer medição filha for REPROVADO
ERRO      se não houver medições

Testes

Autoteste (12 casos)

codigo-gerado.shCódigo bash

ID	Caso	Resultado
CT01	Acento removido	OK
CT02	Placeholder vira None	OK
CT03	Vírgula decimal	OK
CT04	tol_menos absoluto	OK
CT05	Data BR → ISO	OK
CT06	Data placeholder rejeitada	OK
CT07	Limite superior exato = APROVADO	OK
CT08	Acima do limite = REPROVADO	OK
CT09	Consolidado com 1 reprovado	OK
CT10	Consolidado todos aprovados	OK
CT11	Consolidar vazio levanta erro	OK
CT12	Medida vazia bloqueada	OK

Resultado: 12 casos, 0 falhas.

Teste com a planilha real

Entrada: Registro MMC.xlsx — 14 parâmetros do dispositivo de controle.

Parâmetro	Nominal	Tol +	Obtido	Erro	Status
PLANICIDADE_REF	0,0000	0,0500	0,002217	+0,002217	APROVADO
ENTRE CENTROS_REF	0,0000	0,0400	0,027415	+0,027415	APROVADO
62P_DIAMETRO 1	6,0750	0,0100	6,078729	+0,003729	APROVADO
62P_POSICAO 1	0,0000	0,1000	0,429552	+0,429552	REPROVADO
62P_DIAMETRO 2	6,0750	0,0100	6,078081	+0,003081	APROVADO
62P_POSICAO 2	0,0000	0,1000	0,244611	+0,244611	REPROVADO
13P_DIAMETRO 1	16,9640	0,0100	16,968448	+0,004448	APROVADO
13P_POSICAO 1	0,0000	0,1000	0,959044	+0,959044	REPROVADO
13P_DIAMETRO 2	16,9640	0,0100	16,969826	+0,005826	APROVADO
13P_POSICAO 2	0,0000	0,1000	0,235575	+0,235575	REPROVADO
106P_DIAMETRO 1	6,3450	0,0100	6,346313	+0,001314	APROVADO
106P_POSICAO 1	0,0000	0,1000	0,132190	+0,132190	REPROVADO
106P_DIAMETRO 2	6,3450	0,0100	6,348562	+0,003562	APROVADO
106P_POSICAO 2	0,0000	0,1000	0,867758	+0,867758	REPROVADO

Consolidação: 14 parâmetros, 8 aprovados, 6 reprovados → REPROVADO

Todos os diâmetros passaram (erro máximo de 0,006 mm contra tolerância de 0,010 mm). Todas as posições reprovaram — a maior é a 13P_POSICAO 1 com 0,959 mm, quase 10× o limite de 0,1 mm. Isso indica desalinhamento geométrico do dispositivo, não erro de medição.

Uso do executável

Modo interativo

Duplo clique no Schulz_Calibracao.exe. O programa pergunta a planilha de entrada e processa.

Modo linha de comando

codigo-gerado.batCódigo bat

Argumento	Função
--cli	Roda sem interação
--planilha NOME	Define a planilha de entrada
--selftest	Roda os 12 casos de teste internos

Saídas geradas

• certificados/certificado_<numero>.txt — documento formatado, pronto para impressão
• certificados/resultados_<numero>.csv — dados brutos para conferência
• schulz_calibracao.db — banco populado

Consultas úteis no banco

codigo-gerado.sqlCódigo sql

Limitações conhecidas

• Cabeçalho da planilha incompleto — a Registro MMC.xlsx não traz técnico, código do equipamento, padrão nem procedimento. O certificado sai com "não informado".
• Sem interface gráfica — o executável roda em terminal ou linha de comando.
• Sem assinatura digital — o certificado é .txt formatado, sem hash de integridade.
• Sem cálculo de incerteza combinada — o certificado declara U e k, mas não calcula a partir das fontes.

Documentação

Documento	Conteúdo
08_mvp_final_manual.pdf	Documentação técnica final + manual do usuário (16 páginas)
08_mvp_final_manual.md	Mesma documentação em Markdown
evidencia_build.txt	Prova de build: versões, autoteste, executável, execução real

Glossário

Termo	Definição
Calibração	Operações que estabelecem a relação entre os valores de um instrumento e os de referência
Certificado	Documento que registra o resultado de uma calibração
Incerteza expandida (U)	Incerteza multiplicada pelo fator de abrangência k
Fator k	Multiplicador do nível de confiança (k=2 ≈ 95%)
Tolerância	Faixa admissível de variação em torno do valor nominal
Desvio padrão	Medida da dispersão entre medições repetidas
EA-4/02	Referência europeia para expressão da incerteza em calibração
