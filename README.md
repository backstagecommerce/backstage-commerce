# Backstage Commerce

**Engenharia aplicada aos bastidores do e-commerce.**

Este laboratório torna custos, dados e automações mais compreensíveis, verificáveis e utilizáveis. A assinatura editorial é simples: **abra os bastidores, confira os números e entenda o código**.

O repositório é voltado a quem opera lojas, marketplaces e integrações e precisa acompanhar o caminho entre pedido, estoque, cobrança e margem. Cada ferramenta deve explicar o problema que resolve, as entradas esperadas, como reproduzir o resultado e onde estão seus limites.

## Identidade e princípios

- Faturamento sozinho não explica resultado; custos e premissas precisam fechar.
- Uma automação precisa tratar falhas, entradas incompletas e limites conhecidos.
- Um exemplo reproduzível vale mais que um print sem contexto.
- O trabalho manual deve ser compreendido antes de ser automatizado.
- Exemplos demonstrativos usam dados sintéticos e não representam clientes, tarifas ou resultados reais.

Newsletter e produtos Pro são caminhos complementares. O uso dos exemplos públicos não depende de compra nem de cadastro.

## Índice de ferramentas verificadas

| Recurso | Estado nesta revisão | O que faz | Dependências e limites |
| --- | --- | --- | --- |
| [`calculo_cubagem_lote.py`](calculo_cubagem_lote.py) | Verificado localmente | Lê um CSV de dimensões e calcula peso cubado, peso tarifado, excesso e classificação por linha; exporta CSV e, opcionalmente, JSON. | Python 3.9+ e biblioteca padrão. Não consulta transportadora, não calcula preço de frete e não substitui a conferência do contrato aplicável. |
| [`cubagem_lote_csv.py`](cubagem_lote_csv.py) | Verificado localmente | Auditoria CLI estruturada de cubagem em lote com modo `--demo` e exportação analítica. | Python 3.9+ e biblioteca padrão. Identifica divergências volumétricas e penalidades de frete. |
| [`auditoria_frete_demo.py`](auditoria_frete_demo.py) | Em revisão para publicação | Contém um modo demonstrativo e um caminho opcional de consulta externa. | O caminho de API exige credencial e contrato externo; não é tratado como integração validada nesta entrega. Nunca coloque token em CSV, README ou commit. |

## Início rápido

Requer Python 3.9 ou superior. O exemplo abaixo não faz chamadas de rede e utiliza apenas a biblioteca padrão do Python.

```powershell
python calculo_cubagem_lote.py `
  --input examples/pedidos_sinteticos.csv `
  --output examples/saida_cubagem.csv `
  --json examples/saida_cubagem.json
```

O fator padrão é `6000`. Ele pode ser alterado explicitamente com `--fator`, desde que o valor usado seja compatível com o contrato que está sendo auditado:

```powershell
python calculo_cubagem_lote.py --input examples/pedidos_sinteticos.csv --fator 5000
```

Para executar a demonstração da auditoria completa em lote:

```powershell
python cubagem_lote_csv.py --demo
```

Para descobrir todas as opções:

```powershell
python calculo_cubagem_lote.py --help
```

### Exemplo reproduzível

[`examples/pedidos_sinteticos.csv`](examples/pedidos_sinteticos.csv) contém três pedidos fictícios. Com o fator `6000`, a execução produz:

- 3 embalagens auditadas;
- 2 linhas com peso cubado acima do peso físico;
- 1 linha classificada como crítica pelo limiar implementado (`desperdicio_pct > 100`);
- 3,7 kg de excesso somado nas linhas penalizadas.

Esses números são derivados apenas das dimensões e dos pesos do CSV. Não são economia, cobrança ou benchmark de transportadora.

## Como a conta funciona

Para cada linha, o script calcula:

```text
peso_cubado_kg = comprimento_cm × largura_cm × altura_cm ÷ fator
peso_tarifado_kg = máximo(peso_físico_kg, peso_cubado_kg)
```

O código arredonda o peso cubado e o excesso para três casas. A classificação é uma heurística do exemplo: `OTIMIZADO` quando o físico é maior ou igual ao cubado, `ATENÇÃO` quando há cubagem acima do físico e `CRÍTICO` quando o percentual de excesso supera 100%.

## Limites importantes

- O fator de cubagem padrão é um parâmetro do exemplo, não uma regra universal.
- O script não valida se a transportadora aceita o fator informado.
- O script não consulta faturas, tabelas de preço, impostos, SLA ou eventos de rastreio.
- Linhas com número inválido são ignoradas com aviso; revise a saída antes de tomar decisão operacional.
- O script não foi desenhado para receber segredos. Integrações externas devem ser especificadas e testadas separadamente.

## Contribuição

Leia [`CONTRIBUTING.md`](CONTRIBUTING.md) antes de abrir uma alteração. Relatos com entrada sintética, comando executado e saída observada são especialmente úteis.

## Canais complementares

- Newsletter: [Beehiiv](https://backstagecommerce.beehiiv.com/)
- X: [@BackstageCmrc](https://x.com/BackstageCmrc)

Esses canais complementam o laboratório; a documentação pública continua sendo a fonte para reproduzir cada ferramenta.
