# Local Repository Skills Index

Entry point for `data/skills/` in `vpn_list`: lists local skills (`pr_loc`) excluded from shared indexes. Load this index rather than the full directory and use the routing map to open relevant skills. Decision order when norms are absent - `project_standards.md`, Section 07.06.

---

## Mandatory Application

Tagging this file requires applying relevant local skills, not merely reading the index:

1. Identify relevant skills via the routing map
2. Open the matched skill files and follow their instructions
3. Apply relevant skills whenever a matching task arises, even without explicit tagging

---

## Skill Registry

| Skill | Class | Scope | Auto-Apply | Version | Purpose |
|-------|-------|-------|------------|---------|---------|

## Anthropic Agent Skills (SKILL.md)

| Skill (dir) | Class | Scope | Version | Purpose |
|-------------|-------|-------|---------|---------|
| `vpn-list-update` | local | - | 1.2.0 | Обогащает и проверяет каталог списков VPN (data/lists/catalog.json) - скачивает записи из внешних источников и добавляет только новые, не удаляет и не меняет существующие, валидирует целостность, ловит дубликаты и некорректные записи |

---

## Routing Map

Maps task topics to skills (`index_nav_standards.md`, Section 04).

| Task Topic | Skill |
|------------|-------|
| Обогащает и проверяет каталог списков VPN (data/lists/catalog.json) - скачивает записи из внешних источников и добавляет только новые, не удаляет и не меняет существующие, валидирует целостность, ловит дубликаты и некорректные записи | `vpn-list-update` |

---

## Index Auto-Update

On any change to `data/skills/` (adding, removing, renaming, or updating skill frontmatter), rebuild this index with `glob-update-indexes`, refine purposes and routing map topics per `index_nav_standards.md` (Sections 03.03, 04), fix `metadata.purpose` and `metadata.topic` where the description yields a weak purpose or topic, and report added, updated, and removed entries.
