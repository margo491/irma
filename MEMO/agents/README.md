# MEMO/agents — Агентная модель

## Текущий режим: single-agent

**Системный агент:** `system_agent_id = irma-bot-claude-v1`  
**Инструмент:** Claude Code  
**Статус:** активен

---

## Принципы

- Один активный агент на сессию.
- Логирование в `MEMO/sessions/` и `MEMO/events/`.
- Конфликты записи невозможны — только один агент.

---

## Расширение до multi-agent

Структура каталога совместима с multi-agent расширением.  
При добавлении новых агентов создать карточки по схеме из `docs/03 структуры JSON.md` и `docs/04 реестр активных агентов.md`.

Шаблон карточки агента (`agents/<agent-id>.json`):
```json
{
  "agent_id": "agent-<role>-<name>",
  "role": "<роль>",
  "status": "active | idle | closed",
  "skills": [],
  "session_log": "MEMO/sessions/<date>-<id>.md",
  "updated_at": "YYYY-MM-DDTHH:MM:SSZ"
}
```

Реестр активных агентов (`agents/index.md`) — создать по необходимости.
