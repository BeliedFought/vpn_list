#!/usr/bin/env python3
"""Проверка целостности каталога списков VPN.

Скрипт валидирует catalog.json: схему, формат версии, состав групп, формат
значений (домены и подсети), дубликаты внутри и между группами, лимиты числа
записей и ширины подсетей. Каталог только читается.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_MIN_PREFIX_V4 = 16
DEFAULT_MIN_PREFIX_V6 = 32
DEFAULT_MAX_ENTRIES = 5000
KNOWN_GROUPS = ("youtube", "telegram", "meta", "twitter", "discord", "payments", "ai")
KNOWN_KINDS = ("domain", "cidr_v4", "cidr_v6")
ENTRY_REQUIRED_KEYS = ("value", "kind", "source", "added")
COMPACT_DATE_FORMAT = "%y%m%d"
LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
VERSION_RE = re.compile(r"^\d{6}\Z")
DOMAIN_RE = re.compile(r"^(?=.{1,253}\Z)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\Z")


def log(marker: str, message: str) -> None:
    """Вывести строку журнала в формате строгого режима без логгера.

    Args:
        marker: маркер строки: ``[i]``, ``[!]`` или ``[*]``.
        message: текст сообщения, без точки в конце.
    """
    stamp = datetime.now().strftime(LOG_TIME_FORMAT)
    print(f"{stamp} [{marker}] {message}")


def is_valid_compact_date(value: str) -> bool:
    """Проверить, что строка является датой в формате yymmdd.

    Args:
        value: проверяемая строка.

    Returns:
        True, если строка разбирается как дата yymmdd.
    """
    try:
        datetime.strptime(value, COMPACT_DATE_FORMAT)
    except ValueError:
        return False
    return True


def check_value(value: str, kind: str, min_prefix_v4: int, min_prefix_v6: int) -> str | None:
    """Проверить соответствие значения записи ее типу.

    Args:
        value: значение записи (домен или CIDR).
        kind: тип записи: domain, cidr_v4 или cidr_v6.
        min_prefix_v4: минимальная длина префикса IPv4.
        min_prefix_v6: минимальная длина префикса IPv6.

    Returns:
        Текст ошибки или None, если значение корректно.
    """
    if kind == "domain":
        if DOMAIN_RE.match(value) is None:
            return "некорректный домен"
        return None
    try:
        network = ipaddress.ip_network(value, strict=True)
    except ValueError:
        return "некорректная подсеть или не каноническая запись CIDR"
    if kind == "cidr_v4" and network.version != 4:
        return "в записи cidr_v4 указан не IPv4-адрес"
    if kind == "cidr_v6" and network.version != 6:
        return "в записи cidr_v6 указан не IPv6-адрес"
    min_prefix = min_prefix_v4 if network.version == 4 else min_prefix_v6
    if network.prefixlen < min_prefix:
        return f"подсеть шире минимума: /{network.prefixlen} при минимуме /{min_prefix}"
    return None


def parse_args() -> argparse.Namespace:
    """Разобрать аргументы командной строки.

    Returns:
        Пространство имен с аргументами.
    """
    parser = argparse.ArgumentParser(
        description="Проверка целостности каталога списков VPN (catalog.json)",
    )
    parser.add_argument("--catalog", required=True, type=Path, help="путь до catalog.json")
    parser.add_argument(
        "--min-prefix-v4",
        type=int,
        default=DEFAULT_MIN_PREFIX_V4,
        help="минимальная длина префикса IPv4: более широкие подсети - ошибка",
    )
    parser.add_argument(
        "--min-prefix-v6",
        type=int,
        default=DEFAULT_MIN_PREFIX_V6,
        help="минимальная длина префикса IPv6: более широкие подсети - ошибка",
    )
    parser.add_argument(
        "--max-entries", type=int, default=DEFAULT_MAX_ENTRIES, help="максимум записей в группе",
    )
    return parser.parse_args()


def validate(catalog_path: Path, min_prefix_v4: int, min_prefix_v6: int, max_entries: int) -> list[str]:
    """Проверить каталог и собрать список ошибок.

    Args:
        catalog_path: путь до catalog.json.
        min_prefix_v4: минимальная длина префикса IPv4.
        min_prefix_v6: минимальная длина префикса IPv6.
        max_entries: максимум записей в группе.

    Returns:
        Список текстов ошибок; пустой список означает валидный каталог.
    """
    errors: list[str] = []
    if not catalog_path.is_file():
        return [f"Файл не найден: {catalog_path}"]
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        return [f"Файл не читается: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"Некорректный JSON: {exc}"]
    if not isinstance(catalog, dict):
        return ["Корневой элемент не является JSON-объектом"]

    if catalog.get("schema") != SCHEMA_VERSION:
        errors.append(f"Неизвестная схема: {catalog.get('schema')}, ожидается {SCHEMA_VERSION}")
    version = catalog.get("version")
    if not isinstance(version, str) or VERSION_RE.match(version) is None:
        errors.append(f"Версия каталога не в формате yymmdd: {version!r}")
    elif not is_valid_compact_date(version):
        errors.append(f"Версия каталога не является датой: {version}")

    groups = catalog.get("groups")
    if not isinstance(groups, dict) or not groups:
        errors.append("Отсутствует непустой объект groups")
        return errors

    seen: dict[str, tuple[str, int]] = {}
    total = 0
    domains = 0
    subnets = 0
    max_added = ""
    for group_name, entries in groups.items():
        if group_name not in KNOWN_GROUPS:
            errors.append(f"Группа {group_name} вне контракта групп: {', '.join(KNOWN_GROUPS)}")
            continue
        if not isinstance(entries, list):
            errors.append(f"Группа {group_name}: ожидается массив записей")
            continue
        if len(entries) > max_entries:
            errors.append(f"Группа {group_name}: записей {len(entries)} при лимите {max_entries}")
        local_seen: set[str] = set()
        for index, entry in enumerate(entries):
            label = f"Группа {group_name}, запись {index}"
            if not isinstance(entry, dict):
                errors.append(f"{label}: ожидается объект")
                continue
            missing = [key for key in ENTRY_REQUIRED_KEYS if key not in entry]
            if missing:
                errors.append(f"{label}: отсутствуют поля: {', '.join(missing)}")
                continue
            value = entry["value"]
            kind = entry["kind"]
            if not isinstance(value, str) or not value:
                errors.append(f"{label}: поле value не непустая строка")
                continue
            if not isinstance(kind, str) or kind not in KNOWN_KINDS:
                errors.append(f"{label}: некорректный kind: {kind!r}")
                continue
            if not isinstance(entry["source"], str) or not entry["source"]:
                errors.append(f"{label} ({value}): поле source не непустая строка")
            added = entry["added"]
            if not isinstance(added, str) or not is_valid_compact_date(added):
                errors.append(f"{label} ({value}): поле added не дата yymmdd: {added!r}")
            elif isinstance(version, str) and VERSION_RE.match(version) is not None:
                if added > max_added:
                    max_added = added
            comment = entry.get("comment", "")
            if not isinstance(comment, str):
                errors.append(f"{label} ({value}): поле comment не строка")
            problem = check_value(value, kind, min_prefix_v4, min_prefix_v6)
            if problem is not None:
                errors.append(f"{label}: {problem}")
                continue
            if value in local_seen:
                errors.append(f"Группа {group_name}: дубликат внутри группы: {value}")
            else:
                local_seen.add(value)
                if value in seen:
                    first_group, first_index = seen[value]
                    errors.append(
                        f"Дубликат между группами: {value} "
                        f"(уже в группе {first_group}, запись {first_index})",
                    )
                else:
                    seen[value] = (group_name, index)
            total += 1
            if kind == "domain":
                domains += 1
            else:
                subnets += 1

    if (
        isinstance(version, str)
        and VERSION_RE.match(version) is not None
        and max_added
        and version < max_added
    ):
        errors.append(f"Версия каталога {version} старше даты добавления записей {max_added}")

    log(
        "i",
        f"Состав: групп {len(groups)}, записей {total} (домены {domains}, подсети {subnets})",
    )
    return errors


def main() -> int:
    """Точка входа: проверка каталога.

    Returns:
        0 - каталог валиден; 1 - найдены ошибки; 2 - ошибка вызова.
    """
    args = parse_args()
    errors = validate(args.catalog, args.min_prefix_v4, args.min_prefix_v6, args.max_entries)
    if errors:
        for message in errors:
            log("!", message)
        log("!", f"Итог: ошибок {len(errors)}")
        return 1
    log("i", "Каталог валиден")
    return 0


if __name__ == "__main__":
    sys.exit(main())
