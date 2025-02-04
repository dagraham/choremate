from modules.model import DatabaseManager
from modules.common import fmt_dt, fmt_td
from rich.table import Table
from rich.box import HEAVY_EDGE
from datetime import datetime
import bisect
from .common import fmt_dt, fmt_td, log_msg, truncate_string


def decimal_to_base26(decimal_num):
    """
    Convert a decimal number to its equivalent base-26 string.

    Args:
        decimal_num (int): The decimal number to convert.

    Returns:
        str: The base-26 representation where 'a' = 0, 'b' = 1, ..., 'z' = 25.
    """
    if decimal_num < 0:
        raise ValueError("Decimal number must be non-negative.")

    if decimal_num == 0:
        return "a"  # Special case for zero

    base26 = ""
    while decimal_num > 0:
        digit = decimal_num % 26
        base26 = chr(digit + ord("a")) + base26  # Map digit to 'a'-'z'
        decimal_num //= 26

    return base26


def base26_to_decimal(base26_num):
    """
    Convert a 2-digit base-26 number to its decimal equivalent.

    Args:
        base26_num (str): A 2-character string in base-26 using 'a' as 0 and 'z' as 25.

    Returns:
        int: The decimal equivalent of the base-26 number.
    """
    # Ensure the input is exactly 2 characters
    if len(base26_num) != 2:
        raise ValueError("Input must be a 2-character base-26 number.")

    # Map each character to its base-26 value
    digit1 = ord(base26_num[0]) - ord("a")  # First character
    digit2 = ord(base26_num[1]) - ord("a")  # Second character

    # Compute the decimal value
    decimal_value = digit1 * 26**1 + digit2 * 26**0

    return decimal_value


def indx_to_tag(indx: int, fill: int = 1):
    """
    Convert an index to a base-26 tag.
    """
    return decimal_to_base26(indx).rjust(fill, "a")


class Controller:
    def __init__(self, database_path: str, reset: bool = False):
        self.db_manager = DatabaseManager(database_path, reset=reset)
        self.tag_to_id = {}
        self.chore_names = []
        log_msg("Controller initialized.")

    def is_chore_unique(self, name: str):
        return name not in self.chore_names

    def show_chores_as_table(self, width: int = 70):
        colors = {
            0: "#0066cc",
            1: "#3385a3",
            2: "#8cba5c",
            3: "#ffff00",
            4: "#ffff00",
            5: "#ffb920",
            6: "#ff8438",
            7: "#ff5050",
        }
        now = round(
            datetime.now()
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .timestamp()
        )

        chores = self.db_manager.list_chores()
        log_msg(f"Found {len(chores)}: {chores}")
        if not chores:
            return "No chores found."

        table = Table(title="Chores", expand=True, box=HEAVY_EDGE)
        table.add_column("row", justify="center", width=3, style="dim")
        table.add_column("name", width=25, overflow="ellipsis", no_wrap=True)
        table.add_column("last", justify="center", width=8)
        table.add_column("next", justify="center", width=8)
        table.add_column("+/-", justify="center", width=6)

        # chore_id: 0,  name: 1, created: 2, first_completion: 3, last_completion: 4,
        # mean_interval: 5, mean_absolute_deviation: 6, begin: 7, next: 8, num_completions: 9
        self.chore_names = []
        for idx, chore in enumerate(chores):
            self.chore_names.append(chore[1])
            tag = indx_to_tag(idx)
            self.tag_to_id[tag] = chore[0]
            if chore[7] and chore[6]:
                slots = [chore[7] + i * chore[6] for i in range(7)]
                slot_num = bisect.bisect_left(slots, now) if slots else 0
                row_color = colors.get(slot_num, "#ffffff")
            else:
                slot_num = 0
                row_color = "#ffffff"
            log_msg(
                f"next: {chore[8] = }, {fmt_dt(chore[8]) = }, {slot_num = }, {row_color = }"
            )
            table.add_row(
                str(tag),
                f"[{row_color}]{chore[1]}[/{row_color}]",
                f"[{row_color}]{fmt_dt(chore[4])}[/{row_color}]",
                f"[{row_color}]{fmt_dt(chore[8])}[/{row_color}]",
                f"[{row_color}]{fmt_td(3 * chore[6])}[/{row_color}]",
            )

        return table

    def show_chores_as_list(self, width: int = 70):
        colors = {
            0: "#0066cc",
            1: "#3385a3",
            2: "#8cba5c",
            3: "#ffff00",
            4: "#ffff00",
            5: "#ffb920",
            6: "#ff8438",
            7: "#ff5050",
        }
        now = round(
            datetime.now()
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .timestamp()
        )

        chores = self.db_manager.list_chores()
        log_msg(f"Found {len(chores)}: {chores}")
        if not chores:
            return "No chores found."

        table = Table(title="Chores", expand=True, box=HEAVY_EDGE)
        table.add_column("row", justify="center", width=3, style="dim")
        table.add_column("name", width=25, overflow="ellipsis", no_wrap=True)
        table.add_column("last", justify="center", width=8)
        table.add_column("next", justify="center", width=8)
        table.add_column("+/-", justify="center", width=6)

        # 5*2 + 8*2 + 6 = 10 + 16 + 6 = 32 => name width = width - 32
        name_width = width - 33
        results = [
            f"{'row':^3}  {'name':<{name_width}}  {'last':^8}  {'next':^8}  {'+/-':^6}",
        ]

        # chore_id: 0,  name: 1, created: 2, first_completion: 3, last_completion: 4,
        # mean_interval: 5, mad_minus: 6, mad_plus: 7, next: 8, num_completions: 9
        self.chore_names = []
        for idx, chore in enumerate(chores):
            self.chore_names.append(chore[1])
            tag = indx_to_tag(idx)
            self.tag_to_id[tag] = chore[0]
            if chore[8] and chore[6]:
                # 4, 3, 2 * mad_minus before next and 2, 3, 4 * mad_plus after next
                #             -4  -3  -2  -1   0   1   2   3   4
                # -------------|---|---|---.---X---.---|---|---|--------------------
                #          0     1   2     3       4     5   6    7
                slots_minus = [chore[8] - i * chore[6] for i in range(2, 5)]
                slots_plus = [chore[8] + i * chore[7] for i in range(2, 5)]
                slots = slots_minus + slots_plus
                slots.sort()
                slot_num = bisect.bisect_left(slots, now) if slots else 0
                row_color = colors.get(slot_num, "#ffffff")
            else:
                slot_num = 0
                row_color = "#ffffff"
            log_msg(
                f"next: {chore[8] = }, {fmt_dt(chore[8]) = }, {slot_num = }, {row_color = }"
            )
            name = truncate_string(chore[1], name_width)
            row = "  ".join(
                [
                    f"[dim]{tag:^3}[/dim]",
                    f"[{row_color}]{name:<{name_width}}[/{row_color}]",
                    f"[{row_color}]{fmt_dt(chore[4]):<8}[/{row_color}]",
                    f"[{row_color}]{fmt_dt(chore[8]):<8}[/{row_color}]",
                    f"[{row_color}]{fmt_td(2 * (chore[6] + chore[7])):^6}[/{row_color}]",
                ]
            )
            results.append(row)

        return results

    def show_chore(self, tag):
        chore_id = self.tag_to_id.get(tag)
        if not chore_id:
            return None, None, [f"There is no item corresponding to tag '{tag}'."]

        record = self.db_manager.show_chore(chore_id)
        fields = [
            "chore_id",
            "name",
            "created",
            "first_completion",
            "last_completion",
            "mean_interval",
            "mad_minus",
            "mad_plus",
            "next",
            "num_intervals",
        ]
        chore_name = record[1]
        results = [f"[bold]Details for tag [green]{tag}[/green][/bold]"]
        for field, value in zip(fields, record):
            log_msg(f"{field}: {value}")
            field_fmt = f"[bold blue]{field}[/bold blue]"
            if field in (
                "created",
                "first_completion",
                "last_completion",
                "next",
            ):
                value = fmt_dt(value, False)
            elif field in ("mean_interval", "mad_minus", "mad_plus"):
                value = fmt_td(value, False)
            results.append(
                f"  {field_fmt}: [not bold][yellow]{value}[/yellow][/not bold]"
            )

            # return chore_id, "\n".join(results)
            log_msg(f"returing chore_id: {chore_id}, chore_name: {chore_name}")
        return chore_id, chore_name, results

    def add_chore(self, name, created: int = round(datetime.now().timestamp())):
        self.db_manager.add_chore(name, created)
        log_msg(f"Chore '{name}' added successfully.")

    def complete_chore(
        self, chore_id, completion_datetime: int = round(datetime.now().timestamp())
    ):
        if type(completion_datetime) == datetime:
            completion_datetime = round(completion_datetime.timestamp())
        log_msg(f"Completing chore {chore_id} at {fmt_dt(completion_datetime)}.")
        self.db_manager.complete_chore(chore_id, completion_datetime)
        return f"Chore {chore_id} completed successfully."

    def remove_chore(self, tag):
        chore_id = self.tag_to_id.get(tag)
        if chore_id:
            self.db_manager.remove_chore(chore_id)
            return f"Chore {tag} removed successfully."
        return f"No chore found for tag '{tag}'."
