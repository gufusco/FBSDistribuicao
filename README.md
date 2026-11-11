# Assistente via Telegram para Consultas Operacionais

Projeto acadêmico **IA 1** para a **FBS Distribuição**, com classificação supervisionada de intenções e consultas operacionais sintéticas.

Autores: Daniel Domiciano Spindola (RA 115562), Gustavo de Oliveira Fusco (RA 115220) e Joao Gabriel Coitinho Bonin (RA 115872) — Engenharia de Computação, FHO Araras.

## Instalação

Requer Python 3.13. No PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/seed_db.py
python scripts/generate_corpus.py
python scripts/train.py
python experiments/run_experiments.py
pytest
```

O `.env` deve conter `TELEGRAM_BOT_TOKEN` obtido conversando com **@BotFather** no Telegram (New Bot, escolha nome e username, copie o token para o `.env`). Nunca versionar esse arquivo.

## Execução

Demo local: `python -m fbs_bot.channels.cli --chat-id 1` (após `pip install -e .`, ou com `PYTHONPATH=src`).
Bot Telegram: `python -m fbs_bot.channels.telegram_bot`, usando polling e texto sem Markdown/HTML.

## Arquitetura

`engine.py` é a interface independente de canal. A precedência é: comandos, regras de saudação/ajuda, identificadores isolados, classificador calibrado e fallback quando P < 0,55. Entidades são extraídas por regex e o contexto de intenção expira em cinco minutos. A camada de consultas usa SQLite e pode ser trocada por SQL Server. Serviços separados calculam estadia, autorização e auditoria.

São gerados `tms.db`, `patio.db`, `ocorrencias.db` e `app.db`; os três primeiros representam sistemas operacionais distintos. O corpus de desenvolvimento possui 10 classes balanceadas; `corpus_ood.csv` é um conjunto ruidoso provisório e `corpus_ood_modelo.csv` é o modelo para os alunos ampliarem.

## Dados e conformidade

Todos os dados são fictícios/sintéticos. A tolerância de estadia é de cinco horas e o valor padrão é R$ 60,00/h, configurável por `VALOR_HORA_ESTADIA`. A auditoria mascara placas e NFs e possui retenção configurável.

## Licença

MIT. Veja `LICENSE`.
