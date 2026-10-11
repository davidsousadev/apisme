# Atualização da API para vínculo de alunos — CEMAB App

Esta atualização adiciona a rota `POST /alunos/vincular` para validar matrícula e nome completo com o cadastro oficial de alunos. As rotas existentes (`/users/cadastrar`, `/fire` e `/testeme`) foram preservadas.

## Importante antes de publicar

A API agora possui uma tabela `aluno` (SQLModel), mas ela começa vazia. **É necessário importar os alunos reais fornecidos pela escola** antes de o vínculo no aplicativo funcionar. Não existe integração com sistema escolar externo nesta versão porque nenhum endpoint/base de dados oficial de alunos foi fornecido.

## Endpoints

### `POST /alunos/vincular` — público para o aplicativo

Corpo JSON:

```json
{
  "matricula": "202600123",
  "nome_completo": "Nome Completo do Aluno"
}
```

Resposta de sucesso (`200`):

```json
{
  "success": true,
  "message": "Aluno validado com sucesso.",
  "aluno": {
    "id": 1,
    "matricula": "202600123",
    "nome_completo": "Nome Completo do Aluno"
  }
}
```

Matrícula e nome são comparados com o cadastro oficial. A comparação do nome ignora maiúsculas/minúsculas, acentos e espaços repetidos. Dados incorretos ou aluno inativo retornam `404` com mensagem genérica.

### `POST /alunos/cadastrar` — administrativo

Adiciona um aluno individual. Requer o cabeçalho `X-Admin-Token`.

```json
{
  "matricula": "202600123",
  "nome_completo": "Nome Completo do Aluno",
  "ativo": true
}
```

### `POST /alunos/importar` — administrativo

Importa até 5.000 registros por requisição. Se a matrícula já existir, atualiza nome e estado ativo.

```json
{
  "alunos": [
    {"matricula": "202600123", "nome_completo": "Nome Completo do Aluno", "ativo": true},
    {"matricula": "202600124", "nome_completo": "Outra Pessoa", "ativo": true}
  ]
}
```

Ambas as rotas administrativas exigem a variável de ambiente `ALUNOS_ADMIN_TOKEN`. Configure um segredo forte nas variáveis de ambiente do ambiente de hospedagem. Nunca coloque esse segredo no aplicativo Cordova nem no repositório.

### `GET /alunos/health`

Verifica se o módulo de alunos está disponível.

## Configuração e implantação

1. Faça backup da versão atualmente publicada e do banco de dados.
2. Copie os arquivos atualizados para o repositório `apisme`.
3. Configure `ALUNOS_ADMIN_TOKEN` nas variáveis de ambiente da hospedagem (por exemplo, Vercel).
4. Confirme que a URL de banco de dados aponta para o banco persistente correto. A tabela será criada pelo `SQLModel.metadata.create_all` existente, desde que o modelo esteja importado.
5. Publique a API.
6. Importe a lista oficial de alunos pela rota `/alunos/importar`, usando uma ferramenta administrativa segura e o cabeçalho `X-Admin-Token`.
7. Teste `/alunos/health` e, depois, `POST /alunos/vincular` com um registro de teste autorizado pela escola.

## Observações de segurança e escopo

- Matrícula + nome é uma verificação básica de correspondência, não prova por si só que a pessoa que usa o celular é responsável legal pelo aluno. Para dados escolares sensíveis, a escola deve considerar uma etapa adicional de confirmação do responsável.
- Esta rota valida o aluno, mas ainda **não associa o token FCM ao aluno ou ao responsável**. O app atual envia apenas matrícula e nome para o vínculo. A associação dispositivo-aluno e o envio de notificações de presença são a próxima etapa, que exigirá adaptar o app para enviar o token registrado e definir a política para vários responsáveis/dispositivos.
- O banco SQLite local pode não ser persistente em ambientes serverless. Em produção, use o banco persistente já adotado pelo projeto (por exemplo, PostgreSQL) e verifique suas variáveis de conexão.
