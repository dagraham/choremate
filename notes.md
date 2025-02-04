# Notes

## Database Design

I need a python file, model.py, for a new application that would use sqlite3 to manage the datastore with this setup:

- Table: Chores
  - chore_id: int
  - name: str (unique)
  - last_completion: int (seconds since epoch)
  - mean_interval: int (seconds computed)
  - mean_absolute_deviation: int (seconds computed)
  - begin: int (seconds since epoch computed)
  - next: int (seconds since epoch computed)
  - end: int (seconds since epoch computed)

- Table: Intervals
  - interval_id: int
  - chore_id: int
  - interval: int (seconds)

Database Methods:

- setup_database
- add_chore(name)
- remove_chore(name) and related intervals
- complete_chore(name, completion_datetime: datetime)
  - if there is a last_completion for the chore:
    - add a new interval equal to completion_datetime - last_completion
    - if there are at least 2 intervals
      - update the mean_interval
      - update next = last_completion + mean_interval
    - if there are at least 3 intervals
      - update mean_absolute_deviation
      - update begin = next - 3*mean_absolute_deviation
      - update end = next + 3*mean_absolute_deviation
  - set last_completion = completion_datetime
- list chores
  - chore_id, name, begin, next, end, num_completions
  - order by begin, next, name
- show_chore(name)
  - chore_id, name, last_completion, mean_interval, mean_absolute_deviation, begin, next, end, num_completions

## Entry Design

# Directory Structure

- root
  - modules
    - model.py (already done)
    - controller.py
    - view.py
  chores.py (provisionally done)

# Entry Point

chores.py: (provisional)

  ```python
  from modules.controller import Controller
  from modules.view import ClickView

  def main():
      controller = Controller("example.db")
      view = ClickView(controller)
      view.run()

  if __name__ == "__main__":
      main()
  ```

# Model

model.py: (already done)

  ```python
  import sqlite3
  from sqlite3 import Error

  class DatabaseManager:
      def __init__(self, database_path: str):
          self.database_path = database_path
          self.connection = None
          self.cursor = None
          self.setup_database()

      def setup_database(self):
          try:
              self.connection = sqlite3.connect(self.database_path)
              self.cursor = self.connection.cursor()
              self.cursor.execute(
                  """
                  CREATE TABLE IF NOT EXISTS Chores (
                      chore_id INTEGER PRIMARY KEY,
                      name TEXT UNIQUE,
                      last_completion INTEGER,
                      mean_interval INTEGER,
                      mean_absolute_deviation INTEGER,
                      begin INTEGER,
                      next INTEGER,
                      end INTEGER
                  )
                  """
              ...
  ```

# Controller

controller.py: (to be done)

  ```python
  from model import DatabaseManager
  from common import fmt_dt, fmt_td
  from rich.table import Table
  from rich.box import box
  from datetime import datetime 
  import bisect 

  class Controller:
      def __init__(self, database_path: str):
          # Initialize the database manager
          self.db_manager = DatabaseManager(database_path)
          self.tag_to_id = {}  # Maps tag numbers to event IDs
      ...
  ```

# methods to be implemented in Controller

- list_chores()
- show_chore()
- ...

Controller.list_chores():
  chores = self.db_manager.list_chores()

  ```python
  def list_chores(self):
    colors = {
      0: '#0066cc',
      1: '#3385a3',
      2: '#8cba5c',
      3: '#ffff00',
      4: '#ffff00',
      5: '#ffb920',
      6: '#ff8438',
      7: '#ff5050'
    }
    now = round(
      datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    )
    chores = self.db_manager.list_chores()
    if not chores:
      return "No chores found."
    table = Table(
        title=f"Chores",
        caption=f"{now.strftime('%Y-%m-%d')}",
        expand=True,
        box=box.HEAVY_EDGE,
    )
    table.add_column("row", justify="center", width=3, style="dim")
    table.add_column("name", width=10, overflow="ellipsis", no_wrap=True)
    table.add_column("last", justify="center", width=8)
    table.add_column("next", justify="center", width=8)
    table.add_column("+/-", justify="center", width=6)

    for idx, chore in enumerate(chores):
      self.tag_to_id[idx] = chore["chore_id"]
      slots = [chore['begin'] + i * chore['mean_absolute_deviation'] for i in range(8)]
      slot_num = bisect.bisect_left(slots, now)
      row_color = colors[slot_num]
      table.add_row(
          str(idx),
          f"[{row_color}]{chore['name']}[/{row_color}]",
          f"[{row_color}]{fmt_dt(chore['last'])}[/{row_color}]",
          f"[{row_color}]{fmt_dt(chore['next'])}[/{row_color}]",
          f"[{row_color}]{fmt_td(3*chore['mean_absolute_deviation'])}[/{row_color}]",
      )
    return table
  ```

Controller.show_chore():

```python
def show_chore(self, tag):
    """
    Process the base26 tag entered by the user.
    """
    chore_id = self.tag_to_id.get(tag, None)
    if not chore_id:
      return [f"There is no item corresponding to tag '{tag}'."]
    details = [f"Tag [{SELECTED_COLOR}]{tag}[/{SELECTED_COLOR}] details"]
    record = self.db_manager.get_chore(chore_id) 
    fields = ["chore_id", "name", "last_completion", "mean_interval", "mean_absolute_deviation", "begin", "next", "end"]
    content = "\n".join(
        f" [cyan]{field}:[/cyan] [white]{value if value is not None else '[dim]NULL[/dim]'}[/white]"
        for field, value in zip(fields, record)
    )
    return details + fields
```

list_chores() and show_chore(name) should return a list of dictionaries with the following keys:

- chore_id
- name
- last_completion
- mean_interval
- mean_absolute_deviation
- begin
- next
- end
- num_completions

## Controller and View Design Thoughts

- keybindings
  - viewing_mode = 'list'
    - 'Q' - quit
    - 'A' - add_chore
    - {tag} - show_chore corresponding to tag and set viewing_mode = 'details'

  - viewing_mode = 'details'
    - 'Q' - quit
    - 'R' - remove_chore (selected chore)
    - 'C' - complete_chore (selected chore)
    - 'U' - update_chore (selected chore)
    - 'L' - list_chores and set viewing_mode = 'list'

colors {
  0: '#0066cc',
  1: '#3385a3',
  2: '#8cba5c',
  3: '#ffff00',
  4: '#ffff00',
  5: '#ffb920',
  6: '#ff8438',
  7: '#ff5050'
}

- display_chores:
  - set viewing_mode = 'list'
  - set selected_chore = None
  - call model.list_chores
  - create a table with the results
    - each row with a tag colored dim that maps to the chore_id
    - with the rest of the row colored corresponding to the status of the chore

```python
now = round(
  datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
)
slots = [begin + i * mean_absolute_deviation for i in range(8)]
slot_num = bisect.bisect_left(slots, now)
row_color = colors[slot_num]
```

- show_chore:
  - activated by pressing the keyboard character corresponding to the tag of a chore
  - set viewing_mode = 'details'
  - set selected_chore = chore_id
  - call model.show_chore(selected_chore)
  - create a table to display the details of the chore
    - chore_id, name, last_completion, mean_interval, mean_absolute_deviation, begin, next, end, num_completions

- add_chore:
  - prompt user for name
  - insure name is unique
  - call model.add_chore(name)

- remove_chore:
  - activated by pressing the keyboard character corresponding to the tag of a chore
  - set viewing_mode = 'details'
  - set selected_chore = chore_id
  - call model.show_chore(selected_chore)
  - create a table to display the details of the chore
    - chore_id, name, last_completion, mean_interval, mean_absolute_deviation, begin, next, end, num_completions

- add_chore:
  - prompt user for name
  - insure name is unique
  - call model.add_chore(name)

- remove_chore:
  - prommpt user for name
  - call model.remove_chore(name)

- complete_chore:
  
Now I need a command line interface, cli.py, that provides a python click interface to the database methods to manage the chores.

CLI Class Methods:

- init: osetup_database
- add_chore: prompt for name, insure unique and call add_chore
