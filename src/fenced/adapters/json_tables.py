"""The catalog, the margin table, the purchase history and the roster, each read from a JSON file.

Each file is checked here for its shape and nothing more. A row that is not an object, a
name that is not text or a name written twice is refused with the file and the position it
was found at. What a price, a margin or a past order is worth stays with the domain, which
refuses an amount it will not do arithmetic with when it is asked to.

A file that is not there is refused rather than read as empty, because an empty catalog
and a missing catalog are two different problems.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fenced.adapters.json_files import FileError, read_json
from fenced.domain.matching import MatchError, Seller

# The fields of one seller in the roster file, which are the fields of `Seller`.
SELLER_FIELDS = ("name", "segments", "smallest_ticket", "largest_ticket", "languages")


def _held(path: Path, kind: type, what: str) -> object:
    """What one file holds, refused when the file is not there or is not of that kind."""
    if not path.is_file():
        raise FileError(f"there is no {what} at {path}")
    held = read_json(path, None)
    if not isinstance(held, kind):
        raise FileError(f"{path} holds a {type(held).__name__} and not a {kind.__name__}")
    return held


def _named_rows(path: Path, what: str) -> list[tuple[str, dict]]:
    """Each row of a list file with its name, refusing a row with no name or a name twice."""
    rows = []
    seen = set()
    for position, row in enumerate(_held(path, list, what), start=1):
        where = f"row {position} of {path}"
        if not isinstance(row, dict):
            raise FileError(f"{where} is not an object")
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            raise FileError(f"{where} has no name written as text")
        if name.strip() in seen:
            raise FileError(f"{where} carries the name {name.strip()!r} a second time")
        seen.add(name.strip())
        rows.append((name.strip(), row))
    return rows


def _by_name(path: Path, what: str) -> dict[str, object]:
    """An object file that maps a name to a value, with each name trimmed."""
    table: dict[str, object] = {}
    for name, value in _held(path, dict, what).items():
        if not name.strip():
            raise FileError(f"{path} carries a {what} row with no name")
        if name.strip() in table:
            raise FileError(f"{path} carries the name {name.strip()!r} a second time")
        table[name.strip()] = value
    return table


class JsonCatalog:
    """The catalog one file holds, as a list of rows with a name and a price."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def prices(self) -> dict[str, object]:
        """Every product in the file, by its name, with the price the row gives it."""
        prices = {}
        for name, row in _named_rows(self.path, "catalog"):
            if "price" not in row:
                raise FileError(f"{name!r} in {self.path} has no price")
            prices[name] = row["price"]
        return prices


class JsonMargins:
    """The margin table one file holds, as an object from a product name to its margin."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def margins(self) -> dict[str, object]:
        """Every product in the file, by its name, with its margin."""
        return _by_name(self.path, "margin table")


class JsonHistory:
    """The purchase history one file holds, as an object from an address to its past orders.

    An address is looked up in lower case, because the store keeps a lead under its address
    in lower case and one person should have one history.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._held: Mapping[str, object] | None = None

    def orders(self, address: str) -> list[object]:
        """The past orders of this address as the file has them, and an empty list otherwise."""
        if self._held is None:
            held = {}
            for name, orders in _by_name(self.path, "history").items():
                if not isinstance(orders, list):
                    raise FileError(f"the history of {name!r} in {self.path} is not a list")
                if name.lower() in held:
                    raise FileError(f"{self.path} carries the address {name!r} a second time")
                held[name.lower()] = orders
            self._held = held
        return list(self._held.get(address.lower(), []))


class JsonRoster:
    """The roster one file holds, as a list of rows with the fields of a seller."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def sellers(self) -> list[Seller]:
        """Every seller in the file, in the order it is written there.

        A row the domain refuses as a seller is refused here with the file it came from, so
        a broken roster reads as a broken file and not as a lead nobody can take.
        """
        sellers = []
        for name, row in _named_rows(self.path, "roster"):
            missing = [field for field in SELLER_FIELDS if field not in row]
            if missing:
                raise FileError(f"{name!r} in {self.path} has no {', '.join(missing)}")
            try:
                sellers.append(Seller(**{field: row[field] for field in SELLER_FIELDS}))
            except MatchError as refused:
                raise FileError(f"{name!r} in {self.path} is not a seller, {refused}") from refused
        return sellers
