# GUTO Test Logger

Ferramenta experimental em Python para organizar evidências de testes de agentes a partir de exportações de sessões do Hermes.

Parte do laboratório GUTO AI, desenvolvido por Augusto Sales.

## Problema

Revisar conversas de agentes manualmente dificulta localizar o prompt de um teste, sua resposta e as ferramentas utilizadas.

O Logger extrai esse trecho e organiza arquivos para apoiar a revisão humana, preservando uma cópia integral da exportação com SHA256.

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

## Próximos passos

- Adicionar testes automatizados de sucesso e rejeição.
- Conferir os nomes esperados dos arquivos no Registrador.
- Melhorar mensagens de erro e documentação de compatibilidade.

## Licença

Licença de distribuição ainda não definida.
