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
| [`calculadora_faixa_venenosa.py`](calculadora_faixa_venenosa.py) | Simulação local reproduzível | Compara a margem de contribuição de um SKU com uma referência de preço em um cenário sintético de degrau. | Python 3.9+ e biblioteca padrão. Comissão e copay podem vir do CSV; degrau, preço de referência e taxa fixa estão fixos no código. Não consulta tarifas vigentes. |
| [`calculo_cubagem_lote.py`](calculo_cubagem_lote.py) | Verificado localmente | Lê um CSV de dimensões e calcula peso cubado, peso tarifado, excesso e classificação por linha; exporta CSV e, opcionalmente, JSON. | Python 3.9+ e biblioteca padrão. Não consulta transportadora, não calcula preço de frete e não substitui a conferência do contrato aplicável. |
| [`cubagem_lote_csv.py`](cubagem_lote_csv.py) | Verificado localmente | Simulação CLI de cubagem em lote com modo `--demo` e exportação analítica. | Python 3.9+ e biblioteca padrão. Identifica excesso teórico de cubagem; não comprova penalidade ou cobrança. |
| [`auditoria_frete_demo.py`](auditoria_frete_demo.py) | Em revisão para publicação | Contém um modo demonstrativo e um caminho opcional de consulta externa. | O caminho de API exige credencial e contrato externo; não é tratado como integração validada nesta entrega. Nunca coloque token em CSV, README ou commit. |

## Auditor de Faixa Venenosa de Preços — simulação de degrau

O script [`calculadora_faixa_venenosa.py`](calculadora_faixa_venenosa.py) demonstra como um salto de custo pode reduzir a margem de contribuição mesmo quando o preço aumenta. O cenário usa estas premissas sintéticas, sem representar regras vigentes do Mercado Livre ou de outro canal:

- **Abaixo de R$ 79,00:** O modelo aplica taxa fixa de R$ 6,00 e frete do vendedor igual a zero.
- **A partir de R$ 79,00:** O modelo aplica taxa fixa zero e usa `copay_frete` do CSV (R$ 19,50 quando a coluna está ausente).
- **Referência de comparação:** R$ 78,90, com taxa fixa de R$ 6,00 e frete zero. Esses três valores e o degrau de R$ 79,00 são fixos no código; não podem ser alterados pelo CSV ou por opção de canal.
- **Comissão:** `comissao_pct` do CSV, em porcentagem; padrão sintético de 16 quando a coluna está ausente. Não existe consulta automática de comissão ou frete.

Esses valores não têm fonte tarifária validada nesta entrega. Confira as regras do seu contrato antes de modelar uma operação real. A conta subtrai custo do produto, comissão, taxa fixa e frete do vendedor; não inclui impostos, devoluções, publicidade ou outros custos e não representa lucro líquido.

### Como executar:

```powershell
python calculadora_faixa_venenosa.py `
  --input exemplos_catalogo_degrau.csv `
  --output auditoria_faixa_venenosa_resultado.csv
```

O catálogo demonstrativo [`exemplos_catalogo_degrau.csv`](exemplos_catalogo_degrau.csv) contém 6 SKUs fictícios. Com essas entradas, 2 recebem `FAIXA_VENENOSA_PREJUIZO`: SKU-003 e SKU-004. Suas margens simuladas são R$ 16,54 e R$ 16,82, com diferenças de -R$ 11,74 e -R$ 8,46 em relação à referência. O campo `Preco_Sugerido_Equilibrio` mostra R$ 94,97 para ambos, arredondado para duas casas; esse arredondamento pode deixar a margem ligeiramente abaixo da referência.

Os rótulos `PREJUIZO` e `SAUDAVEL` são nomes do CSV: indicam comparação com a referência e não comprovam prejuízo absoluto ou rentabilidade. Abaixo do degrau, o script mantém o preço e informa diferença zero; não otimiza o catálogo nem recomenda automaticamente reduzir preços.

### Contrato e limites da calculadora

O CSV usa UTF-8 (BOM opcional), vírgula como separador e ponto decimal. O cabeçalho exige `sku,titulo,custo_produto,preco_venda`, sem distinção de maiúsculas/minúsculas; `comissao_pct` e `copay_frete` são opcionais. Colunas adicionais nomeadas são aceitas. Cabeçalhos vazios/duplicados, campos obrigatórios vazios, registros com células faltantes/excedentes, CSV malformado e ausência de registros são recusados. Linhas físicas vazias são ignoradas.

Os números devem ser finitos: custo e copay não negativos, preço positivo e comissão entre 0 (inclusive) e 100 (exclusive). `NaN`, infinitos e resultados intermediários não finitos são recusados. O copay é validado mesmo abaixo do degrau. Defaults aplicam-se somente à coluna ausente; célula opcional vazia é erro.

Entrada inválida retorna código de saída `2` e diagnóstico em stderr com linha física/campo; em registros multilinha, a linha pode indicar o fim do registro. Falha de arquivo/codificação retorna `1`. Nos casos testados, ambos são erros controlados, sem traceback ou mensagem de sucesso. O lote é validado antes da exportação e gravado em temporário na pasta de destino, substituindo a saída somente após a gravação completa. Em erro tratado, nenhuma saída final parcial é criada e uma saída antiga fica intacta, com aviso de que não foi atualizada. Confira o código de saída; a presença de um arquivo antigo não indica sucesso. Entrada e saída apontando para o mesmo arquivo são recusadas.

Os cenários de CLI, compatibilidade de CSV e falhas de gravação/substituição foram testados em Windows com Python 3.12.10. Não foram testados outros runtimes, concorrência entre escritores, queda de energia, disco cheio real ou falha do próprio mecanismo de limpeza de temporários. A verificação cobre os casos executados e não garante robustez integral. Premissas e dados continuam sintéticos; não automatize decisões comerciais com essa saída.

## Início rápido — Cubagem e Peso Tarifado

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

### Exemplo reproduzível de cubagem

[`examples/pedidos_sinteticos.csv`](examples/pedidos_sinteticos.csv) contém três pedidos fictícios. Com o fator `6000`, a execução produz:

- 3 embalagens auditadas;
- 2 linhas com peso cubado acima do peso físico;
- 1 linha classificada como crítica pelo limiar implementado (`desperdicio_pct > 100`);
- 3,7 kg de excesso somado nas linhas penalizadas.

Esses números são derivados apenas das dimensões e dos pesos do CSV. Não são economia, cobrança ou benchmark de transportadora.

## Como a conta de cubagem funciona

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
- Em `calculo_cubagem_lote.py`, campos de dimensão/peso ausentes ou vazios recebem valores padrão; números negativos e não finitos não são rejeitados integralmente. Confira entradas completas, finitas e positivas e use fator positivo. A classificação descreve o modelo, não uma cobrança confirmada.
- Em `cubagem_lote_csv.py`, `--demo` usa o fator interno `6000`; `--fator` é aplicado ao caminho `--input`, com prioridade para a coluna opcional `fator_cubagem` por linha. Para testar outro contrato, use um CSV explícito.
- O script não foi desenhado para receber segredos. Integrações externas devem ser especificadas e testadas separadamente.

## Contribuição

Leia [`CONTRIBUTING.md`](CONTRIBUTING.md) antes de abrir uma alteração. Relatos com entrada sintética, comando executado e saída observada são especialmente úteis.

## Canais complementares

- Newsletter: [Beehiiv](https://backstagecommerce.beehiiv.com/)
- X: [@BackstageCmrc](https://x.com/BackstageCmrc)

Esses canais complementam o laboratório; a documentação pública continua sendo a fonte para reproduzir cada ferramenta.
