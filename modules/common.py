import inspect
from datetime import datetime
import textwrap
import shutil
from rich.markdown import Markdown
from rich.console import Console
import os
import re

ELLIPSIS_CHAR = "…"

# COLORS = {
#     1: "#6495ed",  # cornflowerblue
#     2: "#87cefa",  # lightskyblue
#     # 2: "#7fffd4",  # aquamarine
#     3: "#98fb98",  # palegreen
#     # 2: "#32cd32",  # limegreen
#     # 2: "#90ee90",  # lightgreen
#     # 3: "#adff2f",  # greenyellow
#     4: "#ffff00",
#     5: "#ffb920",
#     6: "#ff8438",
#     7: "#ff5050",
#     8: "#ff5050",
# }

COLORS = {
    0: "#4682b4",  # steelblue
    1: "#6495ed",  # cornflowerblue
    2: "#87cefa",  # lightskyblue
    3: "#98fb98",  # palegreen
    4: "#ffff00",  # yellow
    5: "#ffb920",  # orange
    6: "#ff8438",  # orange red
    7: "#ff5050",  # red
}


def truncate_string(s: str, max_length: int) -> str:
    # log_msg(f"Truncating string '{s}' to {max_length} characters")
    if len(s) > max_length:
        return f"{s[: max_length - 2]} {ELLIPSIS_CHAR}"
    else:
        return s


def log_msg(msg: str, file_path: str = "log_msg.md"):
    """
    Log a message and save it directly to a specified file.

    Args:
        msg (str): The message to log.
        file_path (str, optional): Path to the log file. Defaults to "log_msg.txt".
    """
    stack = inspect.stack()[1]
    caller_name = stack.function  # Function name
    caller_basename = os.path.basename(stack.filename)  # File name (without full path)
    caller_file = os.path.splitext(caller_basename)[0]

    lines = [
        f"- {datetime.now().strftime('%y-%m-%d %H:%M')} "
        + rf"({caller_file}/{caller_name}):  ",
    ]
    lines.extend(
        [
            f"\n{x}"
            for x in textwrap.wrap(
                msg.strip(),
                width=shutil.get_terminal_size()[0] - 6,
                initial_indent="   ",
                subsequent_indent="   ",
            )
        ]
    )
    lines.append("\n\n")

    # Save the message to the file
    with open(file_path, "a") as f:
        f.writelines(lines)


def display_messages(file_path: str = "log_msg.md"):
    """
    Display all logged messages from the specified file.

    Args:
        file_path (str, optional): Path to the log file. Defaults to "log_msg.txt".
    """
    try:
        # Read messages from the file
        with open(file_path, "r") as f:
            markdown_content = f.read()
        markdown = Markdown(markdown_content)
        console = Console()
        console.print(markdown)
    except FileNotFoundError:
        print(f"Error: Log file '{file_path}' not found.")


def time_to_seconds(time_str: str) -> int:
    """
    Converts a time string composed of integers followed by 'w', 'd', 'h', or 'm'
    into the total number of seconds.

    Args:
        time_str (str): The time string (e.g., '3h15s').

    Returns:
        int: The total number of seconds.

    Raises:
        ValueError: If the input string is not in the expected format.
    """
    # Define time multipliers for each unit
    multipliers = {
        "w": 7 * 24 * 60 * 60,  # Weeks to seconds
        "d": 24 * 60 * 60,  # Days to seconds
        "h": 60 * 60,  # Hours to seconds
        "m": 60,  # Minutes to seconds
    }

    # Match all integer-unit pairs (e.g., "3h", "15s")
    matches = re.findall(r"(\d+)([wdhm])", time_str)

    if not matches:
        raise ValueError(
            "Invalid time string format. Expected integers followed by 'w', 'd', 'h', or 'm'."
        )

    # Convert each match to seconds and sum them
    total_seconds = sum(int(value) * multipliers[unit] for value, unit in matches)
    return total_seconds


def seconds_to_time(seconds: int) -> str:
    """
    Converts an integer number of seconds into a human-readable time string
    using days, hours, minutes, and seconds.

    Args:
        seconds (int): The total number of seconds.

    Returns:
        str: A time string (e.g., '3h15s', '2d5h', etc.).
    """
    if seconds < 0:
        raise ValueError("Seconds must be non-negative.")

    # Define time units in seconds
    time_units = {
        "w": 7 * 24 * 60 * 60,  # Weeks to seconds
        "d": 24 * 60 * 60,  # Days to seconds
        "h": 60 * 60,  # Hours to seconds
        "m": 60,  # Minutes to seconds
    }

    # Compute the number of each unit
    result = []
    for unit, value in time_units.items():
        if seconds >= value:
            count = seconds // value
            seconds %= value
            result.append(f"{count}{unit}")

    return "".join(result) or "0m"  # Return '0s' for input 0


def fmt_td(seconds: int, short=True):
    """
    Format seconds as a human readable string
    if short report only biggest 2, else all
    >>> td = timedelta(weeks=1, days=2, hours=3, minutes=27).total_seconds()
    >>> fmt_td(td)
    '1w2d3h27m'
    """
    if type(seconds) is not int:
        return "?"
    if seconds <= 0:
        return ""
    try:
        total_seconds = abs(seconds)
        until = []
        days = hours = minutes = 0
        if total_seconds:
            seconds = total_seconds % 60
            minutes = total_seconds // 60
            if minutes >= 60:
                hours = minutes // 60
                minutes = minutes % 60
            if hours >= 24:
                days = hours // 24
                hours = hours % 24
        if days:
            until.append(f"{days}d")
        if hours:
            until.append(f"{hours}h")
        if minutes:
            until.append(f"{minutes}m")
        # if seconds:
        #     until.append(f"{seconds}s")
        if not until:
            until.append("0m")
        ret = "".join(until[:2]) if short else "".join(until)
        return ret
    except Exception as e:
        log_msg(f"{seconds}: {e}")
        return ""


def fmt_dt(dt: int, short=True):
    """
    Format seconds as a human readable string
    >>> fmt_dt(1610386800)
    '2021-01-11 00:00:00'
    """
    # log_msg(f"dt: {dt}")
    fmt = "%b %-d %-H:%M" if short else "%y-%m-%d %H:%M"
    if type(dt) is not int:
        return "?"
    if dt <= 0:
        return ""
    return datetime.fromtimestamp(dt).strftime(fmt)
