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

# from textual.widgets import Label
import string
import shutil
from textual.screen import ModalScreen

# from textual.widgets import Button
from dateutil.parser import parse, ParserError
from rich.rule import Rule
from typing import List

# from textual.app import ComposeResult
from textual.containers import Container

# from textual.widgets import Static, Input
from .common import log_msg, display_messages, COLORS

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
    - **ESC**: Return to the list view.

### List View Details

When a chore is completed, ChoreMate records the *interval* between this and the previous completion and then updates the value of the last completion. The updated last completion is displayed in the **last** column of the list view. The mean or average of the recorded intervals for the chore is then added to the last completion to get a forecast of when the next completion will likely be needed. This forecast is displayed in the **next** column of the list view. The chores in list view are sorted by **next**.

How good is the **next** forecast? When three or more intervals have been recorded, ChoreMate separates the intervals into those that are *less* than the *mean interval* and those that are *more* than the *mean interval*. The average difference between an interval and the *mean interval* is then calculated for *each* of the two groups and labeled *mad_less* and *mad_more*, respectively. The column in the list view labeled **+/-** displays the range from `next - 2 × mad_less` to `next + 2 × mad_more`. The significance of this value is that at least 50% of the recorded intervals must lie within this range - a consquence of *Chebyshev's inequality*.

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


class AddChoreScreen(ModalScreen):
    """Screen for adding a new chore."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.chore_name = ""

    def compose(self) -> ComposeResult:
        """Create UI elements."""
        yield Static("Enter the name of the new chore:", id="title")
        yield Input(placeholder="Chore Name", id="chore_input")
        yield Static("", id="validation_message")  # Feedback message
        yield Static(
            "[bold yellow]Enter[/bold yellow] submit, [bold yellow]ESC[/bold yellow] cancel",
            id="instructions",
        )  # Feedback message

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


class AddChoreScreen(ModalScreen):
    """Screen for adding a new chore."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.chore_name = ""

    def compose(self) -> ComposeResult:
        """Create UI elements."""
        yield Static("Enter the name of the new chore:", id="title")
        yield Input(placeholder="Chore Name", id="chore_input")
        yield Static("", id="validation_message")  # Feedback message
        yield Static("", id="footer")  # Placeholder for footer

    def on_mount(self) -> None:
        """Set up footer after mounting."""
        footer = self.query_one("#footer", Static)
        footer.update(
            "[bold yellow]Enter[/bold yellow] submit, [bold yellow]ESC[/bold yellow] cancel"
        )
        # footer.styles.align = "center"

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


class DateInputScreen(ModalScreen):
    """Screen for entering a completion datetime."""

    def __init__(self, controller, chore_name):
        super().__init__()
        self.controller = controller
        self.chore_name = chore_name
        self.parsed_date = None  # Holds valid parsed datetime

    def compose(self) -> ComposeResult:
        """Create UI elements."""
        yield Static(f"Enter completion date for: {self.chore_name}", id="title")
        yield Input(placeholder="YYYY-MM-DD HH:MM", id="date_input")
        yield Static("", id="validation_message")  # Feedback message
        yield Static(
            "[bold yellow]Enter[/bold yellow] submit, [bold yellow]ESC[/bold yellow] cancel",
            id="instructions",
        )  # Feedback message

    def compose(self) -> ComposeResult:
        """Create UI elements with a fixed footer."""
        with Container(id="content"):  # Content container
            yield Static(f"Enter completion date for: {self.chore_name}", id="title")
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
        # footer.styles.align = "center"
        footer.styles.margin_top = 1  # Ensures space between content and footer

    def validate_date(self, date_str: str) -> str:
        """Try to parse the entered date."""
        try:
            self.parsed_date = parse(date_str)  # Parse the date
            return f"[green]Recognized: {self.parsed_date.strftime('%Y-%m-%d %H:%M')}[/green]"
        except ParserError:
            self.parsed_date = None
            return "[red]Invalid format! Try again.[/red]"

    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate input and update the feedback message."""
        validation_message = self.query_one("#validation_message", Static)
        validation_message.update(self.validate_date(event.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key submission."""
        if event.input.id == "date_input" and self.parsed_date:
            self.dismiss(self.parsed_date)  # Return parsed datetime

    def on_key(self, event):
        """Handle key presses for cancellation."""
        if event.key == "escape":
            self.dismiss(None)  # Close without completing


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
        footer_content: str = "[bold yellow]?[/bold yellow] Help",
    ):
        super().__init__()
        if details:
            self.title = details[0]  # First line is the title
            self.lines = details[1:]  # Remaining lines are scrollable content
        else:
            self.title = "Untitled"
            self.lines = []
        self.footer_content = footer_content
        log_msg(f"FullScreenList: {details[:3] = }")

    def compose(self) -> ComposeResult:
        """Compose the layout."""
        width = shutil.get_terminal_size().columns - 3
        self.virtual_size = Size(width, len(self.lines))
        log_msg(
            f"FullScreenList: {self.title = }, {len(self.title) = },  {self.lines[:3] = }"
        )
        yield Static(self.title, id="scroll_title", expand=True)
        yield Static(
            Rule("", style="#fff8dc"), id="separator"
        )  # Add a horizontal line separator
        yield ScrollableList(self.lines, id="list")  # Using "list" as the ID
        yield Static(self.footer_content, id="custom_footer")


class TextualView(App):
    """A Textual-based interface for managing chores."""

    CSS_PATH = "view_textual.css"

    digit_buffer = reactive([])  # To store pressed characters for selecting chores
    afill = 1  # Number of characters needed to trigger a tag action

    BINDINGS = [
        ("Q", "quit", "Quit"),
        ("?", "show_help", "Help"),
        ("S", "take_screenshot", "Screenshot"),
        ("L", "show_list", "Show List"),
    ]

    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self.title = ""
        self.view = "list"  # Initial view is the ScrollableList
        self.selected_chore = None
        self.selected_name = None
        self.selected_tag = None

    def on_mount(self) -> None:
        """Ensure the list of chores appears on startup."""
        self.action_show_list()

    def action_take_screenshot(self):
        """Save a screenshot of the current app state."""
        screenshot_path = f"{self.view}_screenshot.svg"
        self.save_screenshot(screenshot_path)
        log_msg(f"Screenshot saved to: {screenshot_path}")

    # def action_add_chore(self):
    #     """Add a new chore."""
    #     self.notify("Adding a new chore...", severity="info")

    def action_add_chore(self):
        """Prompt the user to enter a new chore name."""

        def on_close(chore_name):
            if chore_name:
                self.notify(
                    f"Chore '{chore_name}' added successfully!", severity="success"
                )
            else:
                self.notify("Chore addition cancelled.", severity="warning")

        self.push_screen(AddChoreScreen(self.controller), callback=on_close)

    def action_show_list(self):
        """Show the list of chores using FullScreenList."""
        chores = self.controller.show_chores_as_list(
            self.app.size.width
        )  # Fetch chore data
        details = chores  # Title + chore data
        self.view = "list"  # Track that we're in the list view
        self.push_screen(FullScreenList(details))

    def action_show_chore(self, tag: str):
        """Show details for a selected chore."""
        chore_id, name, details = self.controller.show_chore(tag)
        self.selected_chore = chore_id
        self.selected_name = name
        self.selected_tag = tag
        self.view = "details"  # Track that we're in the details view
        self.push_screen(DetailsScreen(details))

    def action_show_help(self):
        """Show the help screen."""
        self.view = "help"
        width = self.app.size.width
        title = f"{HelpTitle:^{width}}"
        title_fmt = f"[bold][{TITLE_COLOR}]{title}[/{TITLE_COLOR}][/bold]"
        self.push_screen(DetailsScreen([title_fmt, *HelpText], True))

    def action_clear_info(self):
        try:
            footer = self.query_one("#custom_footer", Static)
            footer.update("[bold yellow]?[/bold yellow] Help")
        except LookupError:
            log_msg("Footer not found to update.")

    def action_complete_chore(self):
        """Prompt the user for a completion datetime."""
        if not self.selected_chore:
            self.notify("No chore selected!", severity="warning")
            return

        def on_close(parsed_date):
            """Handle the result of the date input screen."""
            if parsed_date:
                log_msg(
                    f"{self.selected_chore = }, {parsed_date = }, {type(parsed_date) = }"
                )
                self.controller.complete_chore(self.selected_chore, parsed_date)
                self.notify(
                    f"{self.selected_name} completed at {parsed_date.strftime('%Y-%m-%d %H:%M')}"
                )
                # self.action_show_list()  # Refresh the list view
                self.action_show_chore(self.selected_tag)  # Refresh the list view

        self.push_screen(
            DateInputScreen(self.controller, self.selected_chore), callback=on_close
        )

    def action_delete_chore(self):
        """Delete the currently selected chore."""
        self.notify("Deleting chore...", severity="warning")

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
        elif self.view == "help":
            if event.key in ["escape", "L"]:
                self.action_show_list()


if __name__ == "__main__":
    pass
