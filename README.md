# apisme

## Api para meus projetos pessoais

### Sumario
- [apisme](#apisme)
  - [Api para meus projetos pessoais](#api-para-meus-projetos-pessoais)
    - [Sumario](#sumario)
    - [Git Push](#git-push)
    - [Criar Venv](#criar-venv)
    - [Ativar o Venv](#ativar-o-venv)
    - [Desativar o Venv](#desativar-o-venv)
    - [Gerar requirements.txt](#gerar-requirementstxt)
    - [Instalar dependências](#instalar-dependências)
    - [Rodar o projeto](#rodar-o-projeto)

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

### Desativar o Venv
```sh
  deactivate
```

### Gerar requirements.txt
```sh
  pip freeze >> requirements.txt
```

### Instalar dependências
```sh
  pip install -r requirements.txt
```

### Rodar o projeto
```sh
  uvicorn src.main:app --reload
```