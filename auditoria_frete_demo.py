#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
BACKSTAGE COMMERCE - EDIÇÃO PRO #01
Motor de Auditoria de Frete, Cubagem Logística e Detecção de Vazamento de Margem
Integração Oficial com API v2 do Melhor Envio
=============================================================================
Arquivo: edicao_01_script_auditoria.py
Autor: Diretor Técnico & Engenheiro Chefe de Automação
Versão: 1.0.0
Requisitos: Python 3.9+ (Zero dependências externas obrigatórias)
=============================================================================
"""

import os
import sys
import json
import csv
import argparse
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

# Forçar UTF-8 no stdout/stderr no Windows para evitar falhas com caracteres especiais
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Constantes de Engenharia Logística
FATOR_CUBAGEM_PADRAO = 6000  # Padrão rodoviário/aéreo Brasil (cm³ / 6000 = kg)
API_URL_SANDBOX = "https://sandbox.melhorenvio.com.br/api/v2/me/shipment/calculate"
API_URL_PROD = "https://melhorenvio.com.br/api/v2/me/shipment/calculate"

USER_AGENT = "BackstageCommerce-AuditPro/1.0 (contato@backstagecommerce.pro)"


@dataclass
class ItemPedido:
    pedido_id: str
    origem_cep: str
    destino_cep: str
    frete_cobrado_cliente: float
    altura_cm: float
    largura_cm: float
    comprimento_cm: float
    peso_fisico_kg: float
    valor_declarado: float
    transportadora_alvo: str = "Jadlog .Package"


@dataclass
class ResultadoAuditoria:
    pedido_id: str
    origem_cep: str
    destino_cep: str
    peso_fisico_kg: float
    peso_cubado_kg: float
    peso_tarifado_kg: float
    excesso_cubagem_pct: float
    frete_cobrado: float
    custo_melhor_envio: float
    servico_cotado: str
    saldo_margem: float
    status_auditoria: str
    severidade: str
    recomendacao_tecnica: str


def sanitizar_cep(cep: Any) -> str:
    """Remove caracteres não numéricos e garante 8 dígitos com zero à esquerda."""
    numeros = "".join(ch for ch in str(cep) if ch.isdigit())
    return numeros.zfill(8)[:8]


def calcular_cubagem(comprimento: float, largura: float, altura: float, peso_fisico: float, fator: int = FATOR_CUBAGEM_PADRAO) -> Dict[str, Any]:
    """Calcula o peso volumétrico e determina o peso tarifado."""
    volume_cm3 = comprimento * largura * altura
    peso_cubado = round(volume_cm3 / fator, 3)
    peso_tarifado = max(peso_fisico, peso_cubado)
    penalidade = peso_cubado > peso_fisico
    excesso_pct = round(((peso_cubado - peso_fisico) / peso_fisico) * 100, 1) if peso_fisico > 0 and penalidade else 0.0

    return {
        "volume_cm3": volume_cm3,
        "peso_cubado_kg": peso_cubado,
        "peso_tarifado_kg": peso_tarifado,
        "penalidade_cubagem": penalidade,
        "excesso_cubagem_pct": excesso_pct
    }


def consultar_melhor_envio(
    item: ItemPedido,
    peso_tarifado: float,
    token: str,
    usar_sandbox: bool = True
) -> List[Dict[str, Any]]:
    """Realiza requisição HTTP direta para a API do Melhor Envio usando a standard library."""
    url = API_URL_SANDBOX if usar_sandbox else API_URL_PROD

    payload = {
        "from": {"postal_code": item.origem_cep},
        "to": {"postal_code": item.destino_cep},
        "package": {
            "height": max(item.altura_cm, 2.0),
            "width": max(item.largura_cm, 11.0),
            "length": max(item.comprimento_cm, 16.0),
            "weight": max(peso_tarifado, 0.1)
        },
        "options": {
            "insurance_value": max(item.valor_declarado, 10.0),
            "receipt": False,
            "own_hand": False
        }
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.strip()}",
        "User-Agent": USER_AGENT
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            dados = json.loads(response.read().decode("utf-8"))
            if isinstance(dados, list):
                return dados
            elif isinstance(dados, dict) and "data" in dados:
                return dados["data"]
            return []
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", errors="ignore")
        if e.code == 401:
            raise PermissionError("Token do Melhor Envio inválido ou expirado (HTTP 401).")
        raise RuntimeError(f"Erro na API Melhor Envio (HTTP {e.code}): {corpo}")
    except Exception as exc:
        raise RuntimeError(f"Falha de conexão com Melhor Envio: {str(exc)}")


def auditar_pedido(
    item: ItemPedido,
    token: Optional[str] = None,
    usar_sandbox: bool = True,
    fator_cubagem: int = FATOR_CUBAGEM_PADRAO,
    modo_simulacao: bool = False
) -> ResultadoAuditoria:
    """Executa o ciclo completo de auditoria para um pedido."""
    cubagem = calcular_cubagem(
        item.comprimento_cm,
        item.largura_cm,
        item.altura_cm,
        item.peso_fisico_kg,
        fator_cubagem
    )

    custo_real = 0.0
    servico_escolhido = "Indisponível"

    if modo_simulacao or not token:
        # Modo de simulação heurística calibrado com tabelas reais do setor
        custo_base_km = 14.50
        peso_ref = cubagem["peso_tarifado_kg"]
        custo_real = round(custo_base_km + (peso_ref * 4.80) + (item.valor_declarado * 0.007), 2)
        servico_escolhido = f"{item.transportadora_alvo} (Estimado)"
    else:
        try:
            cotacoes = consultar_melhor_envio(item, cubagem["peso_tarifado_kg"], token, usar_sandbox)
            validas = [c for c in cotacoes if not c.get("error") and float(c.get("price") or 0) > 0]
            if validas:
                match = next((c for c in validas if item.transportadora_alvo.lower() in c.get("name", "").lower()), validas[0])
                custo_real = float(match.get("price", 0))
                servico_escolhido = f"{match.get('name', 'N/A')} ({match.get('company', {}).get('name', '')})"
            else:
                custo_real = 0.0
                servico_escolhido = "Nenhuma transportadora disponível"
        except Exception as err:
            servico_escolhido = f"Erro API: {str(err)[:40]}"
            custo_real = 0.0

    saldo = round(item.frete_cobrado_cliente - custo_real, 2)

    if custo_real == 0.0:
        status = "FALHA_COTACAO"
        severidade = "ALERTA"
        recomendacao = "Falha ao obter cotação real. Valide CEPs e restrições de dimensões mínimas."
    elif saldo < -10.0:
        status = "PREJUIZO_CRITICO"
        severidade = "CRITICA"
        recomendacao = f"Prejuízo severo de R$ {abs(saldo):.2f}. A caixa está tarifando {cubagem['peso_tarifado_kg']}kg. Readeque o tamanho da caixa imediatamente."
    elif saldo < 0.0:
        status = "PREJUIZO_LEVE"
        severidade = "MEDIA"
        recomendacao = f"Evasão de margem de R$ {abs(saldo):.2f}. Reajuste a margem de segurança no checkout da loja."
    elif cubagem["penalidade_cubagem"] and cubagem["excesso_cubagem_pct"] > 40:
        status = "DESPERDICIO_CUBAGEM"
        severidade = "BAIXA"
        recomendacao = f"Margem positiva, porém transportando 'vento': {cubagem['excesso_cubagem_pct']}% acima do peso físico. Migre para envelopes ou caixas menores para lucrar mais."
    else:
        status = "MARGEM_SAUDAVEL"
        severidade = "OK"
        recomendacao = "Operação equilibrada. Frete cobrado cobre integralmente o custo logístico."

    return ResultadoAuditoria(
        pedido_id=item.pedido_id,
        origem_cep=item.origem_cep,
        destino_cep=item.destino_cep,
        peso_fisico_kg=item.peso_fisico_kg,
        peso_cubado_kg=cubagem["peso_cubado_kg"],
        peso_tarifado_kg=cubagem["peso_tarifado_kg"],
        excesso_cubagem_pct=cubagem["excesso_cubagem_pct"],
        frete_cobrado=item.frete_cobrado_cliente,
        custo_melhor_envio=custo_real,
        servico_cotado=servico_escolhido,
        saldo_margem=saldo,
        status_auditoria=status,
        severidade=severidade,
        recomendacao_tecnica=recomendacao
    )


def gerar_lote_demonstrativo() -> List[ItemPedido]:
    """Gera um lote de pedidos representativos de cenários reais de e-commerce."""
    return [
        ItemPedido(
            pedido_id="PED-1001",
            origem_cep="01001000",
            destino_cep="20040002",
            frete_cobrado_cliente=22.90,
            altura_cm=25.0,
            largura_cm=35.0,
            comprimento_cm=45.0,
            peso_fisico_kg=1.10,
            valor_declarado=180.00,
            transportadora_alvo="Jadlog .Package"
        ),
        ItemPedido(
            pedido_id="PED-1002",
            origem_cep="01001000",
            destino_cep="30130000",
            frete_cobrado_cliente=19.50,
            altura_cm=4.0,
            largura_cm=20.0,
            comprimento_cm=25.0,
            peso_fisico_kg=0.35,
            valor_declarado=89.00,
            transportadora_alvo="Correios PAC"
        ),
        ItemPedido(
            pedido_id="PED-1003",
            origem_cep="01001000",
            destino_cep="80010000",
            frete_cobrado_cliente=35.00,
            altura_cm=30.0,
            largura_cm=30.0,
            comprimento_cm=40.0,
            peso_fisico_kg=0.80,
            valor_declarado=120.00,
            transportadora_alvo="Jadlog .Package"
        ),
        ItemPedido(
            pedido_id="PED-1004",
            origem_cep="01001000",
            destino_cep="40020000",
            frete_cobrado_cliente=48.00,
            altura_cm=15.0,
            largura_cm=20.0,
            comprimento_cm=20.0,
            peso_fisico_kg=4.20,
            valor_declarado=320.00,
            transportadora_alvo="Correios SEDEX"
        ),
        ItemPedido(
            pedido_id="PED-1005",
            origem_cep="01001000",
            destino_cep="70040010",
            frete_cobrado_cliente=18.00,
            altura_cm=20.0,
            largura_cm=25.0,
            comprimento_cm=30.0,
            peso_fisico_kg=1.50,
            valor_declarado=140.00,
            transportadora_alvo="Jadlog .Package"
        )
    ]


def carregar_csv(caminho: str) -> List[ItemPedido]:
    """Carrega pedidos de um arquivo CSV estruturado."""
    pedidos = []
    with open(caminho, mode="r", encoding="utf-8-sig") as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            pedidos.append(ItemPedido(
                pedido_id=linha.get("pedido_id", f"PED-{len(pedidos)+1}"),
                origem_cep=sanitizar_cep(linha.get("origem_cep", "01001000")),
                destino_cep=sanitizar_cep(linha.get("destino_cep", "20040002")),
                frete_cobrado_cliente=float(linha.get("frete_cobrado", 0)),
                altura_cm=float(linha.get("altura_cm", 10)),
                largura_cm=float(linha.get("largura_cm", 15)),
                comprimento_cm=float(linha.get("comprimento_cm", 20)),
                peso_fisico_kg=float(linha.get("peso_kg", 0.5)),
                valor_declarado=float(linha.get("valor_declarado", 50)),
                transportadora_alvo=linha.get("transportadora", "Jadlog .Package")
            ))
    return pedidos


def imprimir_relatorio_executivo(resultados: List[ResultadoAuditoria]):
    """Gera o painel visual no terminal com métricas de engenharia e impacto financeiro."""
    total_pedidos = len(resultados)
    pedidos_prejuizo = [r for r in resultados if r.saldo_margem < 0]
    total_cobrado = sum(r.frete_cobrado for r in resultados)
    total_custo = sum(r.custo_melhor_envio for r in resultados)
    saldo_consolidado = round(total_cobrado - total_custo, 2)
    evasao_total = round(sum(abs(r.saldo_margem) for r in pedidos_prejuizo), 2)
    pedidos_penalizados_cubagem = [r for r in resultados if r.peso_cubado_kg > r.peso_fisico_kg]

    print("\n" + "=" * 80)
    print(" 🚀 BACKSTAGE COMMERCE | RELATÓRIO EXECUTIVO DE AUDITORIA DE FRETE")
    print("=" * 80)
    print(f" Total de Pedidos Auditados    : {total_pedidos}")
    print(f" Pedidos com Margem Negativa   : {len(pedidos_prejuizo)} ({len(pedidos_prejuizo)/total_pedidos*100:.1f}%)")
    print(f" Pedidos Penalizados na Cubagem: {len(pedidos_penalizados_cubagem)} ({len(pedidos_penalizados_cubagem)/total_pedidos*100:.1f}%)")
    print(f" Total Cobrado no Checkout     : R$ {total_cobrado:,.2f}")
    print(f" Custo Real das Transportadoras : R$ {total_custo:,.2f}")
    print(f" Saldo Líquido Operacional     : R$ {saldo_consolidado:,.2f}")
    print(f" Evasão / Prejuízo Detectado   : R$ {evasao_total:,.2f}")
    print("-" * 80)
    print(f"{'ID':<10} | {'FÍSICO':<8} | {'CUBADO':<8} | {'COBRADO':<10} | {'REAL':<10} | {'SALDO':<10} | {'STATUS'}")
    print("-" * 80)

    for r in resultados:
        saldo_fmt = f"{'+' if r.saldo_margem >= 0 else ''}{r.saldo_margem:.2f}"
        print(f"{r.pedido_id:<10} | {r.peso_fisico_kg:<8.2f} | {r.peso_cubado_kg:<8.2f} | R${r.frete_cobrado:<8.2f} | R${r.custo_melhor_envio:<8.2f} | R${saldo_fmt:<8} | {r.status_auditoria}")

    print("-" * 80)
    print(" 💡 RECOMENDAÇÕES DIRETIVAS DE ENGENHARIA:")
    for r in resultados:
        if r.severidade in ("CRITICA", "MEDIA"):
            print(f"  • [{r.pedido_id} - {r.severidade}]: {r.recomendacao_tecnica}")
    print("=" * 80 + "\n")


def salvar_resultados(resultados: List[ResultadoAuditoria], caminho_csv: str, caminho_json: Optional[str] = None):
    """Exporta os resultados para CSV e opcionalmente JSON."""
    linhas = [asdict(r) for r in resultados]
    if linhas:
        with open(caminho_csv, mode="w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
            escritor.writeheader()
            escritor.writerows(linhas)
        print(f"✅ Relatório CSV salvo com sucesso em: {caminho_csv}")

    if caminho_json:
        with open(caminho_json, mode="w", encoding="utf-8") as f:
            json.dump(linhas, f, indent=2, ensure_ascii=False)
        print(f"✅ Relatório JSON salvo com sucesso em: {caminho_json}")


def main():
    parser = argparse.ArgumentParser(
        description="Backstage Commerce PRO #01 - Auditoria de Frete e Cubagem via Melhor Envio"
    )
    parser.add_argument("--token", help="Token Bearer da API do Melhor Envio (ou defina MELHOR_ENVIO_TOKEN)")
    parser.add_argument("--prod", action="store_true", help="Usa endpoint de Produção (padrão é Sandbox)")
    parser.add_argument("--input", help="Caminho para arquivo CSV com os pedidos a auditar")
    parser.add_argument("--demo", action="store_true", help="Executa com lote de demonstração realista")
    parser.add_argument("--output", default="auditoria_resultado.csv", help="Caminho do CSV de saída")
    parser.add_argument("--json", help="Caminho para exportar relatório estruturado em JSON")
    parser.add_argument("--fator-cubagem", type=int, default=FATOR_CUBAGEM_PADRAO, help="Fator de cubagem (padrão 6000)")

    args = parser.parse_args()

    token = args.token or os.environ.get("MELHOR_ENVIO_TOKEN")
    usar_sandbox = not args.prod

    if args.input:
        pedidos = carregar_csv(args.input)
    elif args.demo or not token:
        print("\nℹ️  Iniciando em modo DEMO/SIMULAÇÃO (sem token real obrigatório).")
        pedidos = gerar_lote_demonstrativo()
    else:
        print("Erro: Forneça um arquivo via --input ou use a flag --demo para testar.")
        sys.exit(1)

    modo_simulacao = token is None

    resultados: List[ResultadoAuditoria] = []
    print(f"Iniciando auditoria de {len(pedidos)} pedidos...")

    for pedido in pedidos:
        res = auditar_pedido(
            item=pedido,
            token=token,
            usar_sandbox=usar_sandbox,
            fator_cubagem=args.fator_cubagem,
            modo_simulacao=modo_simulacao
        )
        resultados.append(res)

    imprimir_relatorio_executivo(resultados)
    salvar_resultados(resultados, args.output, args.json)


if __name__ == "__main__":
    main()
