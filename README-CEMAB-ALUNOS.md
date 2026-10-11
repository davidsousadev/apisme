# CEMAB App — alunos, vínculos, presenças e notificações

Esta versão integra os dispositivos FCM aos alunos e cria a entrada para a automação externa de presença. A automação que lê o arquivo/relatório Control iD **não faz parte deste projeto**: ela será desenvolvida em outro computador e deverá chamar os endpoints descritos aqui.

## 1. Variáveis de ambiente

Configure na hospedagem da API (por exemplo, Vercel):

- `DATABASE_URL`: banco de dados persistente de produção (PostgreSQL recomendado).
- `ALUNOS_ADMIN_TOKEN`: segredo para cadastrar/importar o cadastro oficial de alunos.
- `CEMAB_EVENT_TOKEN`: segredo diferente, usado somente pela automação que envia eventos de presença.
- Todas as variáveis de credencial do Firebase Admin SDK listadas em `.env.example`.

Nunca envie `ALUNOS_ADMIN_TOKEN`, `CEMAB_EVENT_TOKEN` ou credenciais Firebase no aplicativo Cordova ou em repositório público. O `CEMAB_EVENT_TOKEN` deve ficar somente no computador da automação e no ambiente da API.

As novas tabelas são criadas pelo `SQLModel.metadata.create_all`: `aluno_dispositivo` (relaciona aluno a dispositivo FCM) e `cemab_evento_presenca` (idempotência e histórico de eventos enviados). `create_all` não migra colunas de tabelas antigas, mas essas duas tabelas são novas nesta implementação.

## 2. Cadastro oficial dos alunos

A tabela de alunos começa vazia. Antes de os responsáveis poderem vincular aluno, importe o cadastro oficial.

### `POST /alunos/importar` — administrativo

Cabeçalho `X-Admin-Token: <ALUNOS_ADMIN_TOKEN>`.

```json
{
  "alunos": [
    {"matricula": "12.345.678", "nome_completo": "NOME COMPLETO DO ALUNO", "ativo": true},
    {"matricula": "23.456.789", "nome_completo": "OUTRO ALUNO DE EXEMPLO", "ativo": true}
  ]
}
```

Aceita até 5.000 alunos por chamada. A matrícula é normalizada sem pontos, hífens ou espaços; na consulta, o nome ignora diferenças de caixa, acentos e espaços repetidos. Se a matrícula já existir, o nome e o estado ativo são atualizados. Duplicados dentro do mesmo lote são ignorados depois da primeira ocorrência.

### `POST /alunos/cadastrar` — administrativo

Cadastra um único aluno, também protegido por `X-Admin-Token`.

## 3. Vínculo no aplicativo

### `POST /users/cadastrar`

Continua registrando o token FCM. O corpo original `{ "token": "..." }` continua compatível. Opcionalmente, o app envia `{ "token": "NOVO", "token_anterior": "ANTIGO" }` quando o FCM renova o token; a API atualiza o registro ou migra os vínculos existentes para não perder a associação ao aluno.

### `POST /alunos/vincular`

Valida matrícula e nome contra o cadastro oficial e cria a associação dispositivo-aluno no servidor. O token precisa ter sido cadastrado previamente em `/users/cadastrar`.

```json
{
  "matricula": "12.345.678",
  "nome_completo": "NOME COMPLETO DO ALUNO",
  "token": "TOKEN_FCM_DO_DISPOSITIVO"
}
```

Retorno de sucesso inclui `success: true`, `vinculo_ativo: true` e os dados oficiais do aluno. Dados não confirmados retornam `404`; token que ainda não foi registrado retorna `409`.

### `POST /alunos/desvincular`

Remove somente a relação entre o aluno e aquele token FCM:

```json
{"matricula": "12.345.678", "token": "TOKEN_FCM_DO_DISPOSITIVO"}
```

### `GET /alunos/vinculo`

Retorna a lista de alunos associados a um dispositivo. Envie o token no cabeçalho `X-FCM-Token` (não na URL), para evitar que ele seja gravado nos logs de requisição.

## 4. Receber eventos de presença e enviar FCM

A automação externa deve enviar eventos já processados, ou seja, não deve depender de a API interpretar um arquivo CSV/Excel. O endpoint aceita nomes de campos normalizados e também alguns rótulos do relatório, como `Matrícula (Usuário)`, `Nome (Usuário)`, `Data e Hora (Logs de Acesso)`, `Identificação`, `Código (Usuário)` e `Autorização (Logs de Acesso)`.

Nas amostras fornecidas, cada linha parece conter um valor inicial de ID do log além das oito colunas descritas; confirme o cabeçalho real no computador da automação antes de mapear os campos. Algumas linhas não trazem matrícula. Nesses casos, a automação deve resolver a matrícula por uma fonte oficial autorizada ou adiar/descartar o evento; a API não adivinha a matrícula pelo nome.

### `POST /presencas/evento` — um evento

Cabeçalho obrigatório `X-CEMAB-Event-Token: <CEMAB_EVENT_TOKEN>`.

```json
{
  "id_evento": "evento-exemplo-0001",
  "matricula": "12.345.678",
  "nome_completo": "NOME COMPLETO DO ALUNO",
  "data_hora": "2026-10-11T07:35:00-03:00",
  "identificacao": "1717658368",
  "codigo_usuario": "156",
  "autorizacao": "7"
}
```

`data_hora` aceita ISO 8601 (recomendado, com fuso horário) ou timestamp Unix em segundos/milissegundos. O horário no exemplo é apenas ilustrativo: a automação deve enviar o horário já corrigido, conforme combinado. A API não lê nem conserta o arquivo de relatório original.

A API localiza o aluno pela matrícula cadastrada. Se o aluno estiver ativo e houver dispositivos vinculados, envia a notificação FCM a cada dispositivo associado. Se o aluno não estiver cadastrado ou não tiver dispositivo vinculado, a resposta informa o motivo e não envia push. Eventos sem matrícula devem ser enriquecidos/resolvidos pela automação antes do envio; a API não tenta adivinhar o aluno só pelo nome, para evitar correspondências ambíguas.

A notificação enviada contém dados FCM do tipo `presenca`: `evento_id`, `matricula`, `nome_completo`, `data_hora`, `hora_aproximada`, `titulo` e `mensagem`. Todos os campos de `data` são strings, como exige o FCM. A notificação visível informa que o aluno passou pelo reconhecimento facial e inclui o horário aproximado. Quando o Firebase retorna explicitamente que um token não está mais registrado, a API remove a associação antiga desse dispositivo para reduzir vínculos deixados por instalações desinstaladas.

### `POST /presencas/eventos` — lote de eventos

Cabeçalho `X-CEMAB-Event-Token`; corpo:

```json
{
  "eventos": [
    {
      "id_log": "log-exemplo-0001",
      "matricula": "12.345.678",
      "nome_completo": "NOME COMPLETO DO ALUNO",
      "data_hora": "2026-10-11T07:35:00-03:00",
      "identificacao": "1717658368",
      "codigo_usuario": "156",
      "autorizacao": "7"
    }
  ]
}
```

Recomenda-se fornecer `id_evento` (ou `id_log`) único vindo da fonte. A API registra a chave para evitar envio duplicado quando a automação tentar novamente o mesmo evento. O lote permite até 500 eventos por requisição e devolve o resultado individual de cada um.

### `GET /presencas/historico`

O app usa este endpoint para recuperar notificações quando volta a abrir. Envie o token FCM no cabeçalho `X-FCM-Token` (não na URL) e, opcionalmente, `?limite=100`. O histórico retorna somente eventos de alunos ligados ao token e que tiveram envio para pelo menos um dispositivo. A leitura/não leitura é estado local do app.

## 5. Fluxo final

1. App solicita permissão de notificação, obtém token FCM e chama `/users/cadastrar`.
2. Responsável informa matrícula e nome completo.
3. `/alunos/vincular` valida o aluno e grava `aluno_dispositivo` com o `user_id` do token.
4. A automação do outro computador envia `POST /presencas/evento` ou `/presencas/eventos` com `X-CEMAB-Event-Token`.
5. A API consulta os vínculos e envia o FCM somente aos dispositivos associados ao aluno presente.
6. O app salva as notificações recebidas localmente, exibe o aviso em primeiro plano e sincroniza o histórico ao abrir/retomar.

## 6. Testes e implantação

1. Faça backup do código e do banco em uso.
2. Configure `DATABASE_URL`, variáveis Firebase, `ALUNOS_ADMIN_TOKEN` e `CEMAB_EVENT_TOKEN` no provedor.
3. Publique a API.
4. Importe o cadastro oficial via `/alunos/importar`.
5. Instale o APK atualizado e faça o vínculo no celular real.
6. Envie um evento de teste para `/presencas/evento` com credencial de webhook e confirme a resposta FCM.
7. Teste app aberto, em segundo plano, fechado, toque na notificação e histórico ao reabrir.

O endpoint de webhook não deve ficar sem `CEMAB_EVENT_TOKEN`. Se não houver o segredo configurado, a API retorna `503` em vez de aceitar eventos publicamente. Matrícula e nome completo não provam, isoladamente, que a pessoa que está usando o aplicativo é responsável legal; a escola deve avaliar uma etapa de confirmação adicional antes de ampliar o acesso a dados sensíveis.
