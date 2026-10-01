#!/usr/bin/env python3
"""Обогащение каталога списков VPN из внешних источников - только добавление.

Скрипт загружает catalog.json и реестр источников sources.json, скачивает
записи источников и добавляет в группы каталога только новые значения.
Существующие записи не изменяются и не удаляются: ручные правки сохраняются.
При отсутствии изменений файл каталога не перезаписывается.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

SCHEMA_VERSION = 1
DEFAULT_SOURCES_NAME = "sources.json"
DEFAULT_TIMEOUT_SEC = 30
DEFAULT_MIN_PREFIX_V4 = 16
DEFAULT_MIN_PREFIX_V6 = 32
DEFAULT_MAX_ENTRIES = 5000
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
USER_AGENT = "vpn-list-update/1.1"
COMPACT_DATE_FORMAT = "%y%m%d"
LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_SOURCE_FORMAT = "plain"
KNOWN_FORMATS = ("plain", "v2fly", "clash")
V2FLY_STRIP_PREFIXES = ("full:", "domain:")
V2FLY_SKIP_PREFIXES = ("keyword:", "regexp:", "process:")
CLASH_SUPPORTED_RULES = ("DOMAIN", "DOMAIN-SUFFIX", "IP-CIDR", "IP-CIDR6")
INCLUDE_RE = re.compile(r"^include:(?P<name>.+)\Z")
MAX_INCLUDE_DEPTH = 5
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}\Z)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:[a-z]{2,63}|xn--[a-z0-9-]{2,59})\Z",
)


class DataError(Exception):
    """Ошибка данных: некорректный каталог или реестр источников."""


def log(marker: str, message: str) -> None:
    """Вывести строку журнала в формате строгого режима без логгера.

    Args:
        marker: маркер строки: ``[i]``, ``[!]`` или ``[*]``.
        message: текст сообщения, без точки в конце.
    """
    stamp = datetime.now().strftime(LOG_TIME_FORMAT)
    print(f"{stamp} [{marker}] {message}")


def load_json(path: Path, what: str) -> dict:
    """Прочитать JSON-файл и вернуть словарь.

    Args:
        path: путь до файла.
        what: имя сущности для сообщений об ошибках.

    Returns:
        Разобранный JSON-объект.

    Raises:
        DataError: файл не найден, не читается или не является объектом JSON.
    """
    if not path.is_file():
        raise DataError(f"{what}: файл не найден: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise DataError(f"{what}: файл не читается: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"{what}: некорректный JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DataError(f"{what}: ожидается JSON-объект")
    return data


def normalize_domain(raw: str) -> str | None:
    """Привести строку источника к каноническому домену.

    Args:
        raw: строка из источника.

    Returns:
        Домен в нижнем регистре без завершающей точки или None, если строка
        не является корректным доменом.
    """
    value = raw.strip().lower().rstrip(".")
    if DOMAIN_RE.match(value) is None:
        return None
    return value


def normalize_cidr(raw: str) -> tuple[str, int] | None:
    """Привести строку источника к канонической подсети.

    Args:
        raw: строка из источника.

    Returns:
        Кортеж (каноническая запись CIDR, версия IP) или None, если строка
        не является адресом или подсетью.
    """
    try:
        network = ipaddress.ip_network(raw.strip(), strict=False)
    except ValueError:
        return None
    return str(network), network.version


def fetch_lines(url: str, timeout: int) -> list[str]:
    """Скачать текстовый источник и разбить его на строки.

    Args:
        url: адрес источника.
        timeout: таймаут загрузки в секундах.

    Returns:
        Список строк источника без обработки.

    Raises:
        OSError: сетевая ошибка, таймаут или недоступный HTTP-статус.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(raw) > MAX_DOWNLOAD_BYTES:
        raise OSError(f"Размер ответа превышает {MAX_DOWNLOAD_BYTES} байт")
    charset = "utf-8"
    return raw.decode(charset, errors="replace").splitlines()


def clean_lines(lines: list[str]) -> list[str]:
    """Убрать пустые строки и строки-комментарии источника.

    Args:
        lines: строки источника без обработки.

    Returns:
        Список непустых строк без ведущих пробелов и комментариев.
    """
    result: list[str] = []
    for line in lines:
        value = line.strip()
        if value and not value.startswith("#"):
            result.append(value)
    return result


def expand_v2fly_lines(
    url: str,
    timeout: int,
    cache: dict[str, list[str]],
    visiting: set[str],
    depth: int,
) -> list[str]:
    """Скачать источник формата v2fly и развернуть директивы include.

    Args:
        url: адрес файла источника.
        timeout: таймаут загрузки в секундах.
        cache: кэш развернутых файлов по адресу.
        visiting: адреса файлов в текущей ветке разворота, от циклов.
        depth: текущая глубина разворота include.

    Returns:
        Список строк источника с уже развернутыми include.

    Raises:
        OSError: файл недоступен, превышен размер или ошибка сети.
    """
    if url in cache:
        return cache[url]
    if url in visiting or depth > MAX_INCLUDE_DEPTH:
        return []
    visiting.add(url)
    try:
        result: list[str] = []
        for value in clean_lines(fetch_lines(url, timeout)):
            match = INCLUDE_RE.match(value)
            if match is None:
                result.append(value)
                continue
            include_name = match.group("name").strip()
            include_url = urljoin(url, include_name)
            try:
                result.extend(
                    expand_v2fly_lines(include_url, timeout, cache, visiting, depth + 1),
                )
            except (urllib.error.URLError, socket.timeout, OSError) as exc:
                reason = getattr(exc, "reason", exc)
                log("*", f"include {include_name}: недоступен ({reason})")
    finally:
        visiting.discard(url)
    cache[url] = result
    return result


def fetch_source_lines(url: str, source_format: str, timeout: int) -> list[str]:
    """Скачать строки источника с учетом его формата.

    Args:
        url: адрес источника.
        source_format: формат источника: plain, v2fly или clash.
        timeout: таймаут загрузки в секундах.

    Returns:
        Список непустых строк источника без комментариев.

    Raises:
        OSError: сетевая ошибка, таймаут или недоступный HTTP-статус.
    """
    if source_format == "v2fly":
        return expand_v2fly_lines(url, timeout, {}, set(), 1)
    return clean_lines(fetch_lines(url, timeout))


def extract_source_value(raw: str, source_format: str) -> tuple[str | None, bool]:
    """Извлечь значение записи из строки источника по его формату.

    Args:
        raw: непустая строка источника без комментария.
        source_format: формат источника: plain, v2fly или clash.

    Returns:
        Пару (значение, поддерживается); для неподдерживаемой строки
        значение равно None, а второй элемент - False.
    """
    if source_format == "plain":
        return raw, True
    if source_format == "v2fly":
        token = raw.split()[0]
        for prefix in V2FLY_STRIP_PREFIXES:
            if token.startswith(prefix):
                return token[len(prefix):], True
        if token.startswith(V2FLY_SKIP_PREFIXES):
            return None, False
        return token, True
    if source_format == "clash":
        parts = [part.strip() for part in raw.split(",")]
        if len(parts) < 2 or parts[0] not in CLASH_SUPPORTED_RULES:
            return None, False
        return parts[1], True
    return None, False


def load_sources(path: Path) -> list[dict]:
    """Загрузить и проверить реестр источников.

    Args:
        path: путь до sources.json.

    Returns:
        Список валидных источников с ключами id, url, group, kind, enabled.

    Raises:
        DataError: реестр не соответствует формату.
    """
    data = load_json(path, "Реестр источников")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise DataError("Реестр источников: отсутствует непустой список sources")
    valid: list[dict] = []
    for item in sources:
        if not isinstance(item, dict):
            raise DataError("Реестр источников: источник не является объектом")
        for key in ("id", "url", "group", "kind"):
            if not isinstance(item.get(key), str) or not item[key]:
                raise DataError(f"Реестр источников: источник без поля {key}")
        if item["kind"] not in ("domain", "cidr"):
            raise DataError(f"Реестр источников: {item['id']}: Некорректный kind: {item['kind']}")
        source_format = item.get("format", DEFAULT_SOURCE_FORMAT)
        if source_format not in KNOWN_FORMATS:
            raise DataError(
                f"Реестр источников: {item['id']}: Некорректный format: {source_format}",
            )
        item["format"] = source_format
        valid.append(item)
    return valid


def entry_sort_key(entry: dict) -> tuple[str, str]:
    """Ключ детерминированной сортировки записей группы.

    Args:
        entry: запись каталога.

    Returns:
        Кортеж (kind, value) для сортировки.
    """
    return (entry["kind"], entry["value"])


def write_catalog(catalog_path: Path, catalog: dict) -> None:
    """Записать каталог атомарно: временный файл и замена.

    Args:
        catalog_path: путь до catalog.json.
        catalog: данные каталога для записи.
    """
    tmp_path = catalog_path.with_name(catalog_path.name + ".tmp")
    payload = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, catalog_path)


def parse_args() -> argparse.Namespace:
    """Разобрать аргументы командной строки.

    Returns:
        Пространство имен с аргументами.
    """
    default_sources = Path(__file__).resolve().parent.parent / DEFAULT_SOURCES_NAME
    parser = argparse.ArgumentParser(
        description="Обогащение каталога списков VPN из внешних источников - только добавление",
    )
    parser.add_argument("--catalog", required=True, type=Path, help="путь до catalog.json")
    parser.add_argument(
        "--sources",
        type=Path,
        default=default_sources,
        help=f"путь до реестра источников (по умолчанию: {DEFAULT_SOURCES_NAME} в каталоге навыка)",
    )
    parser.add_argument("--only", default=None, help="обработать только источники этой группы")
    parser.add_argument("--dry-run", action="store_true", help="не записывать каталог, только отчет")
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT_SEC, help="таймаут загрузки источника, сек",
    )
    parser.add_argument(
        "--min-prefix-v4",
        type=int,
        default=DEFAULT_MIN_PREFIX_V4,
        help="минимальная длина префикса IPv4: более широкие подсети отбрасываются",
    )
    parser.add_argument(
        "--min-prefix-v6",
        type=int,
        default=DEFAULT_MIN_PREFIX_V6,
        help="минимальная длина префикса IPv6: более широкие подсети отбрасываются",
    )
    parser.add_argument(
        "--max-entries", type=int, default=DEFAULT_MAX_ENTRIES, help="максимум записей в группе",
    )
    return parser.parse_args()


def main() -> int:
    """Точка входа: обогащение каталога.

    Returns:
        0 - успех; 1 - ошибка данных или недоступный источник; 2 - ошибка вызова.
    """
    args = parse_args()
    try:
        catalog = load_json(args.catalog, "Каталог")
        sources = load_sources(args.sources)
    except DataError as exc:
        log("!", str(exc))
        return 1

    if catalog.get("schema") != SCHEMA_VERSION:
        log("!", f"Каталог: несовместимая схема: {catalog.get('schema')}, ожидается {SCHEMA_VERSION}")
        return 1
    groups = catalog.get("groups")
    if not isinstance(groups, dict):
        log("!", "Каталог: отсутствует объект groups")
        return 1
    if args.only is not None and args.only not in groups:
        log("!", f"Каталог: неизвестная группа: {args.only}")
        return 1

    today = datetime.now().strftime(COMPACT_DATE_FORMAT)
    existing: dict[str, set[str]] = {name: set() for name in groups}
    for group_name, entries in groups.items():
        if not isinstance(entries, list):
            log("!", f"Каталог: группа {group_name}: ожидается массив записей")
            return 1
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("value"), str):
                existing[group_name].add(entry["value"])
    pending: dict[str, set[str]] = {name: set() for name in groups}
    new_entries: dict[str, list[dict]] = {}
    added_total = 0
    failed_sources = 0

    for source in sources:
        sid = source["id"]
        if not source.get("enabled", True):
            log("i", f"{sid}: Источник отключен, пропуск")
            continue
        if args.only is not None and source["group"] != args.only:
            continue
        if source["group"] not in groups:
            log("!", f"{sid}: Неизвестная группа каталога: {source['group']}")
            failed_sources += 1
            continue
        try:
            lines = fetch_source_lines(source["url"], source["format"], args.timeout)
        except (urllib.error.URLError, socket.timeout, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            log("!", f"{sid}: Источник недоступен ({reason})")
            failed_sources += 1
            continue

        stats = {
            "total": 0,
            "added": 0,
            "dup": 0,
            "bad": 0,
            "wide": 0,
            "limit": 0,
            "unsupported": 0,
        }
        for line in lines:
            stats["total"] += 1
            group = source["group"]
            if len(existing[group]) + len(pending[group]) >= args.max_entries:
                stats["limit"] += 1
                continue
            value, supported = extract_source_value(line, source["format"])
            if not supported or value is None:
                stats["unsupported"] += 1
                continue
            if source["kind"] == "domain":
                normalized = normalize_domain(value)
                kind = "domain"
            else:
                normalized_ip = normalize_cidr(value)
                if normalized_ip is None:
                    normalized = None
                    kind = ""
                else:
                    canonical, ip_version = normalized_ip
                    min_prefix = args.min_prefix_v4 if ip_version == 4 else args.min_prefix_v6
                    if canonical.split("/")[1].isdigit() and int(canonical.split("/")[1]) < min_prefix:
                        stats["wide"] += 1
                        continue
                    normalized = canonical
                    kind = f"cidr_v{ip_version}"
            if normalized is None:
                stats["bad"] += 1
                continue
            if normalized in existing[group] or normalized in pending[group]:
                stats["dup"] += 1
                continue
            pending[group].add(normalized)
            new_entries.setdefault(group, []).append(
                {"value": normalized, "kind": kind, "source": sid, "added": today, "comment": ""},
            )
            stats["added"] += 1
        added_total += stats["added"]
        skipped = (
            stats["dup"] + stats["bad"] + stats["wide"] + stats["unsupported"] + stats["limit"]
        )
        log(
            "i",
            f"{sid}: Строк {stats['total']}, добавлено {stats['added']}, "
            f"пропущено {skipped} (дубликаты {stats['dup']}, некорректные {stats['bad']}, "
            f"широкие {stats['wide']}, неподдерживаемые {stats['unsupported']}, "
            f"лимит {stats['limit']})",
        )

    if args.dry_run:
        log("i", f"Сухой запуск: было бы добавлено {added_total}, каталог не изменялся")
        return 1 if failed_sources else 0
    if added_total == 0:
        log("i", "Новых записей нет, каталог не перезаписывался")
        return 1 if failed_sources else 0

    for group_name in groups:
        merged = [entry for entry in groups[group_name] if isinstance(entry, dict)]
        merged.extend(new_entries.get(group_name, []))
        merged.sort(key=entry_sort_key)
        groups[group_name] = merged
    catalog["version"] = today
    try:
        write_catalog(args.catalog, catalog)
    except OSError as exc:
        log("!", f"Каталог: ошибка записи: {exc}")
        return 1
    log("i", f"Каталог обновлен: добавлено {added_total}, версия {today}")
    return 1 if failed_sources else 0


if __name__ == "__main__":
    sys.exit(main())
