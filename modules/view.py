from .__version__ import version as VERSION
from datetime import datetime, timedelta

# from packaging.version import parse as parse_version
from prompt_toolkit.styles.named_colors import NAMED_COLORS
from rich.console import Console
from rich.segment import Segment
from rich.text import Text
from textual.app import App, ComposeResult
from textual.geometry import Size
from textual.reactive import reactive
from textual.screen import Screen
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widgets import Input
from textual.widgets import Static
from textual.widgets import Markdown
from textual.events import Key  # Import Key explicitly
from textual.containers import Vertical
from textual.widgets import Label

import string
import shutil
from textual.screen import ModalScreen

from dateutil.parser import parse, ParserError
from rich.rule import Rule
from typing import List

from textual.containers import Container
import asyncio
from pathlib import Path

from .common import (
    log_msg,
    display_messages,
    COLORS,
    fmt_dt,
    fmt_td,
    seconds_to_time,
    time_to_seconds,
    truncate_string,
)

HEADER_COLOR = NAMED_COLORS["LightSkyBlue"]
TITLE_COLOR = NAMED_COLORS["Cornsilk"]

HelpTitle = f"ChoreMate {VERSION}"
HelpText = """\
### Views 
- **List View**:  
  lists the summaries of each chore in the order of when the next completion is likely to be needed. 
- **Details View**:  
  shows the details of a particular chore.

### Key Bindings
- Always available:
    - **Q**: Quit ChoreMate   
    - **?**: Show this help screen
    - **S**: Save a screenshot of the current view to a file
- When list view is active:
    - **A**: Add a new chore.
    - **L**: Refresh the list of chores.
    - **a**-**z**: Show the details of the chore tagged with the corresponding letter.
- When details view is displaying a chore:
    - **C**: Complete the chore.
    - **D**: Delete the chore.
    - **E**: Edit the chore.
    - **a**-**z**: Select the interval corresponding to the tag and then press **u** to update or **r** to remove the interval.
    - **ESC**: Return to the list view.

### List View Details

When a chore is completed for the first time, ChoreMate records the user provided datetime of the completion as the *last* completion datetime. Thereafter, when a chore is completed, ChoreMate first prompts for the datetime the chore was actually completed and then prompts for the datetime that the chore actually needed to be completed. Normally these would be the same and, if this is the case, the user can simply press Enter to accept the completion datetime as the value for the needed datetime as well. 

But the completion and needed datetimes are not necessarily the same. If, for example, the chore is to fill the bird feeders when they are empty, then the completion datetime would be when the feeders are filled, but the needed datetime would be when the feeders became empty. Suppose I noticed that the feeders were empty yesterday at 3pm, but I didn't get around to filling them until 10am today. Then I would enter 10am today as the completion datetime in response to the first prompt and 3pm yesterday in response to the second prompt. Alternatively, if I'm going to be away for a while and won't be able to fill the bird feeders while I'm gone and they are currently half full, then I might fill them now in the hope that they will not be emptied before I return. In this case I would use the current moment as the *completion* datetime. But what about the *needed* datetime? Entering a needed datetime would require me to estimate when the feeders would have become empty. While I could do this, I could also just enter "none". Here's how the different responses would be processed by ChoreMate:

1. Both completion and needed datetimes are provided (but will be the same if the user accepts the default):

    a. the interval `needed_completion - last_completion` is added to the list of *completion intervals* for this chore.

    b. from this list of *completion intervals*, the mean (average) and two measures of dispersion about the mean are calculated and used to forecast the next completion datetime and to determine the "hotness" color of the chore in the list view.

    c. `last_completion` is updated to the value of the submitted *completion datetime* to set the beginning of the next interval. The mean interval is added to this datetime to get the forecast of the next completion datetime. 

2. A completion datetime and "none" are provided:

    a. skipped

    b. previous mean and dispersion measures are unchanged

    c. `last_completion` is updated to the value of the submitted *completion datetime* to set the beginning of the next interval. The mean interval is added to this datetime to get the forecast of the next completion datetime. 

Submitting "none" for the needed datetime can be used when the user can't be sure when the completion was or will be needed. 


When a chore is completed, ChoreMate records the *interval* between this and the previous completion and then updates the value of the last completion. The updated last completion is displayed in the **last** column of the list view. The mean or average of the recorded intervals for the chore is then added to the last completion to get a forecast of when the next completion will likely be needed. This forecast is displayed in the **next** column of the list view. The chores in list view are sorted by **next**.

How good is the **next** forecast? When three or more intervals have been recorded, ChoreMate separates the intervals into those that are *less* than the *mean interval* and those that are *more* than the *mean interval*. The average difference between an interval and the *mean interval* is then calculated for *each* of the two groups and labeled *mad_less* and *mad_more*, respectively. The column in the list view labeled **+/-** displays `2 × mad_less` when the current datetime is less than next and  `2 × mad_more` when it is more than next. The significance of these values is that at least 50% of the recorded intervals must lie within this range - a consquence of *Chebyshev's inequality*.

The chores are diplayed in the list view in one of seven possible colors based on the current datetime.  The diagram below shows the critical datetimes for a chore with `|`'s. The one labeled `N` in the middle corresponds to the value in the *next* column. The others, moving from the far left to the right represent offsets from *next*:  `next - 4 × mad_less`, `next - 3 × mad_less`, and so forth ending with `next + 4 × mad_more`. The numbers below the line represent the Color number used for the different intervals. 

``` 
   -4  -3  -2  -1   N   1   2   3   4 mad offsets
-x--|---|---|---.---|---.-X-|---|---|----> time
  1   2   3         4         5   6   7 colors
            |<---- 1/2 ---->|
        |<-------- 7/9 -------->| 
    |<------------ 7/8 ------------>|
```

If the current datetime is indicated by `x` on the time axis then the chore would be displayed in Color 1. As time and `x` progress to the right, the color changes from 1 to 2 to 3 and so forth. A cool blue is used for Color 1 with the temperature of the color ramping up to yellow for Color 4 and ultimately red for Color 7. 

Suppose at the moment corresponding to `X` that the chore is completed.  With this new interval, the mean interval, mad_less and mad_more will be updated and all the components of the new diagram will be moved a distance corresponding to the new "mean interval" to the right of `X` which will likely put new postion of `X` in the range for Color 1. 

As noted above, the range for Color 4, from -2 to +2 in the diagram, represents at least 1/2 of the recorded intervals so, based on the history of intervals, having Color 4 means that it will likely need to be completed soon. The 1/2 comes from the formula `1 - 2/k^2` where k is the number of mean absolute deviations from the mean which, in this case, means k = 2. For k = 3 and 4, the fractions of the intervals that fall within the range are 7/9 and 7/8, respectively.  
 """.splitlines()


class ConfirmScreen(ModalScreen):
    """A floating modal confirmation screen for goal deletion, using 'Y' or 'N' keys."""

    def __init__(self, goal_name, on_confirm):
        super().__init__()
        self.goal_name = goal_name
        self.on_confirm = on_confirm  # Callback function when confirmed

    def compose(self):
        """Create a floating confirmation dialog."""
        with Vertical(id="confirm-box"):
            yield Label(
                f"Are you sure you want to delete '{self.goal_name}'?",
                id="confirm-text",
            )
            yield Label(
                "Press 'Y' to confirm or 'N' to cancel.", id="confirm-instructions"
            )

    def on_key(self, event: Key):
        """Handle key events dynamically for uppercase 'Y' and 'N'."""
        if event.character == "Y":  # Detect uppercase Y
            self.dismiss()
            self.on_confirm()
        elif event.character == "N":  # Detect uppercase N
            self.dismiss()

    def on_mount(self):
        """Ensure the modal remains centered and floating."""
        self.styles.layer = "overlay"  # Ensures it floats above everything
        self.styles.align = ("center", "middle")  # Corrected alignment syntax


# class AddChoreScreen(ModalScreen):
#     """Screen for adding a new chore."""
#
#     def __init__(self, controller):
#         super().__init__()
#         self.controller = controller
#         self.chore_name = ""
#
#     def compose(self) -> ComposeResult:
#         """Create UI elements."""
#         yield Static("Enter the name of the new chore:", id="title")
#         yield Input(placeholder="Chore Name", id="chore_input")
#         yield Static("", id="validation_message")  # Feedback message
#         yield Static(
#             "[bold yellow]Enter[/bold yellow] submit, [bold yellow]ESC[/bold yellow] cancel",
#             id="instructions",
#         )  # Feedback message
#
#     def validate_chore(self, name: str) -> str:
#         """Check if the chore name is unique."""
#         if name and self.controller.is_chore_unique(name):
#             return f"[green]Valid chore name: {name}[/green]"
#         return "[red]Chore already exists or invalid name![/red]"
#
#     def on_input_changed(self, event: Input.Changed) -> None:
#         """Validate input and update the feedback message."""
#         validation_message = self.query_one("#validation_message", Static)
#         validation_message.update(self.validate_chore(event.value))
#         self.chore_name = event.value
#
#     def on_input_submitted(self, event: Input.Submitted) -> None:
#         """Handle Enter key submission."""
#         if event.input.id == "chore_input" and self.controller.is_chore_unique(
#             self.chore_name
#         ):
#             self.controller.add_chore(self.chore_name)
#             self.dismiss(self.chore_name)  # Confirm and close
#
#     def on_key(self, event):
#         """Handle key presses for cancellation."""
#         if event.key == "escape":
#             self.dismiss(None)  # Close without adding chore


# class AddChoreScreen(ModalScreen):
#     """Screen for adding a new chore."""
#
#     def __init__(self, controller):
#         super().__init__()
#         self.controller = controller
#         self.chore_name = ""
#
#     def compose(self) -> ComposeResult:
#         """Create UI elements."""
#         yield Static("Enter the name of the new chore:", id="title")
#         yield Input(placeholder="Chore Name", id="chore_input")
#         yield Static("", id="validation_message")  # Feedback message
#         yield Static("", id="footer")  # Placeholder for footer
#
#     def on_mount(self) -> None:
#         """Set up footer after mounting."""
#         footer = self.query_one("#footer", Static)
#         footer.update(
#             "[bold yellow]Enter[/bold yellow] submit, [bold yellow]ESC[/bold yellow] cancel"
#         )
#         # footer.styles.align = "center"
#
#     def validate_chore(self, name: str) -> str:
#         """Check if the chore name is unique."""
#         if name and self.controller.is_chore_unique(name):
#             return f"[green]Valid chore name: {name}[/green]"
#         return "[red]Chore already exists or invalid name![/red]"
#
#     def on_input_changed(self, event: Input.Changed) -> None:
#         """Validate input and update the feedback message."""
#         validation_message = self.query_one("#validation_message", Static)
#         validation_message.update(self.validate_chore(event.value))
#         self.chore_name = event.value
#
#     def on_input_submitted(self, event: Input.Submitted) -> None:
#         """Handle Enter key submission."""
#         if event.input.id == "chore_input" and self.controller.is_chore_unique(
#             self.chore_name
#         ):
#             self.controller.add_chore(self.chore_name)
#             self.dismiss(self.chore_name)  # Confirm and close
#
#     def on_key(self, event):
#         """Handle key presses for cancellation."""
#         if event.key == "escape":
#             self.dismiss(None)  # Close without adding chore


class AddChoreScreen(ModalScreen):
    """Screen for adding a new chore."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.chore_name = ""

    def compose(self) -> ComposeResult:
        """Create UI elements with a fixed footer."""
        with Container(id="content"):  # Content container
            yield Static("Enter the name of the new chore:", id="title")
            yield Input(placeholder="Chore Name", id="chore_input")
            yield Static("", id="validation_message")  # Feedback message

        # Footer explicitly placed at the bottom
        yield Static(
            "[bold yellow]Enter[/bold yellow] submit, [bold yellow]ESC[/bold yellow] cancel",
            id="footer",
        )

    def on_mount(self) -> None:
        """Ensure the footer is styled properly."""
        footer = self.query_one("#footer", Static)
        # footer.styles.align = "center"
        footer.styles.margin_top = 1  # Ensures space between content and footer

    def validate_chore(self, name: str) -> str:
        """Check if the chore name is unique."""
        if name and self.controller.is_chore_unique(name):
            return f"[green]Valid chore name: {name}[/green]"
        return "[red]Chore already exists or invalid name![/red]"

    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate input and update the feedback message."""
        validation_message = self.query_one("#validation_message", Static)
        validation_message.update(self.validate_chore(event.value))
        self.chore_name = event.value

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key submission."""
        if event.input.id == "chore_input" and self.controller.is_chore_unique(
            self.chore_name
        ):
            self.controller.add_chore(self.chore_name)
            self.dismiss(self.chore_name)  # Confirm and close

    def on_key(self, event):
        """Handle key presses for cancellation."""
        if event.key == "escape":
            self.dismiss(None)  # Close without adding chore


class IntervalInputScreen(ModalScreen):
    """Screen for entering an interval timedelta."""

    def __init__(
        self,
        controller,
        chore_id,
        chore_name,
        current_interval: int | None = None,
        prompt="Update interval:",
    ):
        super().__init__()
        self.controller = controller
        self.chore_id = chore_id
        self.chore_name = chore_name
        self.prompt = prompt  # Dynamic prompt message
        self.parsed_date = None  # Holds valid parsed datetime
        self.current_interval = current_interval
        self.was_escaped = False  # Tracks whether escape was pressed

    def compose(self) -> ComposeResult:
        """Create UI elements with a fixed footer."""
        with Container(id="content"):  # Content container
            yield Static(
                f'Interval for "{self.chore_name}".\n{self.prompt}',
                id="date_title",
            )
            # current_datetime = round(datetime.now().timestamp())
            if self.current_interval:
                yield Input(
                    value=f"{seconds_to_time(self.current_interval)}",
                    id="interval_input",
                )
            else:
                yield Input(
                    placeholder="0m",
                    id="interval_input",
                )
            yield Static("", id="validation_message")  # Feedback message

        # Footer explicitly placed at the bottom
        yield Static(
            "[bold yellow]Enter[/bold yellow] submit, [bold yellow]ESC[/bold yellow] cancel",
            id="footer",
        )

    def on_mount(self) -> None:
        """Ensure the footer is styled properly."""
        footer = self.query_one("#footer", Static)
        footer.styles.margin_top = 1  # Ensures space between content and footer

    def validate_interval(self, td_str: str) -> str:
        """Try to parse the entered date."""
        log_msg(f"{td_str = }")
        try:
            self.parsed_interval = time_to_seconds(td_str)  # Parse the date
            return f"[green]Recognized: {seconds_to_time(self.parsed_interval)}[/green]"
        except ValueError as e:
            self.parsed_interval = None
            return "[red]{e}[/red]"

    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate input and update the feedback message."""
        validation_message = self.query_one("#validation_message", Static)
        validation_message.update(self.validate_interval(event.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key submission."""
        log_msg(f"{event.input.id = }, {event.value = }, {self.was_escaped = }")
        if self.was_escaped:  # Prevent handling if escape was pressed
            return

        if event.input.id == "interval_input":
            input_value = event.value.strip()
            try:
                parsed_interval = time_to_seconds(input_value)
                self.dismiss(parsed_interval)  # Return the parsed datetime
            except ParserError:
                self.dismiss(None)  # Should not happen due to validation

    def on_key(self, event):
        """Handle key presses for cancellation."""
        if event.key == "escape":
            self.was_escaped = True  # Track that escape was pressed
            self.notify("Completion cancelled.", severity="warning")
            log_msg(f"{self.was_escaped = }")
            self.dismiss("_ESCAPED_")  # Return a special marker to detect escape


class DateInputScreen(ModalScreen):
    """Screen for entering a completion datetime."""

    def __init__(
        self,
        controller,
        chore_id,
        chore_name,
        second_datetime: bool = False,
        prompt="Enter completion date:",
    ):
        super().__init__()
        self.controller = controller
        self.chore_id = chore_id
        self.chore_name = chore_name
        self.prompt = prompt  # Dynamic prompt message
        self.parsed_date = None  # Holds valid parsed datetime
        self.second_datetime = second_datetime
        self.was_escaped = False  # Tracks whether escape was pressed

    def compose(self) -> ComposeResult:
        """Create UI elements with a fixed footer."""
        with Container(id="content"):  # Content container
            yield Static(
                f'Recording completion for "{self.chore_name}".\n{self.prompt}',
                id="date_title",
            )
            yield Input(placeholder="datetime expression", id="date_input")
            yield Static("", id="validation_message")  # Feedback message

        # Footer explicitly placed at the bottom
        yield Static(
            "[bold yellow]Enter[/bold yellow] submit, [bold yellow]ESC[/bold yellow] cancel",
            id="footer",
        )

    def on_mount(self) -> None:
        """Ensure the footer is styled properly."""
        footer = self.query_one("#footer", Static)
        footer.styles.margin_top = 1  # Ensures space between content and footer

    def validate_date(self, date_str: str) -> str:
        """Try to parse the entered date."""
        log_msg(f"{date_str = }")
        if self.second_datetime:
            if not date_str.strip():  # Allow empty input, return empty string
                self.parsed_date = ""
                return (
                    "[yellow]No needed date entered; default behavior applied.[/yellow]"
                )
            if date_str.strip().lower() == "none":  # Allow "none" input
                self.parsed_date = "none"
                return "[yellow]Omitting interval for this completion.[/yellow]"
        try:
            self.parsed_date = parse(date_str)  # Parse the date
            return f"[green]Recognized: {self.parsed_date.strftime('%Y-%m-%d %H:%M (%A)')}[/green]"
        except ParserError:
            self.parsed_date = None
            return "[red]Invalid format! Try again.[/red]"

    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate input and update the feedback message."""
        validation_message = self.query_one("#validation_message", Static)
        validation_message.update(self.validate_date(event.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key submission."""
        log_msg(f"{event.input.id = }, {event.value = }, {self.was_escaped = }")
        if self.was_escaped:  # Prevent handling if escape was pressed
            return

        if event.input.id == "date_input":
            input_value = event.value.strip()
            if input_value.lower() == "none":
                self.dismiss(None)  # Explicitly discard the interval
            elif input_value == "":
                self.dismiss("")  # Explicitly return empty string (use default)
            else:
                try:
                    parsed_date = parse(input_value)
                    self.dismiss(parsed_date)  # Return the parsed datetime
                except ParserError:
                    self.dismiss(None)  # Should not happen due to validation

    def on_key(self, event):
        """Handle key presses for cancellation."""
        if event.key == "escape":
            self.was_escaped = True  # Track that escape was pressed
            self.notify("Completion cancelled.", severity="warning")
            log_msg(f"{self.was_escaped = }")
            self.dismiss("_ESCAPED_")  # Return a special marker to detect escape


class DetailsScreen(Screen):
    """A temporary details screen."""

    def __init__(self, details: List[str], markdown: bool = False):
        super().__init__()
        self.markdown = markdown
        self.title = details[0]
        self.lines = details[1:]
        self.footer = [
            "",
            "[bold yellow]L[/bold yellow] list view, [bold yellow]C[/bold yellow] complete, [bold yellow]D[/bold yellow] delete, [bold yellow]E[/bold yellow] edit",
        ]

    def compose(self) -> ComposeResult:
        """Create UI elements with a fixed footer."""

        if self.markdown:
            yield Static(self.title, id="details_title", classes="title-class")
            yield Markdown("\n".join(self.lines), id="details_text")
            yield Static(
                "[bold yellow]ESC[/bold yellow] return to previous display", id="footer"
            )
        else:
            with Container(id="content"):  # Content container
                yield Static(self.title, id="details_title", classes="title-class")
                # yield markdown("\n".join(self.lines), expand=true, id="details_text")
                if self.markdown:
                    yield Markdown("\n".join(self.lines), id="details_text")
                else:
                    yield Static("\n".join(self.lines), id="details_text")

            # Footer explicitly placed at the bottom
            yield Static("\n".join(self.footer), id="footer")

    def on_mount(self) -> None:
        """Ensure the footer is styled properly."""
        footer = self.query_one("#footer", Static)
        # footer.styles.align = "center"
        footer.styles.margin_top = 1  # Ensures space between content and footer

    def on_key(self, event):
        if event.key == "escape":
            self.app.pop_screen()


class DetailsScreen(Screen):
    """A temporary details screen with scrollable content."""

    def __init__(self, details: List[str], markdown: bool = False):
        super().__init__()
        self.markdown = markdown
        self.title = details[0]
        self.lines = details[1:]
        self.footer = [
            "",
            "[bold yellow]L[/bold yellow] list view, [bold yellow]C[/bold yellow] complete, [bold yellow]D[/bold yellow] delete, [bold yellow]E[/bold yellow] edit",
        ]

    def compose(self) -> ComposeResult:
        """Create UI elements with a fixed footer."""
        yield Static(self.title, id="details_title", classes="title-class")

        if self.markdown:
            # If markdown, use the Markdown widget directly (not ScrollableList)
            yield Markdown("\n".join(self.lines), id="details_text")
        else:
            # ScrollableList handles long text as scrollable
            yield ScrollableList(self.lines, id="details_list")

        yield Static("\n".join(self.footer), id="footer")

    def on_mount(self) -> None:
        """Style the footer spacing."""
        footer = self.query_one("#footer", Static)
        footer.styles.margin_top = 1

    def on_key(self, event):
        if event.key == "escape":
            self.app.pop_screen()


class ScrollableList(ScrollView):
    """A scrollable list widget with a fixed title and search functionality."""

    def __init__(self, lines: list[str], **kwargs) -> None:
        super().__init__(**kwargs)

        # Extract the title and remaining lines
        # self.title = Text.from_markup(title) if title else Text("Untitled")
        width = shutil.get_terminal_size().columns - 3
        self.lines = [Text.from_markup(line) for line in lines]  # Exclude the title
        self.virtual_size = Size(
            width, len(self.lines)
        )  # Adjust virtual size for lines
        self.console = Console()
        self.search_term = None
        self.matches = []

    def render_line(self, y: int) -> Strip:
        """Render a single line of the list."""
        scroll_x, scroll_y = self.scroll_offset  # Current scroll position
        y += scroll_y  # Adjust for the current vertical scroll offset

        # If the line index is out of bounds, return an empty line
        if y < 0 or y >= len(self.lines):
            return Strip.blank(self.size.width)

        # Get the Rich Text object for the current line
        line_text = self.lines[y].copy()  # Create a copy to apply styles dynamically

        # Highlight the line if it matches the search term
        # if self.search_term and y in self.matches:
        #     line_text.stylize(f"bold {match_color}")  # apply highlighting

        # Render the Rich Text into segments
        segments = list(line_text.render(self.console))

        # Adjust segments for horizontal scrolling
        cropped_segments = Segment.adjust_line_length(
            segments, self.size.width, style=None
        )
        return Strip(
            cropped_segments,
            self.size.width,
        )


class FullScreenList(Screen):
    """Reusable full-screen list for Last, Next, and Find views."""

    def __init__(
        self,
        details: list[str],
        timestamp: str = "",
    ):
        super().__init__()
        if details:
            self.title = details[0]  # First line is the title
            self.lines = details[1:]  # Remaining lines are scrollable content
        else:
            self.title = "Untitled"
            self.lines = []
        # current_time = datetime.now().strftime("%a %H:%M")  # Format time
        footer_default = "[bold yellow]?[/bold yellow] Help"
        if timestamp:
            self.footer = f"[not bold]{timestamp}[/not bold] | {footer_default}"
        else:
            self.footer = footer_default

    def compose(self) -> ComposeResult:
        """Compose the layout."""
        width = shutil.get_terminal_size().columns - 3
        self.virtual_size = Size(width, len(self.lines))

        yield Static(self.title, id="scroll_title", expand=True)
        yield Static(Rule("", style="#fff8dc"), id="separator")  # Horizontal separator
        yield ScrollableList(self.lines, id="list")  # Scrollable content
        yield Static(self.footer, id="custom_footer")  # Footer with time

    def update_list(self, new_details: list[str]):
        """Update the list dynamically without needing a timer."""
        if new_details:
            self.title = new_details[0]
            self.lines = new_details[1:]

        # Update UI components
        self.query_one("#scroll_title", Static).update(self.title)
        self.query_one("#list", ScrollableList).update(self.lines)

    def update_footer(self):
        """Update the footer with the current time."""
        current_time = datetime.now().strftime("%a %H:%M")  # Format time
        footer = f"[bold]{current_time}[/bold] | {self.footer_content}"
        self.query_one("#custom_footer", Static).update(footer)  # ✅ Update UI


class TextualView(App):
    """A Textual-based interface for managing chores."""

    CSS_PATH = "view_textual.css"

    digit_buffer = reactive([])  # To store pressed characters for selecting chores
    afill = 1  # Number of characters needed to trigger a tag action

    BINDINGS = [
        ("Q", "quit", "Quit"),
        ("?", "show_help", "Help"),
        ("S", "take_screenshot", "Export SVG"),
        ("L", "show_list", "Show List"),
    ]

    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self.title = ""
        self.afill = 1
        self.view = "list"  # Initial view is the ScrollableList
        self.selected_chore = None
        self.selected_name = None
        self.selected_tag = None
        self.timestamp = None
        self.update_timer = None
        self.details = None
        self.full_screen_list = None  # Store the FullScreenList instance

    def on_mount(self):
        """Wait until the next full minute starts, then set an interval of 60s."""
        self.action_update_list()  # Initial update
        self.action_show_list()  # Start with list view
        self.update_timer = self.set_interval(1, self.maybe_update)

    def maybe_update(self):
        """Update the list if the current time is a full minute."""
        now = datetime.now()
        if now.second == 0:
            self.action_update_list(now)

    # def refresh_update_timer(self, seconds: float = 60.000):
    #     """Start the update timer to trigger action_show_list at one minute intervals."""
    #     log_msg("Starting update timer.")
    #     self.action_update_list()  # Initial update
    #     # self.action_show_list()  # Initial update
    #     if self.update_timer:
    #         self.update_timer.stop()
    #     self.update_timer = self.set_interval(
    #         seconds, self.refresh_update_timer, repeat=1
    #     )

    def action_update_list(self, now: datetime = datetime.now()):
        """Show the list of chores using FullScreenList."""
        log_msg(f"{self.view = }")
        chores = self.controller.show_chores_as_list(
            self.app.size.width - 1
        )  # Fetch chore data
        num_chores = len(chores) - 1
        self.afill = 1 if num_chores < 26 else 2 if num_chores < 676 else 3
        self.details = chores  # Title + chore data

        self.timestamp = now.strftime("%a %H:%M")  # Format time
        log_msg(f"{self.view = }, {self.timestamp = }")
        if self.view == "list":
            self.action_show_list()

    def action_show_list(self):
        # log_msg(f"show_list {timestamp = }")
        self.view = "list"
        # log_msg(f"{self.view = }")
        self.push_screen(FullScreenList(self.details, self.timestamp))

    def action_take_screenshot(self):
        """Save a timestamped screenshot and keep only the 10 most recent."""
        timestamp = datetime.now().strftime("%y%m%dT%H%M%S")
        screenshot_dir = Path(
            "screenshots"
        )  # You can change this to a dedicated folder if desired
        screenshot_path = screenshot_dir / f"{timestamp}.svg"

        # Save the screenshot
        self.save_screenshot(str(screenshot_path))
        self.notify(f"Screenshot saved to: {screenshot_path}", severity="info")

        # Clean up old screenshots, keep only the 10 most recent
        screenshots = sorted(
            screenshot_dir.glob("*.svg"), key=lambda f: f.stat().st_mtime, reverse=True
        )
        for old_file in screenshots[10:]:
            try:
                old_file.unlink()
            except Exception as e:
                self.notify(
                    f"Error removing old screenshot: {old_file.name}",
                    severity="warning",
                )

    def action_add_chore(self):
        """Prompt the user to enter a new chore name."""

        def on_close(chore_name):
            if chore_name:
                self.notify(
                    f"Chore '{chore_name}' added successfully!", severity="success"
                )
                self.action_update_list()
                self.action_show_list()  # Refresh the list view
            else:
                self.notify("Chore addition cancelled.", severity="warning")

        self.push_screen(AddChoreScreen(self.controller), callback=on_close)

    def action_show_chore(self, tag: str):
        """Show details for a selected chore."""
        chore_id, name, last_completion, details, interval_tag_to_idx = (
            self.controller.show_chore(tag)
        )
        self.selected_chore = chore_id
        self.selected_name = name
        self.selected_tag = tag
        self.last_completion = last_completion
        self.interval_tag_to_idx = interval_tag_to_idx
        self.view = "details"  # Track that we're in the details view
        log_msg(f"{self.view = }")
        self.push_screen(DetailsScreen(details))

    def action_refresh_chore(self):
        """Show details for a selected chore."""
        result = self.controller.show_chore(self.selected_chore)
        log_msg(f"{result = }")
        chore_id, name, last_completion, details, interval_tag_to_idx = result
        self.view = "details"  # Track that we're in the details view
        self.push_screen(DetailsScreen(details))

    def action_show_help(self):
        """Show the help screen."""
        self.view = "help"
        log_msg(f"{self.view = }")
        # width = self.app.size.width
        # title = f"{HelpTitle:^{width}}"
        title_fmt = f"[bold][{TITLE_COLOR}]{HelpTitle}[/{TITLE_COLOR}][/bold]"
        self.push_screen(DetailsScreen([title_fmt, *HelpText], True))

    def action_clear_info(self):
        try:
            footer = self.query_one("#custom_footer", Static)
            footer.update("[bold yellow]?[/bold yellow] Help")
        except LookupError:
            log_msg("Footer not found to update.")

    def action_complete_chore(self):
        """Prompt the user for completion and needed datetimes."""
        completion_fmt = needed_fmt = ""
        if not self.selected_chore:
            self.notify("No chore selected!", severity="warning")
            return

        def on_completion_close(completion_datetime):
            """Handle first datetime input."""
            log_msg(f"{self.selected_chore = }, {completion_datetime = }")
            if completion_datetime is None:
                return  # User canceled

            if isinstance(completion_datetime, datetime):
                completion_datetime = round(completion_datetime.timestamp())

            def on_needed_close(needed_datetime):
                """Handle second datetime input correctly."""
                log_msg(f"starting on_needed_close {needed_datetime = }")
                if needed_datetime == "_ESCAPED_":
                    log_msg("Escape detected! Cancelling completion.")
                    return  # Stop the process, do NOT record completion
                if needed_datetime is None:
                    needed_datetime = ""  # default behavior
                elif isinstance(needed_datetime, str):
                    if needed_datetime.strip().lower() == "none":
                        needed_datetime = "none"  # No interval recorded
                    elif needed_datetime.strip() == "first":
                        needed_datetime = "none"  # No interval recorded

                # Normalize input: distinguish "none" from empty string
                elif isinstance(needed_datetime, datetime):
                    needed_datetime = round(needed_datetime.timestamp())

                # ✅ Ensure record_completion is called with all required arguments
                self.controller.record_completion(
                    self.selected_chore, completion_datetime, needed_datetime
                )
                self.action_update_list()
                self.notify(
                    f'Recorded completion for "{self.selected_name}"',
                    severity="success",
                )

                # Refresh the view
                self.action_show_chore(self.selected_chore)

            # ✅ Make sure the second screen passes its result to on_needed_close
            if self.last_completion:
                # this is not the first completion so we can calculate the interval
                self.push_screen(
                    DateInputScreen(
                        self.controller,
                        self.selected_chore,
                        self.selected_name,
                        True,
                        "\n".join(
                            [
                                f"You completed the chore at {fmt_dt(completion_datetime, False)}.",
                                "Did the chore need to be completed at this same time?",
                                "1. If yes, enter nothing.",
                                "2. If no, either enter the needed datetime or",
                                '3. enter "none" to skip recording the prior interval.',
                            ]
                        ),
                    ),
                    callback=on_needed_close,  # ✅ Correctly passing the callback
                )
            else:
                # this is the first completion so we can't calculate the interval
                on_needed_close("first")

        # ✅ Ensure the first screen passes its result to on_completion_close
        self.push_screen(
            DateInputScreen(
                self.controller,
                self.selected_chore,
                self.selected_name,
                False,
                "Enter the datetime the chore was completed:",
            ),
            callback=on_completion_close,  # ✅ Correctly passing the callback
        )

    def action_delete_chore(self):
        """Delete the currently selected chore."""
        if not self.selected_chore:
            self.notify("No chore selected!", severity="warn bing")
            return
        log_msg(f"Deleting chore {self.selected_chore = }")
        ok, msg = self.controller.remove_chore(self.selected_chore)
        if ok:
            self.notify(f"Deleted chore '{self.selected_name}'", severity="success")
            self.action_update_list()
            self.action_show_list()
        else:
            self.notify(msg, severity="warning")

    def action_edit_chore(self):
        """Edit the currently selected chore."""
        self.notify("Editing chore...", severity="info")

    def on_key(self, event):
        """Handle key events based on the current view."""

        if self.view == "list":
            if (
                event.key in string.ascii_lowercase
            ):  # Only allow lowercase a-z for selecting chores
                self.digit_buffer.append(event.key)
                if len(self.digit_buffer) == self.afill:
                    base26_tag = "".join(self.digit_buffer)
                    self.digit_buffer.clear()
                    self.action_show_chore(base26_tag)
            elif event.key == "A":
                self.action_add_chore()
            elif event.key == "L":
                self.action_show_list()
            elif event.key == "Q":
                self.action_quit()
            elif event.key == "?":
                self.action_show_help()

        elif self.view == "details":
            if event.key in ["escape", "L"]:
                self.action_show_list()
            elif event.key == "C":
                self.action_complete_chore()
            elif event.key == "D":
                self.action_delete_chore()
            elif event.key == "E":
                self.action_edit_chore()
            # Step 1: Select a interval tag (lowercase letter)
            elif event.key and event.key in self.interval_tag_to_idx:
                self.selected_tag = self.interval_tag_to_idx[
                    event.key
                ]  # Store selected tag
                self.notify(
                    f"Selected interval {self.selected_tag}. Press 'u' to update or 'r' to remove.",
                    severity="info",
                )

            # Step 2: Perform action based on second keypress
            elif self.selected_tag and event.key in ["u", "r"]:
                if event.key == "u":
                    self.action_update_interval(self.selected_tag)
                elif event.key == "r":
                    self.action_remove_interval(self.selected_tag)
                self.selected_tag = None  # Reset after action
        elif self.view == "help":
            if event.key in ["escape", "L"]:
                self.action_show_list()

    def action_update_interval(self, interval_id):
        """Prompt the user for interval datetime."""
        interval_fmt = ""
        log_msg(f"{self.selected_chore = }, {interval_id = }")
        interval_timedelta = self.controller.get_interval(interval_id)
        log_msg(f"{interval_timedelta = }")
        if not interval_timedelta:
            self.notify("Could not obtain the current timestamp!", severity="warning")
            return

        def on_interval_close(interval_timedelta):
            """Handle datetime input."""
            log_msg(f"{self.selected_chore = }, {interval_timedelta = }")
            if interval_timedelta == "_ESCAPED_":
                log_msg("Escape detected! Cancelling completion.")
                return  # Stop the process, do NOT record completion
            if interval_timedelta is None:
                return  # User canceled

            # ✅ Ensure record_interval is called with all required arguments
            log_msg(f"{interval_id = }, {interval_timedelta = }")
            self.controller.update_interval(interval_id, interval_timedelta)

            self.notify(
                f'Updated interval for "{self.selected_name}"',
                severity="success",
            )

            # Refresh the view
            self.action_refresh_chore()

        # ✅ Ensure the first screen passes its result to on_interval_close
        self.push_screen(
            IntervalInputScreen(
                self.controller,
                self.selected_chore,
                self.selected_name,
                interval_timedelta,
                "Enter the new interval for the chore:",
            ),
            callback=on_interval_close,  # ✅ Correctly passing the callback
        )

    def action_remove_interval(self, interval_id: int | None = None):
        """Request confirmation before deleting the interval, using 'y' or 'n'."""
        if interval_id is None:
            self.notify("No interval selected.", severity="warning")
            return
        interval_timestamp = self.controller.get_interval(interval_id)
        if not interval_timestamp:
            self.notify("Could not obtain the current timestamp!", severity="warning")
            return

        def confirm_delete():
            log_msg(f"Deleting {interval_id = }, {interval_timestamp = }")
            self.controller.remove_interval(interval_id)
            self.notify(
                f"Deleted interval {seconds_to_time(interval_timestamp)} from {self.selected_name}",
                severity="warning",
            )
            self.action_refresh_chore()

        self.push_screen(ConfirmScreen(self.selected_name, confirm_delete))


if __name__ == "__main__":
    pass
