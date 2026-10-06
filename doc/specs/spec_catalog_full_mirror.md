# Спецификация: полное зеркало каталога под роутер

- Слаг: catalog-full-mirror
- Источник: `doc/change_requests/cr_catalog-full-mirror.md`
- Дата: 2026-10-01

Реализация согласованного CR `cr_catalog-full-mirror.md`: каталог `vpn_list` становится единственным источником истины и вбирает все ресурсы, которые маршрутизирует роутер (`rtr-vpn-setup`), кроме ресурсов РФ.

---

## 1. Юзкейсы

1. Потребитель (навык `rtr-vpn-setup` в `arch_desktop_setup`) забирает `data/lists/catalog.json` и строит из него `exclusions.txt`, `domains.txt`, `networks.txt` полным зеркалом, без ручных списков.
2. Обогащение каталога из внешних источников: сервисные списки (`allow-domains`, v2fly) и bulk-списки (geoblock, antifilter, Re-filter).
3. Проверка целостности каталога: схема, группы, значения, дубликаты, лимиты, правило РФ.

## 2. Решения

### 2.1. Контракт групп - 15 групп

`youtube`, `telegram`, `meta`, `twitter`, `discord`, `payments`, `ai`, `google`, `microsoft`, `dev`, `software`, `distros`, `torrents`, `geoblock`, `blocked-subnets`.

### 2.2. Правило ресурсов РФ

- Домены с TLD `.ru`, `.su`, `.рф` (`xn--p1ai`) в каталог не берутся.
- `enrich.py` отбрасывает такие домены при разборе любого источника.
- `validate.py` считает такую запись ошибкой.
- Три существующие записи (`bestchange.ru`, `mastercard.ru`, `visa.com.ru`) удалены как явное исключение из правила «только добавление».

### 2.3. Источники

Сервисные (v2fly, формат `v2fly`): `openai`, `anthropic`, `cursor`, `github`, `jetbrains`, `microsoft`, `protonmail`, `category-ai-!cn`.

Bulk: allow-domains `Categories/geoblock.lst` и `Russia/inside-raw.lst` - домены, группа `geoblock`; antifilter `community.lst` и `subnet.lst`, Re-filter `discord_ips.lst` и `community_ips.lst` - подсети, группа `blocked-subnets`.

### 2.4. Подсети

Ручные записи (`source: manual`) восполняют диапазоны роутера, которых нет в источниках:

- `youtube`: 14 диапазонов Google; слишком широкие `142.250.0.0/15` и `192.178.0.0/15` разбиты на `/16` (итого 16 записей);
- `meta`: `57.144.0.0/14` разбит на 4 `/16`, плюс `157.240.0.0/16` (итого 5 записей);
- `telegram`: `149.154.151.0/24`, `205.172.60.0/24`;
- `twitter`: `104.244.40.0/21`, `199.232.172.0/24` (Fastly, медиа Twitter).

Разбиение до `/16` - требование контракта: подсети не шире IPv4 `/16`.

### 2.5. Домены

Сервисные домены - из источников; остаток референса роутера (`network/vpn/adguard.md`) - ручными записями с привязкой к группам по разделам референса. Домены РФ отбрасываются.

### 2.6. Дедупликация обогащения

`enrich.py` дедуплицирует значения глобально (по всему каталогу), а не в пределах группы: контракт запрещает совпадение значений между группами, а bulk-источники пересекаются с сервисными.

## 3. Затрагиваемые компоненты

| Компонент | Изменение |
|-----------|-----------|
| `README.md` | контракт: список 15 групп, правило РФ, описание источников |
| `data/skills/vpn-list-update/SKILL.md` | группы, источники, правило РФ; версия |
| `data/skills/vpn-list-update/reference.md` | группы, источники, правило РФ, дедупликация |
| `data/skills/vpn-list-update/sources.json` | +15 источников |
| `data/skills/vpn-list-update/scripts/enrich.py` | фильтр РФ, глобальная дедупликация |
| `data/skills/vpn-list-update/scripts/validate.py` | 15 групп, проверка РФ |
| `data/lists/catalog.json` | удаление 3 РФ-записей, 15 групп, подсети и домены, версия |

## 4. Критерии приемки

- `python3 data/skills/vpn-list-update/scripts/validate.py --catalog data/lists/catalog.json` - код 0.
- В каталоге нет ни одной записи с TLD `.ru`, `.su`, `.рф`.
- 15 групп согласованы в `README.md`, `reference.md`, `validate.py` и `catalog.json`.
- Присутствуют все 20 диапазонов роутера (Google/YouTube, Telegram, Meta, Twitter, Fastly).
- Отчет `enrich.py` без недоступных источников.

## 5. Откат

`git restore` по `data/lists/catalog.json`, `data/skills/vpn-list-update/`, `README.md`.
