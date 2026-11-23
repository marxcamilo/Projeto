"""
evidencia_build.py — Gera o relatório de evidência de build.
Executa o autoteste, processa uma planilha real, valida o executável
e grava tudo em evidencia_build.txt.
"""
import subprocess
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PASTA = Path(__file__).resolve().parent
SAIDA = PASTA / "evidencia_build.txt"
APP_NAME = "Schulz_Calibracao"


def executar(comando: list[str], timeout: int = 180) -> tuple[int, str]:
    """Roda um comando e devolve (código de saída, stdout+stderr)."""
    try:
        r = subprocess.run(
            comando, capture_output=True, text=True, timeout=timeout,
            cwd=PASTA, encoding="utf-8", errors="replace",
        )
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"[TIMEOUT] Comando excedeu {timeout}s."
    except Exception as exc:
        return 1, f"[EXCECAO] {exc}"


def versao_pacote(nome: str) -> str:
    """Lê a versão instalada sem depender do pip."""
    try:
        return version(nome)
    except PackageNotFoundError:
        return "nao instalado"


def localizar_executavel() -> Path | None:
    """Procura o binário gerado pelo PyInstaller."""
    candidatos = [
        PASTA / "dist" / APP_NAME,
        PASTA / "dist" / f"{APP_NAME}.exe",
        PASTA / APP_NAME,
        PASTA / f"{APP_NAME}.exe",
    ]
    for c in candidatos:
        if c.exists():
            return c
    return None


def main() -> int:
    linhas = [
        "=" * 70,
        "EVIDENCIA DE BUILD — Schulz Calibracao",
        f"Gerado em: {datetime.now():%d/%m/%Y %H:%M:%S}",
        f"Python: {sys.version.split()[0]}",
        f"Plataforma: {sys.platform}",
        "=" * 70,
        "",
    ]

    # --- 1. Versões ---------------------------------------------------
    print("[1/5] Verificando versoes...")
    linhas.append("DEPENDENCIAS")
    linhas.append("-" * 70)
    for pacote in ("openpyxl", "pyinstaller"):
        linhas.append(f"{pacote:<14} {versao_pacote(pacote)}")
    linhas.append("")

    # --- 2. Arquivos de origem ----------------------------------------
    print("[2/5] Listando arquivos de origem...")
    linhas.append("ARQUIVOS DE ORIGEM")
    linhas.append("-" * 70)
    for nome in ("03_banco.sql", "04_classes.py", "05_main.py",
                 "07_gerador_certificado.py"):
        arq = PASTA / nome
        if arq.exists():
            kb = arq.stat().st_size / 1024
            linhas.append(f"{nome:<32} {kb:>8.1f} KB")
        else:
            linhas.append(f"{nome:<32} AUSENTE")
    linhas.append("")

    # --- 3. Autoteste -------------------------------------------------
    print("[3/5] Executando autoteste...")
    codigo, saida = executar(
        [sys.executable, "07_gerador_certificado.py", "--selftest"]
    )
    linhas.append("-" * 70)
    linhas.append("AUTOTESTE")
    linhas.append("-" * 70)
    linhas.append(saida.strip())
    linhas.append(f"Codigo de saida: {codigo}")
    linhas.append("")

    # --- 4. Executável ------------------------------------------------
    print("[4/5] Validando o executavel...")
    linhas.append("-" * 70)
    linhas.append("EXECUTAVEL")
    linhas.append("-" * 70)
    exe = localizar_executavel()
    if exe is None:
        linhas.append("[AVISO] Executavel nao encontrado.")
        linhas.append("Rode build.sh (Linux) ou build.bat (Windows) antes.")
    else:
        tamanho_mb = exe.stat().st_size / (1024 * 1024)
        linhas.append(f"Caminho : {exe.relative_to(PASTA)}")
        linhas.append(f"Tamanho : {tamanho_mb:.2f} MB")
        linhas.append("")
        linhas.append("Autoteste do executavel:")
        codigo, saida = executar([str(exe), "--selftest"])
        linhas.append(saida.strip())
        linhas.append(f"Codigo de saida: {codigo}")
    linhas.append("")

    # --- 5. Planilha real ---------------------------------------------
    print("[5/5] Processando planilha real...")
    planilhas = sorted(PASTA.glob("*.xlsx"))
    alvo = next((p for p in planilhas if "Registro" in p.name), None)
    if alvo:
        linhas.append("-" * 70)
        linhas.append(f"PROCESSAMENTO — {alvo.name}")
        linhas.append("-" * 70)
        codigo, saida = executar([
            sys.executable, "07_gerador_certificado.py",
            "--cli", "--planilha", alvo.name,
        ])
        linhas.append(saida.strip())
        linhas.append(f"Codigo de saida: {codigo}")
    else:
        linhas.append("[AVISO] Nenhuma planilha 'Registro*.xlsx' encontrada.")

    # --- Saídas geradas -----------------------------------------------
    linhas.append("")
    linhas.append("-" * 70)
    linhas.append("ARQUIVOS GERADOS")
    linhas.append("-" * 70)
    pasta_cert = PASTA / "certificados"
    if pasta_cert.exists():
        for arq in sorted(pasta_cert.iterdir()):
            kb = arq.stat().st_size / 1024
            linhas.append(f"{arq.name:<44} {kb:>8.1f} KB")
    else:
        linhas.append("(pasta certificados nao encontrada)")
    banco = PASTA / "schulz_calibracao.db"
    if banco.exists():
        kb = banco.stat().st_size / 1024
        linhas.append(f"{banco.name:<44} {kb:>8.1f} KB")

    linhas.append("")
    linhas.append("=" * 70)
    linhas.append("FIM DA EVIDENCIA")
    linhas.append("=" * 70)

    SAIDA.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\nEvidencia gravada em: {SAIDA.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
