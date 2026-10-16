# CEMAB — notificações de falta e painel administrativo

## O que mudou
- O endpoint existente `POST /presencas/eventos` continua recebendo o formato usado pelo script Control iD, mas agora apenas registra as passagens; não envia push de presença.
- O painel administrativo fica em `/admin` (por exemplo, `https://apisme.vercel.app/admin`).
- O painel permite calcular e enviar faltas por data, enviar aviso personalizado para todos os alunos ativos ou para um aluno específico e consultar o histórico dos envios.
- As notificações administrativas são incluídas no endpoint de histórico do aplicativo (`GET /presencas/historico`), para sincronização com o app existente.
- O script de controle de presença/planilha não faz parte desta alteração e deve permanecer como está.

## Configuração obrigatória
Configure no ambiente da API:

- `ALUNOS_ADMIN_TOKEN`: token forte e secreto usado para entrar no painel e autenticar as rotas administrativas. Pode ser o mesmo já usado para cadastro/importação de alunos.
- As variáveis de credenciais `FIREBASE_*` que a API já utiliza para o Firebase Admin.
- `DATABASE_URL` apontando para um banco persistente em produção. Não use SQLite efêmero de função serverless para dados que precisam sobreviver a reinicializações.

O painel não grava o token no armazenamento persistente do navegador; ele fica apenas em memória durante a sessão da página. Use HTTPS.

## Uso seguro para enviar faltas
1. Confira se o cadastro de alunos ativos está completo/importado na API.
2. Execute o script Control iD normalmente e confirme que o envio de eventos para `/presencas/eventos` terminou com sucesso.
3. Abra `/admin`, entre com `ALUNOS_ADMIN_TOKEN` e escolha a data correta.
4. Confira o resumo de presentes/faltas antes de clicar em **Calcular e enviar faltas**.
5. A API evita reenviar a falta para um aluno que já teve notificação de falta registrada para aquela data.

**Atenção:** não envie faltas antes de importar os registros de presença daquele dia. Se os eventos ainda não chegaram à API, os alunos poderão aparecer incorretamente como ausentes. A API não tem como inferir a presença de alunos cujo registro não foi recebido.

## Rotas administrativas
- `GET /admin`: painel web.
- `GET /admin/api/alunos`: lista de alunos ativos.
- `GET /admin/api/resumo?data=AAAA-MM-DD`: resumo de presença/falta para a data.
- `POST /admin/api/faltas/enviar`: calcula e envia notificações de falta.
- `POST /admin/api/personalizada/enviar`: aviso personalizado para todos ou um aluno.
- `GET /admin/api/historico`: histórico administrativo.

As rotas `/admin/api/*` exigem o cabeçalho `X-Admin-Token`.
