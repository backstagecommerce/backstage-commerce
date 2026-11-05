# Contribuindo com o Backstage Commerce

O Backstage Commerce é um laboratório de engenharia aplicada a custos, dados e automações de e-commerce. Contribuições devem tornar uma conta, uma entrada ou uma decisão mais verificável.

## Antes de propor uma mudança

1. Reproduza o comportamento atual com dados sintéticos ou anonimizados.
2. Registre o comando, a versão do Python e a saída observada.
3. Confirme se a mudança é compatível com a documentação e atualize os limites quando necessário.
4. Não inclua tokens, credenciais, dados de clientes, faturas reais ou identificadores pessoais.

## Relatando um problema

Inclua, quando possível:

- sistema operacional e versão do Python;
- arquivo de entrada mínimo e sintético;
- comando completo executado;
- resultado esperado e resultado observado;
- traceback completo, se houver;
- indicação de que o problema é reproduzível.

Não publique segredos para demonstrar uma falha de integração. Redija o valor e descreva apenas o tipo de credencial necessário.

## Enviando uma alteração

- Mantenha a biblioteca padrão quando ela for suficiente.
- Preserve a compatibilidade do formato de entrada ou documente a quebra.
- Prefira funções determinísticas e exemplos pequenos.
- Atualize o README ou a documentação de limites junto com o código.
- Acrescente uma verificação executável para cada comportamento novo.
- Identifique claramente dados sintéticos e resultados derivados.

Antes de enviar, execute pelo menos:

```powershell
python -m py_compile calculo_cubagem_lote.py
python calculo_cubagem_lote.py --help
python calculo_cubagem_lote.py `
  --input examples/pedidos_sinteticos.csv `
  --output examples/saida_cubagem.csv `
  --json examples/saida_cubagem.json
```

Confira os arquivos gerados e remova saídas temporárias antes de propor a alteração. O repositório não aceita commits, releases ou issues artificiais para preencher calendário.

## Escopo editorial

O código público deve explicar o problema e seus limites sem prometer economia, compatibilidade ou resultado que não tenha sido medido. Newsletter e produtos Pro podem complementar o laboratório, mas não substituem a documentação nem justificam esconder o funcionamento do exemplo público.
