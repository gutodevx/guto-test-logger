# GUTO Test Logger

[![Testes Python](https://github.com/gutodevx/guto-test-logger/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/gutodevx/guto-test-logger/actions/workflows/tests.yml)

Ferramenta em Python que estou desenvolvendo para organizar os registros dos testes que faço com agentes de inteligência artificial.

O projeto faz parte do laboratório GUTO AI e está sendo desenvolvido por Augusto Sales, com apoio de IA na construção do código, nas revisões e no aprendizado.

## Por que criei

Durante os testes com agentes, precisei conferir mensagens, respostas e ferramentas utilizadas em uma conversa. Fazer essa revisão manualmente dificulta encontrar e organizar as informações de cada teste.

O GUTO Test Logger ajuda nesse processo: lê uma conversa exportada do Hermes, separa o trecho do teste e gera arquivos para facilitar a conferência.

## Como funciona

1. Recebe um arquivo de conversa exportado do Hermes.
2. Localiza a mensagem usada no teste e as respostas relacionadas.
3. Separa a resposta final e os registros das ferramentas utilizadas.
4. Guarda uma cópia completa da conversa exportada e calcula seu SHA256.
5. Cria um arquivo para a avaliação humana do teste.

O SHA256 funciona como uma identificação do conteúdo do arquivo e ajuda a conferir se ele foi alterado.

A ferramenta organiza registros existentes. Ela não executa o agente nem as ferramentas que aparecem na conversa.

## Componentes

- `guto_logger.py`: processa uma exportação existente, sem acessar o Hermes.
- `registrar_teste.py`: exporta uma sessão pela CLI do Hermes, executa o Logger e confere o registro.

## Estado do projeto

Protótipo experimental. Não apresentado como solução de produção.

O registro de uma execução não comprova a correção da resposta do agente. A avaliação humana permanece separada.

## Requisitos

- Python 3. Demonstração local verificada com Python 3.14.7 no Windows.
- Nenhuma dependência Python externa.
- Para o Registrador: CLI do Hermes instalada e comando `hermes` disponível no PATH.

A compatibilidade com outras versões do Python e do Hermes precisa ser verificada.

## Demonstração sem Hermes

Na pasta do projeto, execute no PowerShell:

```powershell
py -3 .\guto_logger.py --input .\examples\sessao-ficticia.jsonl --output .\outputs --test DEMO-T01 --session-id sessao-demo-001 --message-id 1
```

Em Linux, use `python3` e ajuste os caminhos.

O exemplo é inteiramente fictício. A chamada `read_file` está registrada na entrada: nenhuma ferramenta ou agente é executado nesta demonstração.

Resultado esperado:

- Uma chamada de ferramenta registrada.
- Sete arquivos em `outputs/DEMO-T01`.
- Avaliação humana pendente.
- SHA256 da origem registrado nos metadados.

Se a pasta do teste já existir, a execução é recusada. Use outro destino ou `--force` para criar uma nova versão sem substituir a anterior.

## Arquivos gerados

| Sufixo | Conteúdo |
| --- | --- |
| `PROMPT.md` | Prompt selecionado |
| `RESPOSTA.md` | Resposta final extraída |
| `FERRAMENTAS.json` | Chamadas e resultados de ferramentas |
| `METADADOS.json` | Identificadores, contagens e hash da origem |
| `AVALIACAO.md` | Modelo para revisão humana |
| `ORIGEM-SHA256.txt` | Hash da exportação |
| `ORIGEM.json` ou `ORIGEM.jsonl` | Cópia integral da entrada |

## Integração opcional com Hermes

Consulte as opções:

```powershell
py -3 .\registrar_teste.py --help
```

O Registrador exige perfil, ID completo da sessão, código do teste e destino. O ID da mensagem pode ser informado para selecionar explicitamente o prompt.

Ele cria uma pasta exclusiva por execução, exporta a sessão integralmente e gera um recibo `REGISTRO.json`.

A demonstração fictícia deste repositório não valida a integração com a CLI real do Hermes no ambiente de quem executar.

## Validações implementadas

- Seleção de sessão sem ambiguidade.
- Seleção de prompt por ID ou código de teste único.
- Exclusão de mensagens inativas.
- Rejeição de trechos selecionados com mensagens compactadas.
- Correspondência entre IDs de chamadas e resultados de ferramentas.
- Preservação da origem e cálculo de SHA256.
- Marcador de execução incompleta durante a gravação.

SHA256 permite conferir a igualdade dos arquivos; não comprova a autenticidade ou a veracidade da conversa.

## Privacidade

A cópia de origem contém a exportação integral, incluindo mensagens fora do teste selecionado.

O projeto não anonimiza dados automaticamente. Use somente entradas fictícias nas demonstrações públicas e revise todo conteúdo antes de compartilhar.

As pastas `outputs/`, `exports/` e `local-data/` estão no `.gitignore`. Isso não impede a inclusão de dados sensíveis em outros caminhos.

## Limitações

- Depende dos formatos de exportação reconhecidos pelo código.
- Não reúne sessões divididas por compressão.
- Não suporta conteúdo estruturado no trecho selecionado.
- Não avalia automaticamente a qualidade das respostas.
- Um teste de demonstração bem-sucedido não valida todos os cenários.

## Testes automatizados

O projeto tem sete testes automáticos para conferir a extração dos registros, a geração do recibo e algumas situações em que a execução deve ser recusada.

Na pasta do projeto, execute no Windows:

    py -3 -m unittest discover -s tests -v

No Linux:

    python3 -m unittest discover -s tests -v

Os testes verificam:

- Extração dos registros e conferência do SHA256.
- Recusa de sobrescrita de registros existentes.
- Rejeição de chamada de ferramenta sem resultado.
- Rejeição de trecho com mensagem compactada.
- Geração do recibo pelo Registrador.
- Rejeição de arquivo com nome incorreto.
- Rejeição de pasta no lugar de um arquivo esperado.

O GitHub Actions executa esses testes com Python 3.14 no Windows e no Linux a cada envio de alterações e nos pull requests para a main. Ele também verifica se os scripts têm erros de sintaxe.

O indicador no início deste README mostra o resultado da automação na main. Para consultar cada execução e seus detalhes, abra a aba Actions.

Nos testes do Registrador, a exportação do Hermes é simulada. Esses testes executam o Logger real, mas não executam o Hermes de verdade.

Os testes ajudam a identificar problemas nos cenários que foram programados. Eles não garantem que o projeto esteja livre de falhas nem avaliam se a resposta do agente está correta.

## Próximos passos

- Ampliar a cobertura para outros formatos e cenários de falha.
- Validar a integração com versões identificadas da CLI do Hermes.
- Melhorar mensagens de erro e documentação de compatibilidade.

## Licença

Licença de distribuição ainda não definida.
