# vpn-list

Соответствует стандарту: 4.15.1

## Назначение

Приватный репозиторий - единое место хранения и формирования каталога списков сайтов, которые ходят через VPN. Каталог - единственный источник истины: на роутере и машинах через VPN идут только записи каталога, остальной трафик - напрямую. Потребители (навыки других репозиториев) забирают `data/lists/catalog.json` сами и преобразуют в свои форматы; экспорт и доставка в репозитории нет.

Правила ведения каталога:

- наполняется с нуля, без затравки из старых списков
- внешние источники - только дообогащение: добавляют записи; источник с `refresh: true` обновляется (его записи, пропавшие в источнике, удаляются), остальные только добавляют
- ручные дописывания разрешены в любой момент и скриптами не удаляются
- строгой синхронизации с внешними каталогами нет
- переопределений «всегда-в» и «всегда-напрямую» нет: каталог - список того, что идет через VPN
- ресурсы РФ не берутся: домены с TLD `.ru`, `.su`, `.рф` отбрасываются источниками и проверкой

## Контракт формата catalog.json

Корневые поля:

| Поле | Тип | Смысл |
|------|-----|-------|
| `schema` | число | Версия схемы контракта; допустимое значение - `1` |
| `version` | строка | Версия каталога, формат `yymmdd`; поднимается при любом изменении содержимого |
| `groups` | объект | Группы записей; ключи - фиксированный набор групп |

Группы: `youtube`, `telegram`, `meta`, `twitter`, `discord`, `payments`, `ai`, `google`, `microsoft`, `dev`, `software`, `distros`, `torrents`, `geoblock`, `blocked-subnets`. Новая группа - изменение контракта: сначала правка README, потом каталога.

Запись группы - объект:

| Поле | Тип | Смысл |
|------|-----|-------|
| `value` | строка | Домен (`example.com`, нижний регистр, без схемы и пути) или подсеть в канонической записи CIDR (`203.0.113.0/24`) |
| `kind` | строка | `domain`, `cidr_v4` или `cidr_v6`; соответствует формату `value` |
| `source` | строка | `manual` для ручных записей или идентификатор внешнего источника |
| `added` | строка | Дата добавления записи, `yymmdd` |
| `comment` | строка | Опциональный комментарий |

Ограничения содержимого: значения уникальны по всему каталогу; подсети без битов хоста, не шире IPv4 `/16` и IPv6 `/32`; записей в группе не больше 5000; записи внутри группы сортированы по `kind`, затем `value`; версия каталога не старше максимальной даты `added`; домены ресурсов РФ (TLD `.ru`, `.su`, `.рф`) не допускаются.

## Использование потребителями

Потребитель (навык другого репозитория):

1. Забирает `data/lists/catalog.json` из этого репозитория (git или копирование)
2. Проверяет `schema` - при несовпадении останавливается
3. Преобразует в свой формат сам; обратной связи в этот репозиторий нет

## Обогащение и проверка

Обогащение, актуализация версии и проверка целостности - локальный навык `data/skills/vpn-list-update` (индекс - `data/skills/_index_skills_pl.md`). Скрипты запускаются из корня репозитория:

```bash
python3 data/skills/vpn-list-update/scripts/enrich.py --catalog data/lists/catalog.json
python3 data/skills/vpn-list-update/scripts/validate.py --catalog data/lists/catalog.json
```

`enrich.py` скачивает источники из реестра `sources.json` (посервисные списки `itdoginfo/allow-domains` и `v2fly/domain-list-community`, bulk-списки `itdoginfo/allow-domains` geoblock и inside-raw, `antifilter`, `1andrevich/Re-filter-lists`, диапазоны ASN `ipverse/asn-ip`, `core.telegram.org`; форматы `plain`, `v2fly`, `clash`) и добавляет только новые записи; при недоступном источнике каталог не портится. Источники с `refresh: true` обновляются: их записи, пропавшие в источнике, удаляются; записи `manual` не трогаются, при недоступном источнике обновление пропускается. `validate.py` проверяет контракт: схему, формат значений, дубликаты, лимиты. Ручные записи - с `source: manual`; скрипты их не удаляют и не изменяют. Детали - `data/skills/vpn-list-update/reference.md`.

## Структура файлов и директорий

| Путь | Назначение |
|------|------------|
| `README.md` | Документация репозитория и контракт формата каталога |
| `AGENTS.md` | Инструкции AI-агента |
| `.gitignore` | Исключения git: секреты, кэши, tooling, `tmp/` |
| `.gitattributes` | Окончания строк (LF) |
| `data/lists/catalog.json` | Каталог списков VPN - главный артефакт репозитория |
| `data/skills/vpn-list-update/` | Локальный навык обогащения и актуализации каталога |
| `data/skills/vpn-list-update/SKILL.md` | Инструкция навыка |
| `data/skills/vpn-list-update/reference.md` | Детальный контракт каталога и реестра источников |
| `data/skills/vpn-list-update/sources.json` | Реестр внешних источников обогащения |
| `data/skills/vpn-list-update/scripts/enrich.py` | Обогащение каталога, только добавление |
| `data/skills/vpn-list-update/scripts/validate.py` | Проверка целостности каталога |
| `data/skills/_index_skills_pl.md` | Индекс локальных навыков `data/skills/` |
| `doc/standards/` | Пакет стандартов 4.15.0 - только чтение; обновляется навыком `hub-sync-standards` из хаба `project_standards` |
| `doc/standards/_index_standards.md` | Точка входа пакета стандартов: реестр, карта маршрутизации, версия |
| `doc/standards/project_standards.md` | Основной стандарт проекта |
| `doc/standards/code_standards.md` | Канон написания кода по языкам; линтеры |
| `doc/standards/console_ui_standards.md` | Контракт консольного UI |
| `doc/standards/deploy_standards.md` | OS-agnostic ядро деплоя Python-проекта |
| `doc/standards/deploy_lin_standards.md` | Деплой на Linux |
| `doc/standards/deploy_win_standards.md` | Деплой на Windows |
| `doc/standards/deploy_docker_standards.md` | Развертывание Docker-приложений |
| `doc/standards/deploy_hyperv_standards.md` | Развертывание Hyper-V |
| `doc/standards/software_doc_standards.md` | Шаблон документа установки ПО |
| `doc/standards/index_nav_standards.md` | Канон навигационных документов: индексы, карты маршрутизации, каркас AGENTS.md |
| `doc/standards/repo_info_doc_standards.md` | Канон README и человеческих документов |
| `doc/standards/human_text_standards.md` | Канон текстов для человека |
| `doc/standards/human_text_dict_standards.md` | Словарь стоп-слов русского текста |
| `doc/standards/human_text_dict_ai_standards.md` | Словарь маркеров ИИ-текста |
| `doc/standards/human_text_allowlist_standards.md` | Словарь канон-лексики |
| `doc/standards/change_request_standards.md` | Канон заданий на изменение (CR) |
| `doc/standards/skill_plain_standards.md` | Стандарт plain-навыков |
| `doc/standards/skill_anthropic_standards.md` | Стандарт навыков формата Anthropic Agent Skills |
| `doc/standards/opencode_tool_standards.md` | Стандарт кастомных tools opencode |
| `doc/standards/web_standards.md` | Стандарт веб-подсистемы |
| `doc/skills/` | Общие навыки `glob-*` (формат Anthropic); приходят синхронизацией хаба |
| `doc/skills/_index_skills_repo.md` | Индекс навыков репозитория |
| `doc/skills/_index_skills_hub.md` | Сводный индекс навыков хаба; приходит синхронизацией, локально не ведется |
| `doc/specs/_index_specs.md` | Индекс спецификаций |
| `doc/change_requests/` | Задания на изменение (CR) |
| `doc/change_requests/_index_change_requests.md` | Индекс заданий на изменение |
| `doc/agent_questions/` | Транзитная папка уточняющих вопросов; не коммитится, кроме `.gitkeep` |

## Обновление стандарта

Пакет `doc/standards/` правится только в хабе `project_standards`; здесь - только чтение. Обновление пакета в этом репозитории - навыком `hub-sync-standards` из хаба.
