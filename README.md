# Assistente via Telegram para Consultas Operacionais

Projeto acadêmico **IA 1** para a **FBS Distribuição**, com classificação supervisionada de intenções e consultas operacionais sintéticas.

Autores: Daniel Domiciano Spindola (RA 115562), Gustavo de Oliveira Fusco (RA 115220) e João Gabriel Coitinho Bonin (RA 115872) — Engenharia de Computação, FHO Araras.

## Instalação

Requer Python 3.13. No PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
python scripts/seed_db.py
python scripts/generate_corpus.py
python experiments/run_experiments.py
pytest
ruff check src scripts experiments tests
```

`run_experiments.py` compara os três modelos, seleciona um por validação cruzada, treina o artefato usado pelo bot e grava os resultados em `experiments/`. `python scripts/train.py` executa a mesma seleção e salva o mesmo tipo de modelo sem gerar o relatório experimental.

> **Atenção:** `scripts/seed_db.py` recria os quatro bancos SQLite, apagando os arquivos `.db` existentes, inclusive usuários cadastrados e auditoria. Faça backup de `data/app.db` antes de rodar novamente se quiser preservar esses dados. `--data-dir` gera os arquivos em outra pasta, mas o bot continua lendo `data/` por padrão.

O arquivo `.env` deve conter `TELEGRAM_BOT_TOKEN` obtido com o **@BotFather**. Nunca publique esse arquivo nem o token.

## Execução

Depois de gerar os bancos e o modelo:

```powershell
python -m fbs_bot.channels.cli --chat-id 1
python -m fbs_bot.channels.telegram_bot
```

O bot Telegram usa polling e responde com texto simples. Ele só funciona enquanto o processo estiver aberto.

## Arquitetura

`src/fbs_bot/engine.py` contém o fluxo independente do canal: valida usuário, prioriza regras operacionais e identificadores, usa o classificador quando necessário, extrai entidades, aplica autorização por perfil, consulta as bases e registra auditoria. Mensagens com baixa confiança (`P < 0,55`) vão para fallback.

As fontes sintéticas são quatro arquivos SQLite:

- `tms.db`: transportadoras, embarques, notas fiscais e agendamentos;
- `patio.db`: movimentações de veículos;
- `ocorrencias.db`: ocorrências operacionais;
- `app.db`: usuários autorizados e auditoria.

O embarque conecta as três fontes operacionais. A camada de serviços aplica acesso por perfil (`interno`, `transportadora`, `motorista`), normalização de placas, mascaramento e retenção de auditoria. As datas sintéticas são criadas relativas ao horário em que os bancos são gerados, e a estadia usa a saída registrada ou o relógio injetável do motor.

## NLP e experimentos

O corpus possui dez intenções. O pré-processamento normaliza caixa e acentos; TF-IDF usa unigramas e bigramas. O experimento compara Multinomial Naive Bayes, LinearSVC calibrado e Random Forest com `GridSearchCV`, F1-macro e validação cruzada estratificada por grupos de templates. O limiar 0,55 é fixado antes do teste final.

`data/corpus_ood.csv` é um conjunto sintético provisório com exemplos de texto e casos explícitos para regras. Ele não representa coleta de conversas reais; complemente-o com frases inéditas rotuladas independentemente antes de tirar conclusões acadêmicas fortes. A comparação HYBRID é executada pelo próprio `Engine`, e não por uma cópia simplificada da lógica.

## Dados, privacidade e arquivos versionados

Todos os registros operacionais de demonstração são sintéticos. Arquivos `.db`, `.env`, o ambiente virtual e o modelo binário são ignorados pelo Git. Os scripts versionados recriam os bancos e o modelo; os CSVs e os relatórios experimentais são versionados.

A retenção de auditoria padrão é de 90 dias (`AUDIT_RETENTION_DAYS`), e a taxa de estadia padrão é R$ 60,00/h excedente (`VALOR_HORA_ESTADIA`), ambas configuráveis no `.env`. O protótipo acadêmico não é uma avaliação legal ou uma implementação pronta de conformidade LGPD.

## Licença

MIT. Veja `LICENSE`.
