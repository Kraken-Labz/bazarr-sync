# AGENTS.md — Bazarr Bridge (HA)

## Regra Obrigatória

**Antes de iniciar qualquer trabalho:**
1. Ler `docs/COMPASS.md` — plano executivo canônico
2. Ler `docs/STATE.md` — descobrir ponto atual (CURRENT_PHASE, CURRENT_TASK)
3. Executar a próxima etapa elegível conforme COMPASS
4. Validar critérios de conclusão (gates da fase)
5. Atualizar `docs/STATE.md` com novo estado
6. Avançar automaticamente para a etapa seguinte quando não houver bloqueio que exija decisão humana

---

## Regras do Projeto

### Ambiente
- Usar exclusivamente **HA-LAB** para desenvolvimento e testes
- **NUNCA** tocar HA-PROD
- Usar Bazarr de laboratório/container para testes funcionais

### Segurança
- **NUNCA** armazenar, logar ou versionar API keys, tokens ou senhas
- A API key do Bazarr **nunca** pode chegar ao navegador (frontend)
- Paths do filesystem **nunca** vêm do frontend — o backend resolve e valida

### Arquitetura
- **TODA** comunicação HTTP com Bazarr passa por `BazarrClient` em `client.py`
- **NUNCA** fazer chamadas HTTP diretas em `services.py`, `websocket.py`, etc.
- O coordinator delega ao `BazarrClient`
- Models em `models.py` usam dataclasses simples — não criar framework

### Código
- **NÃO** adicionar comentários a menos que pedido
- Seguir o estilo do upstream (black, target py39+)
- Usar `from __future__ import annotations` em todos os módulos
- Type hints obrigatórios

### Upstream
- Preservar: config flow, coordinator (polling), sensores existentes, HACS
- Domain permanece `bazarr`
- Licença MIT do upstream mantida

### Validação
- Rodar `black --check .` antes de commit
- Rodar testes unitários: `pytest tests/`
- Testes funcionais contra Bazarr lab antes de declarar MVP concluído