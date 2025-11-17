# apisme

## Api para meus projetos pessoais

### Sumario
- [apisme](#apisme)
  - [Api para meus projetos pessoais](#api-para-meus-projetos-pessoais)
    - [Sumario](#sumario)
    - [Git Push](#git-push)
    - [Criar Venv](#criar-venv)
    - [Ativar o Venv](#ativar-o-venv)
    - [Atualiza o pip](#atualiza-o-pip)
    - [Desativar o Venv](#desativar-o-venv)
    - [Instalar dependências](#instalar-dependências)
    - [Atualiza dependências](#atualiza-dependências)
    - [Gerar requirements.txt](#gerar-requirementstxt)
    - [Rodar o projeto](#rodar-o-projeto)
    - [Projetos](#projetos)

### Git Push
```sh
  git add . && git commit -m "add " && git push
```

### Criar Venv
```sh
  python3 -m venv venv
```

### Ativar o Venv
```sh
  source venv/bin/activate
```

### Atualiza o pip
```sh
  pip install --upgrade pip

```

### Desativar o Venv
```sh
  deactivate
```

### Instalar dependências
```sh
  pip install -r requirements.txt
```

### Atualiza dependências
```sh
pip-review --auto

```

### Gerar requirements.txt
```sh
  pip freeze >> requirements.txt
```

### Rodar o projeto
```sh
  uvicorn src.main:app --reload
```
 - Obs: No ambiente DEV modificar [database.py](/src/database.py)
  
### Projetos

- [Testeme](https://github.com/davidsousadev/testeme)