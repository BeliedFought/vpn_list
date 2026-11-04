<!-- START static -->
# AGENTS.md

Standard version: 5.0.0

This file contains instructions for AI agents working with this project.

## Session Entry Points

- `@doc/standards/_index_standards.md` - standards package index (registry, routing map, package version); read it first
- `@doc/skills/_index_skills_repo.md` - repository skills index
- `@doc/specs/_index_specs.md` - specifications index
- `data/memory/memory.md`, `data/memory/decisions.md`, `data/memory/env.md` - agent memory minimum when `data/memory/` exists; update it after significant decisions
- Ignore `.backup/`, `.trash/`, `.arch/`, `.opencode/`, `.kilo/` unless the user explicitly asks
- Tagging an `@_index_*.md` file without a task runs its index auto-update procedure

## Language & Typography Matrix

| Contour | Artifacts | Language |
| --- | --- | --- |
| Human | Chat responses, `README.md`, user guides, `doc/specs/`, implementation plans, `doc/change_requests/`, UI and console text through `t()` | Russian |
| Agent and code | `AGENTS.md`, `CLAUDE.md`, standards, indexes, skills, code, comments, docstrings, technical logs (`logger.*`), commit messages, subagent communication | English |

Typography applies to both contours: hyphen-minus `-` only (no em dash or en dash), letter `е` without diaeresis, no ellipsis, no emoji, no exclamation marks, no non-breaking or narrow spaces. User-facing text follows `doc/standards/human_text_standards.md`; the machine override is `~/.config/opencode/AGENTS.md`; the core rule is `project_standards.md` (04.03).

## Development Process

- Use the superpowers skills: `brainstorming` (design exploration and task classification), `writing-plans` (specs and implementation plans), `test-driven-development`, `systematic-debugging`, `subagent-driven-development` or `executing-plans`, `verification-before-completion`, `writing-skills`.
- Classify work as Spike, Bounded, or Architectural before implementation; ratchet up when hidden complexity appears.
- Write specifications and plans in Russian; keep them in `doc/specs/` (`init/` before MVP, `spec_<module>.md` after).
- Delegate isolated search, audit, and verification work to subagents; briefs and answers are English, the user summary is Russian.
- Fact-checking cascade: local code and standards -> `context7` MCP -> `github` MCP -> web search for exact error text -> ask the user when unverifiable.

## Safety, Git & Boundaries

- Mutate code or the system only after the execution trigger `ДЕЛАЙ` or `GO`; design-stage approvals inside `brainstorming` do not replace it.
- Delete repository files only by moving them to `.trash/<slug>_<YYYYMMDDHHMM>/` with `MANIFEST.md`; exceptions: `tmp/` contents, git-native mirror/package synchronization, and `.trash/` purged only on explicit request.
- Run `sudo`, `su`, and `pkexec` only per the privilege levels in `project_standards.md` (05.04); never hardcode secrets.
- Git: one `master` branch; English Conventional Commits `<type>(<scope>): <imperative summary>`; authorship from `whoami` and `hostname`; no AI mention; never bump the package version without an explicit request.
- `CLAUDE.md` mirror: maintained permanently in the hub; deleted by default in derived repositories unless a repo override exists.
<!-- END static -->

<!-- START repo-specific -->
## Специфика репозитория: vpn-list

## Назначение

Приватный репозиторий - каталог списков сайтов, которые ходят через VPN. Главный артефакт и единственный источник истины - `data/lists/catalog.json`; контракт формата - в README.md. Потребители (навыки других репозиториев) забирают каталог сами и преобразуют в свои форматы: экспорт, доставка на устройства и обратная связь в этом репозитории не ведутся.

Сам репозиторий runnable-проектом не является: данныхый репозиторий с одним локальным навыком. Точка входа сессии для задач каталога - `doc/change_requests/_index_change_requests.md` и `data/skills/_index_skills_pl.md`.

<!-- START generated-commands -->
Не runnable-проект: шаги установки, запуска, test/lint/typecheck/build отсутствуют; команды установки, запуска и тестов не добавлять.

Реальные операции:

- Обогащение каталога из внешних источников: `python3 data/skills/vpn-list-update/scripts/enrich.py --catalog data/lists/catalog.json`
- Проверка целостности каталога: `python3 data/skills/vpn-list-update/scripts/validate.py --catalog data/lists/catalog.json`
- Актуализация локальных индексов (`doc/skills/_index_skills_repo.md`, `doc/specs/_index_specs.md`, `data/skills/_index_skills_pl.md`) - навыком `glob-update-indexes`, а не ручным редактированием
- Обновление пакета `doc/standards/` - только навыком `hub-sync-standards` из хаба `project_standards`, локально пакет не правится
<!-- END generated-commands -->

## Структура репозитория

Полная таблица папок и файлов - в README.md. Поведенческие правила:

- `data/lists/catalog.json` - главный артефакт; изменения содержимого - с поднятием `version` (формат `yymmdd`) и последующим validate
- Каталог - только добавление: внешние источники и ручные правки добавляют записи, существующие не удаляются и не изменяются; ручные записи - с `source: manual`
- Значение записи уникально по всему каталогу; подсети не шире IPv4 `/16` и IPv6 `/32`; записей в группе не больше 5000; порядок записей - сортировка по `kind`, затем `value`
- Реестр внешних источников - `data/skills/vpn-list-update/sources.json`; новый источник - после проверки доступности URL и формата строк
- Группы каталога - фиксированный набор (контракт в README); новая группа - сначала правка README и `reference.md`, потом каталога
- `doc/standards/` - пакет стандартов, только чтение; `doc/skills/` - общие навыки `glob-*`, приходят синхронизацией хаба и здесь не редактируются
- `doc/agent_questions/` - транзитная: содержимое не коммитится, кроме `.gitkeep`; `doc/change_requests/` - задания на изменение (CR), коммитится с индексом `_index_change_requests.md` (канон - `doc/standards/change_request_standards.md`)
- Отработанные артефакты (выполненное задание из `doc/change_requests/`, временная спецификация и т.п.) архивировать сразу после завершения работы - перенос в `.arch/` той папки, где они лежали; `.arch/` - архив: в индексы не вносится, содержимое не удаляется; удалять после себя - только `tmp/` (раздел 01.01)
- `tmp/` - разовые артефакты, если возникнут в работе: не коммитится; после коммита агент удаляет созданное; чистить можно в любой момент без предупреждения
- `.opencode/`, `.kilo/` - локальная служебная обвязка инструментов: не читать и в git не коммитить; исключение - кастомные tools opencode (`.opencode/plugins/`) по задачам стандарта `opencode_tool_standards.md`

## Навыки репозитория

Полный реестр - в `doc/skills/_index_skills_repo.md` (общие `glob-*`) и `data/skills/_index_skills_pl.md` (локальные).

Локальный навык (подробности - в `SKILL.md`):

- `vpn-list-update` - обогащение каталога из внешних источников (только добавление), актуализация версии, проверка целостности, оформление ручных дописываний; реестр источников и лимиты - в `reference.md` навыка

Локальные навыки живут в `data/skills/`, в синхронизацию хаба не входят; их индекс ведет `glob-update-indexes` (канон - `index_nav_standards.md`, раздел 06.02).

## Типичные scope коммитов

`catalog` (содержимое `data/lists/`), `skills` (навык и его индексы), `docs` (README, AGENTS.md), `cr` (задания на изменение).

## Особенности

- Формат каталога - контракт для внешних потребителей: любые изменения полей `catalog.json` - сначала правка контракта в README.md и `reference.md`, потом скриптов и данных
- Критерий коммита каталога - валидный validate: коммитить каталог с ошибками валидации нельзя
- Источники обогащения - посервисные списки репозитория `itdoginfo/allow-domains`; перед добавлением источника проверять доступность URL и формат строк
- Решение о связке «репозиторий каталога + навыки-потребители» синхронизировано с CR `cr_vpn-three-part-split.md` в репозитории `arch_desktop_setup` - при смене границ каталога обновить и его
- Перед началом правок проверять `git status`: в рабочем дереве возможны переходные состояния
<!-- END repo-specific -->

## Ссылки

- doc/standards/_index_standards.md - реестр стандартов и политика версионирования
- doc/standards/index_nav_standards.md - канон навигационных документов (индексы, каркас AGENTS.md - этого файла)
- doc/standards/repo_info_doc_standards.md - канон README и человеческих документов
- doc/standards/project_standards.md - раздел 06.01 (git и коммиты), 07.04 (версия пакета), 07.05 (редактирование стандарта)
- https://agents.md - канонический формат
