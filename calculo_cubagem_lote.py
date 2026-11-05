#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
BACKSTAGE COMMERCE — SPRINT DE ENGENHARIA | DIA 2
Calculadora em Lote de Cubagem e Detecção de 'Vento Logístico'
=============================================================================
Arquivo: calculo_cubagem_lote.py
Autor: Forge (Tech Lead) & Volt (Automações) | Squad Backstage Commerce
Versão: 1.0.0
Requisitos: Python 3.9+ (Zero dependências externas)
=============================================================================
"""

import os
import sys
import csv
import json
import argparse
from typing import List, Dict, Any, Optional

# Suporte a UTF-8 no Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def calcular_cubagem_item(
    comprimento: float,
    largura: float,
    altura: float,
    peso_fisico: float,
    fator: int = 6000
) -> Dict[str, Any]:
    """Calcula o peso volumétrico e detecta distorções de embalagem."""
    volume_cm3 = comprimento * largura * altura
    peso_cubado = round(volume_cm3 / fator, 3)
    peso_tarifado = max(peso_fisico, peso_cubado)
    penalizado = peso_cubado > peso_fisico
    diferenca_peso = round(peso_cubado - peso_fisico, 3) if penalizado else 0.0
    desperdicio_pct = round((diferenca_peso / peso_fisico) * 100, 1) if peso_fisico > 0 and penalizado else 0.0

    return {
        "volume_cm3": volume_cm3,
        "peso_cubado_kg": peso_cubado,
        "peso_tarifado_kg": peso_tarifado,
        "penalizado": penalizado,
        "diferenca_kg": diferenca_peso,
        "desperdicio_pct": desperdicio_pct
    }


def processar_lote_csv(caminho_csv: str, fator: int = 6000) -> List[Dict[str, Any]]:
    """Lê arquivo CSV e processa a cubagem de cada linha."""
    if not os.path.exists(caminho_csv):
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {caminho_csv}")

    resultados = []
    with open(caminho_csv, mode="r", encoding="utf-8-sig") as f:
        leitor = csv.DictReader(f)
        for idx, linha in enumerate(leitor, start=1):
            pedido_id = linha.get("pedido_id") or f"ITEM-{idx:03d}"
            try:
                comp = float(linha.get("comprimento_cm") or linha.get("comprimento") or 20.0)
                larg = float(linha.get("largura_cm") or linha.get("largura") or 15.0)
                alt = float(linha.get("altura_cm") or linha.get("altura") or 10.0)
                peso_f = float(linha.get("peso_kg") or linha.get("peso") or 0.5)
            except ValueError as e:
                print(f"⚠️ Linha {idx} ignorada devido a valor numérico inválido: {e}")
                continue

            calc = calcular_cubagem_item(comp, larg, alt, peso_f, fator)
            resultados.append({
                "item_id": pedido_id,
                "dimensoes_cm": f"{comp:.0f}x{larg:.0f}x{alt:.0f}",
                "peso_fisico_kg": peso_f,
                "peso_cubado_kg": calc["peso_cubado_kg"],
                "peso_tarifado_kg": calc["peso_tarifado_kg"],
                "penalizado": calc["penalizado"],
                "excesso_kg": calc["diferenca_kg"],
                "desperdicio_pct": calc["desperdicio_pct"],
                "classificacao": (
                    "CRÍTICO (Vento Severo)" if calc["desperdicio_pct"] > 100 else
                    "ATENÇÃO (Cubado > Físico)" if calc["penalizado"] else
                    "OTIMIZADO (Físico >= Cubado)"
                )
            })

    return resultados


def imprimir_painel(resultados: List[Dict[str, Any]], fator: int):
    """Exibe painel resumido das distorções de frete."""
    total = len(resultados)
    if total == 0:
        print("Nenhum dado processado.")
        return

    penalizados = [r for r in resultados if r["penalizado"]]
    criticos = [r for r in resultados if r["desperdicio_pct"] > 100]
    total_excesso_kg = sum(r["excesso_kg"] for r in penalizados)

    print("\n" + "=" * 80)
    print(f" 📦 AUDITORIA DE CUBAGEM EM LOTE — BACKSTAGE COMMERCE (Fator {fator})")
    print("=" * 80)
    print(f" Total de Embalagens Auditadas : {total}")
    print(f" Penalizadas na Cubagem       : {len(penalizados)} ({len(penalizados)/total*100:.1f}%)")
    print(f" Embalagens Críticas (>100%)   : {len(criticos)} ({len(criticos)/total*100:.1f}%)")
    print(f" 'Vento' Total Faturado em KG : {total_excesso_kg:.2f} kg extras cobrados")
    print("-" * 80)
    print(f"{'ID':<12} | {'DIMENSÕES':<11} | {'FÍSICO':<8} | {'CUBADO':<8} | {'TARIFADO':<8} | {'STATUS'}")
    print("-" * 80)

    for r in resultados:
        print(f"{r['item_id']:<12} | {r['dimensoes_cm']:<11} | {r['peso_fisico_kg']:<8.2f} | {r['peso_cubado_kg']:<8.2f} | {r['peso_tarifado_kg']:<8.2f} | {r['classificacao']}")

    print("=" * 80)
    print(" 💡 REGRA DE ENGENHARIA LOGÍSTICA:")
    print("  Toda embalagem onde o peso cubado supera o peso físico representa frete pago")
    print("  para transportar ar. Reduzir 2cm a 3cm nas três dimensões pode economizar")
    print("  até R$ 12 a R$ 25 por pedido em transportadoras rodoviárias.")
    print("=" * 80 + "\n")


def salvar_csv(resultados: List[Dict[str, Any]], destino: str):
    """Salva os resultados em formato CSV."""
    if not resultados:
        return
    with open(destino, mode="w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(resultados[0].keys()))
        escritor.writeheader()
        escritor.writerows(resultados)
    print(f"✅ Relatório exportado com sucesso em: {destino}")


def main():
    parser = argparse.ArgumentParser(
        description="Calculadora em Lote de Cubagem e Detecção de 'Vento Logístico' — Backstage Commerce"
    )
    parser.add_argument("--input", required=True, help="Arquivo CSV de entrada com as dimensões dos pedidos")
    parser.add_argument("--output", default="cubagem_lote_resultado.csv", help="Arquivo CSV de saída")
    parser.add_argument("--fator", type=int, default=6000, help="Fator de cubagem (6000 padrão BR, 5000 expresso/aéreo)")
    parser.add_argument("--json", help="Exportar resultado também em JSON estruturado")

    args = parser.parse_args()

    resultados = processar_lote_csv(args.input, args.fator)
    imprimir_painel(resultados, args.fator)
    salvar_csv(resultados, args.output)

    if args.json:
        with open(args.json, mode="w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON estruturado salvo em: {args.json}")


if __name__ == "__main__":
    main()
