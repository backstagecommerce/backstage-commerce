#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
BACKSTAGE COMMERCE - ENGENHARIA DE LOGÍSTICA & E-COMMERCE
Simulação de Cubagem em Lote e Peso Teórico (CSV)
=============================================================================
Arquivo: cubagem_lote_csv.py
Autor: Volt (Engenheiro de Automações & Integrações)
Revisor: Forge (Tech Lead) / Censor (QA)
Versão: 1.0.0
Requisitos: Python 3.9+ (Zero dependências externas obrigatórias)
Uso:
    python cubagem_lote_csv.py --demo
    python cubagem_lote_csv.py --input pedidos.csv --output resultado_auditoria.csv
=============================================================================
"""

import sys
import os
import csv
import argparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional

# Forçar UTF-8 no Windows para evitar falhas de codificação (cp1252 / cmd)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Default da simulação; consulte o fator aplicável no contrato de transporte
# Fórmula: (Comprimento x Largura x Altura em cm) / Fator = Peso Cubado em kg
FATOR_CUBAGEM_PADRAO = 6000


@dataclass
class RegistroEnvio:
    pedido_id: str
    sku: str
    peso_declarado_kg: float
    altura_cm: float
    largura_cm: float
    comprimento_cm: float
    fator_cubagem: int = FATOR_CUBAGEM_PADRAO


@dataclass
class ResultadoCubagem:
    pedido_id: str
    sku: str
    volume_cm3: float
    peso_declarado_kg: float
    peso_cubado_kg: float
    peso_tributavel_kg: float
    sofreu_cubagem: bool
    diferenca_kg: float
    percentual_acrescimo: float
    status: str
    observacao: str


def calcular_cubagem(registro: RegistroEnvio) -> ResultadoCubagem:
    """
    Executa a auditoria dimensional de um pacote individual.
    Simula o maior entre peso físico e cubado; não verifica cobrança ou contrato.
    """
    volume = registro.comprimento_cm * registro.largura_cm * registro.altura_cm
    fator = registro.fator_cubagem if registro.fator_cubagem > 0 else FATOR_CUBAGEM_PADRAO
    peso_cubado = round(volume / fator, 3)
    peso_declarado = round(registro.peso_declarado_kg, 3)

    sofreu_cubagem = peso_cubado > peso_declarado
    peso_tributavel = max(peso_declarado, peso_cubado)
    diferenca = round(peso_tributavel - peso_declarado, 3)

    if peso_declarado > 0:
        percentual = round((diferenca / peso_declarado) * 100, 1)
    else:
        percentual = 0.0

    if sofreu_cubagem:
        status = "ALERTA: EXCESSO TEÓRICO DE CUBAGEM"
        obs = f"Simulação baseada em volume (+{diferenca:.3f} kg teóricos)"
    else:
        status = "OK: PESO REAL"
        obs = "Peso físico predominante sobre cubagem"

    return ResultadoCubagem(
        pedido_id=registro.pedido_id,
        sku=registro.sku,
        volume_cm3=round(volume, 1),
        peso_declarado_kg=peso_declarado,
        peso_cubado_kg=peso_cubado,
        peso_tributavel_kg=peso_tributavel,
        sofreu_cubagem=sofreu_cubagem,
        diferenca_kg=diferenca,
        percentual_acrescimo=percentual,
        status=status,
        observacao=obs,
    )


def gerar_dados_demo() -> List[RegistroEnvio]:
    """
    Retorna lote sintético ilustrativo de e-commerce e marketplaces.
    Demonstra armadilhas comuns: calçados, travesseiros, luminárias e caixas superdimensionadas.
    """
    return [
        RegistroEnvio(
            pedido_id="PED-10291",
            sku="TENIS-CORRIDA-PRO-41",
            peso_declarado_kg=0.850,
            altura_cm=16.0,
            largura_cm=24.0,
            comprimento_cm=35.0,
        ),
        RegistroEnvio(
            pedido_id="PED-10292",
            sku="TRAVESSEIRO-VISCOELASTICO-PAR",
            peso_declarado_kg=1.200,
            altura_cm=28.0,
            largura_cm=45.0,
            comprimento_cm=65.0,
        ),
        RegistroEnvio(
            pedido_id="PED-10293",
            sku="LUMINARIA-ARTICULADA-MESA",
            peso_declarado_kg=0.900,
            altura_cm=18.0,
            largura_cm=22.0,
            comprimento_cm=48.0,
        ),
        RegistroEnvio(
            pedido_id="PED-10294",
            sku="SUPORTE-NOTEBOOK-ALUMINIO",
            peso_declarado_kg=1.450,
            altura_cm=6.0,
            largura_cm=26.0,
            comprimento_cm=30.0,
        ),
        RegistroEnvio(
            pedido_id="PED-10295",
            sku="EDREDOM-CASAL-MICROFIBRA",
            peso_declarado_kg=2.100,
            altura_cm=35.0,
            largura_cm=50.0,
            comprimento_cm=55.0,
        ),
        RegistroEnvio(
            pedido_id="PED-10296",
            sku="SMARTWATCH-SPORT-PRETO",
            peso_declarado_kg=0.250,
            altura_cm=8.0,
            largura_cm=12.0,
            comprimento_cm=15.0,
        ),
        RegistroEnvio(
            pedido_id="PED-10297",
            sku="CADEIRA-GAMER-PISTON-GAS",
            peso_declarado_kg=16.500,
            altura_cm=32.0,
            largura_cm=68.0,
            comprimento_cm=84.0,
        ),
    ]


def processar_lote_csv(caminho_csv: str, fator_padrao: int = FATOR_CUBAGEM_PADRAO) -> List[ResultadoCubagem]:
    """Lê arquivo CSV e processa cada linha calculando a cubagem."""
    if not os.path.exists(caminho_csv):
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {caminho_csv}")

    registros: List[RegistroEnvio] = []
    with open(caminho_csv, mode="r", encoding="utf-8-sig") as f:
        leitor = csv.DictReader(f)
        for idx, linha in enumerate(leitor, start=2):
            try:
                pedido_id = linha.get("pedido_id") or linha.get("pedido") or f"LINHA-{idx}"
                sku = linha.get("sku") or linha.get("produto") or "N/A"
                peso = float(str(linha.get("peso_kg") or linha.get("peso") or 0).replace(",", "."))
                altura = float(str(linha.get("altura_cm") or linha.get("altura") or 0).replace(",", "."))
                largura = float(str(linha.get("largura_cm") or linha.get("largura") or 0).replace(",", "."))
                comp = float(str(linha.get("comprimento_cm") or linha.get("comprimento") or 0).replace(",", "."))
                fator = int(linha.get("fator_cubagem") or fator_padrao)

                registros.append(
                    RegistroEnvio(
                        pedido_id=pedido_id.strip(),
                        sku=sku.strip(),
                        peso_declarado_kg=peso,
                        altura_cm=altura,
                        largura_cm=largura,
                        comprimento_cm=comp,
                        fator_cubagem=fator,
                    )
                )
            except (ValueError, KeyError) as e:
                print(f"[AVISO] Linha {idx} ignorada devido a formato inválido: {e}", file=sys.stderr)

    return [calcular_cubagem(reg) for reg in registros]


def exportar_csv(resultados: List[ResultadoCubagem], caminho_saida: str) -> None:
    """Grava os resultados auditados em arquivo CSV para análise contábil/financeira."""
    campos = [
        "pedido_id",
        "sku",
        "volume_cm3",
        "peso_declarado_kg",
        "peso_cubado_kg",
        "peso_tributavel_kg",
        "sofreu_cubagem",
        "diferenca_kg",
        "percentual_acrescimo",
        "status",
        "observacao",
    ]
    with open(caminho_saida, mode="w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        for res in resultados:
            escritor.writerow(asdict(res))


def imprimir_relatorio_terminal(resultados: List[ResultadoCubagem]) -> None:
    """Renderiza relatório executivo formatado diretamente no terminal."""
    total_pacotes = len(resultados)
    pacotes_com_sobretaxa = sum(1 for r in resultados if r.sofreu_cubagem)
    taxa_vazamento = (pacotes_com_sobretaxa / total_pacotes * 100) if total_pacotes > 0 else 0.0

    peso_declarado_total = sum(r.peso_declarado_kg for r in resultados)
    peso_cobrado_total = sum(r.peso_tributavel_kg for r in resultados)
    excesso_peso_total = peso_cobrado_total - peso_declarado_total

    print("=" * 88)
    print("  BACKSTAGE COMMERCE — SIMULAÇÃO DE CUBAGEM EM LOTE (SEM CONFERÊNCIA DE FATURA)")
    print("=" * 88)
    print(f"{'PEDIDO':<12} {'SKU':<28} {'DECLARADO':<10} {'CUBADO':<10} {'TRIBUTADO':<10} {'STATUS':<15}")
    print("-" * 88)

    for r in resultados:
        flag = " [!] ALERTA" if r.sofreu_cubagem else " [OK]"
        print(
            f"{r.pedido_id:<12} {r.sku[:26]:<28} {r.peso_declarado_kg:>7.3f} kg "
            f"{r.peso_cubado_kg:>7.3f} kg {r.peso_tributavel_kg:>7.3f} kg {flag:<15}"
        )

    print("=" * 88)
    print("RESUMO EXECUTIVO DO LOTE:")
    print(f"  * Total de Pacotes Analisados:     {total_pacotes}")
    print(f"  * Pacotes com Excesso Teórico:    {pacotes_com_sobretaxa} ({taxa_vazamento:.1f}% do lote)")
    print(f"  * Peso Físico Declarado:          {peso_declarado_total:.3f} kg")
    print(f"  * Peso Teórico max(físico,cubado): {peso_cobrado_total:.3f} kg")
    print(f"  * Excesso Teórico de Cubagem:     +{excesso_peso_total:.3f} kg (+{(excesso_peso_total/peso_declarado_total*100 if peso_declarado_total>0 else 0):.1f}%)")
    print("=" * 88)
    print("DIAGNÓSTICO TÉCNICO:")
    if excesso_peso_total > 0:
        print(
            f"  SIMULAÇÃO: {excesso_peso_total:.3f} kg teóricos acima do peso físico declarado.\n"
            f"  Cobrança, repasse no checkout e economia financeira não foram verificados.\n"
            f"  Confira dimensões, fator e faixas no contrato antes de comparar com a fatura."
        )
    else:
        print("  SIMULAÇÃO SEM EXCESSO: Peso físico igual ou superior ao cubado em todas as embalagens.")
    print("=" * 88)


def main():
    parser = argparse.ArgumentParser(
        description="Backstage Commerce - Simulação de Cubagem Logística em Lote (CSV), sem comprovação de cobrança"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Executa demonstração com lote sintético e fator fixo 6000 (ignora --fator)",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="CSV de entrada: pedido_id, sku, peso_kg, altura_cm, largura_cm, comprimento_cm; fator_cubagem opcional por linha prevalece sobre --fator",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Caminho opcional para salvar o CSV auditado com resultados detalhados",
    )
    parser.add_argument(
        "--fator",
        type=int,
        default=FATOR_CUBAGEM_PADRAO,
        help=f"Fator conforme contrato para CSV sem fator por linha (default da simulação: {FATOR_CUBAGEM_PADRAO}; não se aplica ao --demo)",
    )

    args = parser.parse_args()

    if not args.demo and not args.input:
        parser.print_help()
        print("\n[DICA] Para testar imediatamente, execute:\n  python cubagem_lote_csv.py --demo\n")
        sys.exit(0)

    try:
        if args.demo:
            print("[INFO] Executando lote de demonstração...")
            registros = gerar_dados_demo()
            resultados = [calcular_cubagem(reg) for reg in registros]
        else:
            print(f"[INFO] Processando arquivo: {args.input} (Fator: {args.fator})...")
            resultados = processar_lote_csv(args.input, args.fator)

        imprimir_relatorio_terminal(resultados)

        if args.output:
            exportar_csv(resultados, args.output)
            print(f"\n[SUCESSO] Relatório detalhado exportado com sucesso em: {args.output}")

    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha ao processar auditoria de cubagem: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
