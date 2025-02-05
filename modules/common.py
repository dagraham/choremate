import inspect
from datetime import datetime
import textwrap
import shutil
from rich.markdown import Markdown
from rich.console import Console

ELLIPSIS_CHAR = "…"

COLORS = {
    0: "#87cefa",
    1: "#32cd32",
    2: "#adff2f",
    3: "#ffff00",
    4: "#ffff00",
    5: "#ffb920",
    6: "#ff8438",
    7: "#ff5050",
}


def truncate_string(s: str, max_length: int) -> str:
    log_msg(f"Truncating string '{s}' to {max_length} characters")
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
    caller_name = inspect.stack()[1].function
    # wrapped_lines = textwrap.wrap(
    #     fmt_msg,
    #     initial_indent="",
    #     subsequent_indent="  ",
    #     width=shutil.get_terminal_size()[0] - 3,
    # )
    lines = [
        f"- {datetime.now().strftime('%y-%m-%d %H:%M')} " + rf"({caller_name}):  ",
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
    log_msg(f"dt: {dt}")
    fmt = "%y-%m-%d" if short else "%Y-%m-%d %H:%M"
    if type(dt) is not int:
        return "?"
    if dt <= 0:
        return ""
    return datetime.fromtimestamp(dt).strftime(fmt)
