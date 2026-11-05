#!/usr/bin/env python3
"""
Backstage Commerce — Ferramenta Open Source de Auditoria Operacional
Script: calculadora_faixa_venenosa.py

Mapeia a "faixa venenosa" (dead zone) de precificação em marketplaces (ex: degrau de R$ 79 no Mercado Livre).
Detecta SKUs onde o aumento de preço bruto gera QUEDA na Margem de Contribuição Líquida devido ao salto de taxa fixa / coparticipação de frete.

Uso:
    python calculadora_faixa_venenosa.py --input produtos.csv --output auditoria_faixa_venenosa.csv
"""

import argparse
import csv
import sys
from typing import List, Dict, Any


def calcular_margem(preco: float, custo: float, taxa_pct: float, taxa_fixa: float, frete_seller: float) -> float:
    """Calcula a margem de contribuição em R$."""
    comissao = preco * (taxa_pct / 100.0)
    deducoes = custo + comissao + taxa_fixa + frete_seller
    return preco - deducoes


def auditar_catalogo(input_path: str, output_path: str) -> None:
    print(f"[*] Lendo catálogo: {input_path}")
    
    with open(input_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        required_cols = {"sku", "titulo", "custo_produto", "preco_venda"}
        if not required_cols.issubset({c.lower() for c in fieldnames}):
            print(f"[!] Erro: O CSV deve conter as colunas: {required_cols}")
            sys.exit(1)

        skus_auditados: List[Dict[str, Any]] = []
        alertas_faixa_venenosa = 0

        for row in reader:
            # Normalizar chaves para lowercase
            r = {k.lower(): v for k, v in row.items()}
            sku = r.get("sku", "SEM_SKU")
            titulo = r.get("titulo", "Sem Título")
            custo = float(r.get("custo_produto", 0.0))
            preco = float(r.get("preco_venda", 0.0))
            taxa_pct = float(r.get("comissao_pct", 16.0))  # Padrão Meli clássico 16% ou premium 19%

            # Regra Meli:
            # Abaixo de R$ 79.00 -> Taxa fixa de R$ 6.00 por item (sem frete grátis obrigatório)
            # A partir de R$ 79.00 -> Sem taxa fixa de R$ 6.00, mas com frete grátis obrigatório (coparticipação do seller ~ R$ 18 a R$ 24)
            # Salto líquido de custo na DRE: ~ R$ 14.00 a R$ 18.00 adicionais
            
            # Ponto de referência logo antes do degrau (R$ 78.90)
            margem_teto_baixo = calcular_margem(78.90, custo, taxa_pct, taxa_fixa=6.00, frete_seller=0.0)
            
            # Cenário atual do SKU
            if preco < 79.00:
                taxa_fixa = 6.00
                frete_seller = 0.0
                status_faixa = "ABAIXO_DO_DEGRAU"
                preco_sugerido = preco
                impacto_margem = 0.0
            else:
                taxa_fixa = 0.0
                # Média conservadora de coparticipação de frete em envios padrão
                frete_seller = float(r.get("copay_frete", 19.50))
                margem_atual = calcular_margem(preco, custo, taxa_pct, taxa_fixa, frete_seller)
                
                # Se o preço está entre R$ 79.00 e o preço de equilíbrio onde margem_atual >= margem_teto_baixo
                # Preço de equilíbrio: P * (1 - taxa_pct/100) - custo - frete_seller = margem_teto_baixo
                # P = (margem_teto_baixo + custo + frete_seller) / (1 - taxa_pct/100)
                preco_equilibrio = (margem_teto_baixo + custo + frete_seller) / (1.0 - (taxa_pct / 100.0))
                
                if preco < preco_equilibrio:
                    status_faixa = "FAIXA_VENENOSA_PREJUIZO"
                    alertas_faixa_venenosa += 1
                    impacto_margem = margem_atual - margem_teto_baixo  # Negativo
                    preco_sugerido = round(preco_equilibrio, 2)
                else:
                    status_faixa = "ACIMA_DO_EQUILIBRIO_SAUDAVEL"
                    preco_sugerido = preco
                    impacto_margem = margem_atual - margem_teto_baixo

            margem_atual = calcular_margem(
                preco, custo, taxa_pct, 
                taxa_fixa=(6.00 if preco < 79.00 else 0.0), 
                frete_seller=(0.0 if preco < 79.00 else float(r.get("copay_frete", 19.50)))
            )

            skus_auditados.append({
                "SKU": sku,
                "Titulo": titulo,
                "Custo_Produto": f"R$ {custo:.2f}",
                "Preco_Atual": f"R$ {preco:.2f}",
                "Margem_Atual": f"R$ {margem_atual:.2f}",
                "Status": status_faixa,
                "Prejuizo_Vs_Teto78": f"R$ {impacto_margem:.2f}" if impacto_margem < 0 else "R$ 0.00",
                "Preco_Sugerido_Equilibrio": f"R$ {preco_sugerido:.2f}"
            })

    # Gravar CSV de auditoria
    out_headers = ["SKU", "Titulo", "Custo_Produto", "Preco_Atual", "Margem_Atual", "Status", "Prejuizo_Vs_Teto78", "Preco_Sugerido_Equilibrio"]
    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_headers)
        writer.writeheader()
        writer.writerows(skus_auditados)

    print("\n" + "="*60)
    print("RELATÓRIO DE AUDITORIA OPERACIONAL — BACKSTAGE COMMERCE")
    print("="*60)
    print(f"Total de SKUs analisados: {len(skus_auditados)}")
    print(f"SKUs na 'Faixa Venenosa' (destruindo margem): {alertas_faixa_venenosa}")
    print(f"Arquivo gerado com as correções sugeridas: {output_path}")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Auditor de Faixa Venenosa de Preços no Mercado Livre — Backstage Commerce")
    parser.add_argument("--input", default="exemplos_catalogo_degrau.csv", help="Caminho do CSV de entrada")
    parser.add_argument("--output", default="auditoria_faixa_venenosa_resultado.csv", help="Caminho do CSV de saída")
    args = parser.parse_args()

    auditar_catalogo(args.input, args.output)


if __name__ == "__main__":
    main()
