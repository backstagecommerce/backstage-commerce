#!/usr/bin/env python3
"""
Backstage Commerce — Ferramenta Open Source de Auditoria Operacional
Script: calculadora_faixa_venenosa.py

Simula a "faixa venenosa" de precificação em um cenário sintético, sem regra tarifária vigente.
Fixos: degrau de R$ 79, referência de R$ 78,90 e taxa de R$ 6 abaixo do degrau.
CSV: comissao_pct (default 16%) e copay_frete (default R$ 19,50, usado a partir do degrau).
Compara a contribuição no cenário com a referência; não inclui tributos nem todos os custos da operação.

Uso:
    python calculadora_faixa_venenosa.py --input produtos.csv --output auditoria_faixa_venenosa.csv
"""

import argparse
import csv
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import List, Dict, Any


class ErroCSV(ValueError):
    """Entrada inválida com localização física no arquivo."""

    def __init__(self, linha: int, campo: str, motivo: str):
        super().__init__(f"linha {linha}, campo {campo}: {motivo}")


def numero_finito(valor: float, linha: int, campo: str) -> float:
    if not math.isfinite(valor):
        raise ErroCSV(linha, campo, "valor ou resultado intermediário não finito")
    return valor


def ler_catalogo(input_path: str) -> List[Dict[str, Any]]:
    """Valida o CSV inteiro antes de iniciar cálculos ou abrir a saída."""
    registros = []
    obrigatorios = ("sku", "titulo", "custo_produto", "preco_venda")
    with open(input_path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, strict=True)
        try:
            header = next(reader, [])
            linha = max(reader.line_num, 1)
            if not header:
                raise ErroCSV(linha, "cabeçalho", "ausente ou vazio")
            nomes = [nome.lower() for nome in header]
            vistos = set()
            for nome in nomes:
                if not nome.strip():
                    raise ErroCSV(linha, "cabeçalho", "nome de coluna vazio")
                if nome in vistos:
                    raise ErroCSV(linha, nome, "cabeçalho duplicado")
                vistos.add(nome)
            for campo in obrigatorios:
                if campo not in nomes:
                    raise ErroCSV(linha, campo, "coluna obrigatória ausente")
            for cells in reader:
                linha = reader.line_num
                if not cells:
                    continue  # Linhas físicas vazias não constituem registros.
                if len(cells) != len(nomes):
                    campo = nomes[len(cells)] if len(cells) < len(nomes) else "registro"
                    raise ErroCSV(linha, campo, "quantidade de células diferente do cabeçalho")
                registro = dict(zip(nomes, cells))
                for campo in obrigatorios:
                    if not registro[campo].strip():
                        raise ErroCSV(linha, campo, "célula obrigatória vazia")
                for campo, default in (("custo_produto", None), ("preco_venda", None),
                                       ("comissao_pct", 16.0), ("copay_frete", 19.50)):
                    raw = registro.get(campo, default)
                    if isinstance(raw, str) and not raw.strip():
                        raise ErroCSV(linha, campo, "célula numérica vazia")
                    try:
                        valor = float(raw)
                    except (ValueError, OverflowError):
                        raise ErroCSV(linha, campo, "número inválido") from None
                    numero_finito(valor, linha, campo)
                    if valor < 0 or (campo == "preco_venda" and valor == 0):
                        raise ErroCSV(linha, campo, "valor fora do domínio permitido")
                    if campo == "comissao_pct" and valor >= 100:
                        raise ErroCSV(linha, campo, "deve ser menor que 100")
                    registro[campo] = valor
                registro["_linha_fisica"] = linha
                registros.append(registro)
        except csv.Error as exc:
            raise ErroCSV(max(reader.line_num, 1), "CSV", str(exc)) from None
        if not registros:
            raise ErroCSV(max(reader.line_num, 1), "registro", "nenhum registro de dados")
    return registros


def calcular_margem(preco: float, custo: float, taxa_pct: float, taxa_fixa: float, frete_seller: float) -> float:
    """Calcula a margem de contribuição em R$."""
    comissao = preco * (taxa_pct / 100.0)
    deducoes = custo + comissao + taxa_fixa + frete_seller
    if not math.isfinite(comissao) or not math.isfinite(deducoes):
        raise ArithmeticError("comissão ou deduções não finitas")
    return preco - deducoes


def auditar_catalogo(input_path: str, output_path: str) -> None:
    entrada, saida = Path(input_path), Path(output_path)
    if entrada.resolve() == saida.resolve() or (
        entrada.exists() and saida.exists() and os.path.samefile(entrada, saida)
    ):
        raise ErroCSV(1, "output", "entrada e saída apontam para o mesmo arquivo")
    print(f"[*] Lendo catálogo: {input_path}")
    registros = ler_catalogo(input_path)
    # Todos os registros já passaram pela validação estrutural e numérica.
    skus_auditados: List[Dict[str, Any]] = []
    alertas_faixa_venenosa = 0

    for r in registros:
        linha = r["_linha_fisica"]
        sku = r.get("sku", "SEM_SKU")
        titulo = r.get("titulo", "Sem Título")
        custo = float(r.get("custo_produto", 0.0))
        preco = float(r.get("preco_venda", 0.0))
        taxa_pct = float(r.get("comissao_pct", 16.0))  # Default sintético; configurável no CSV

        # Cenário sintético fixo; não representa tabela vigente de marketplace:
        # Abaixo de R$ 79.00 -> taxa fixa de R$ 6.00 e frete zero no modelo.
        # A partir de R$ 79.00 -> taxa fixa zero e copay_frete do CSV (default R$ 19.50).
        # Degrau, referência de R$ 78.90 e taxa de R$ 6.00 não são configuráveis.
        
        # Ponto de referência logo antes do degrau (R$ 78.90)
        try:
            margem_teto_baixo = calcular_margem(78.90, custo, taxa_pct, taxa_fixa=6.00, frete_seller=0.0)
        except ArithmeticError as exc:
            raise ErroCSV(linha, "calculo", str(exc)) from None
        numero_finito(margem_teto_baixo, linha, "margem_referencia")
        
        # Cenário atual do SKU
        if preco < 79.00:
            taxa_fixa = 6.00
            frete_seller = 0.0
            status_faixa = "ABAIXO_DO_DEGRAU"
            preco_sugerido = preco
            impacto_margem = 0.0
        else:
            taxa_fixa = 0.0
            # Coparticipação sintética configurável no CSV; default R$ 19.50
            frete_seller = float(r.get("copay_frete", 19.50))
            try:
                margem_atual = calcular_margem(preco, custo, taxa_pct, taxa_fixa, frete_seller)
            except ArithmeticError as exc:
                raise ErroCSV(linha, "calculo", str(exc)) from None
            numero_finito(margem_atual, linha, "margem_atual")
            
            # Se o preço está entre R$ 79.00 e o preço de equilíbrio onde margem_atual >= margem_teto_baixo
            # Preço de equilíbrio: P * (1 - taxa_pct/100) - custo - frete_seller = margem_teto_baixo
            # P = (margem_teto_baixo + custo + frete_seller) / (1 - taxa_pct/100)
            preco_equilibrio = (margem_teto_baixo + custo + frete_seller) / (1.0 - (taxa_pct / 100.0))
            numero_finito(preco_equilibrio, linha, "preco_equilibrio")
            
            if preco < preco_equilibrio:
                status_faixa = "FAIXA_VENENOSA_PREJUIZO"
                alertas_faixa_venenosa += 1
                impacto_margem = margem_atual - margem_teto_baixo  # Negativo
                preco_sugerido = round(preco_equilibrio, 2)
            else:
                status_faixa = "ACIMA_DO_EQUILIBRIO_SAUDAVEL"
                preco_sugerido = preco
                impacto_margem = margem_atual - margem_teto_baixo

        try:
            margem_atual = calcular_margem(
                preco, custo, taxa_pct,
                taxa_fixa=(6.00 if preco < 79.00 else 0.0),
                frete_seller=(0.0 if preco < 79.00 else float(r.get("copay_frete", 19.50)))
            )
        except ArithmeticError as exc:
            raise ErroCSV(linha, "calculo", str(exc)) from None
        numero_finito(margem_atual, linha, "margem_atual")
        numero_finito(impacto_margem, linha, "impacto_margem")

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
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                         dir=saida.parent, prefix=".faixa-", suffix=".tmp",
                                         delete=False) as f:
            temporario = f.name
            writer = csv.DictWriter(f, fieldnames=out_headers)
            writer.writeheader()
            writer.writerows(skus_auditados)
        os.replace(temporario, output_path)
    finally:
        if temporario is not None and os.path.exists(temporario):
            os.unlink(temporario)

    print("\n" + "="*60)
    print("SIMULAÇÃO SINTÉTICA DE CONTRIBUIÇÃO — BACKSTAGE COMMERCE")
    print("="*60)
    print(f"Total de SKUs analisados: {len(skus_auditados)}")
    print(f"SKUs abaixo da contribuição de referência no cenário: {alertas_faixa_venenosa}")
    print(f"Arquivo gerado com os resultados da simulação: {output_path}")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Simulação sintética de faixa venenosa — fixos R$ 79 / R$ 78,90 / R$ 6; copay default R$ 19,50 configurável no CSV. Sem regra tarifária vigente — Backstage Commerce")
    parser.add_argument("--input", default="exemplos_catalogo_degrau.csv", help="Caminho do CSV de entrada")
    parser.add_argument("--output", default="auditoria_faixa_venenosa_resultado.csv", help="Caminho do CSV de saída")
    args = parser.parse_args()

    try:
        auditar_catalogo(args.input, args.output)
    except ErroCSV as exc:
        print(f"[ERRO] {exc}; saída não atualizada", file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        print(f"[ERRO I/O/encoding] {exc}; saída não atualizada", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
