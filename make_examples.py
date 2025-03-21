import random
from datetime import datetime, timedelta
from rich import print
from modules.model import DatabaseManager
from modules.common import log_msg
from time import sleep
import lorem
from typing import List


def phrase():
    # for the summary
    # drop the ending period
    s = lorem.sentence()[:-1]
    num = random.choice([2, 3])
    words = s.split(" ")[:num]
    return " ".join(words).rstrip()


def get_name(names: List[str]):
    """Generate a random phrase not belonging to the provided list."""
    name = phrase()
    count = 0
    while name in names and count < 16:
        count += 1
        name = phrase()
    return name


def get_delay():
    return timedelta(hours=random.randint(-24, 20))


def generate_intervals(name, mean_interval, mean_absolute_deviation, num_items):
    """Generate a list of intervals satisfying the given constraints."""

    # Generate random intervals with given mean and MAD
    now = datetime.now()

    low = mean_interval.total_seconds() - (
        1.5 * mean_absolute_deviation.total_seconds()
    )
    high = mean_interval.total_seconds() + (
        1.5 * mean_absolute_deviation.total_seconds()
    )
    mode = mean_interval.total_seconds()  # Peak at the mean

    intervals = [
        timedelta(seconds=round(random.triangular(low, high, mode)))
        for _ in range(num_items)
    ]
    last_time = now - intervals[-1]
    starting_time = now - sum(intervals, timedelta()) - get_delay()
    return (name, starting_time, last_time, intervals[:-1])


def process_items(items):
    """Process a list of items to generate interval data."""
    results = []
    names = []
    count = 0
    for item in items:
        count += 1
        name = get_name(names)
        names.append(name)
        mean_interval, mean_absolute_deviation, num_items = item
        result = generate_intervals(
            name, mean_interval, mean_absolute_deviation, num_items
        )
        results.append(result)

    return results


items = []
for i in range(12):
    days = random.randint(1, 14)
    hours = days + random.randint(0, 6)
    count = random.randint(1, 10)
    items.append((timedelta(days=days, hours=hours), timedelta(hours=hours), count))

results = process_items(items)
# sorted_results = sorted(results, key=lambda x: x[1])

# # Print results
# for name, start_time, last_time, intervals in results:
#     print(f"{name}: Start Time = {start_time}; Last Time = {last_time}")
#     print(f"Intervals: {[str(interval) for interval in intervals]}")
#     print()
# print("Sorted Results:")
# for name, start_time, last_time, intervals in sorted_results:
#     print(
#         f"{name}: Start Time = {start_time.strftime('%y-%m-%d %H:%M')} Last Time = {last_time.strftime('%y-%m-%d %H:%M')}"
#     )
#
# Save the results to the database
dbm = DatabaseManager("example.db", reset=True)
for name, start_time, last_time, intervals in results:
    log_msg(f"Adding chore {name}, starting at {start_time}")
    chore_id = dbm.add_chore(name, start_time)
    log_msg(
        f"Completing chore {name} with id {chore_id} for the first time at {start_time}."
    )
    dbm.record_completion(chore_id, start_time, "")
    this_time = start_time
    for interval in intervals:
        this_time += interval
        log_msg(f"Completing chore {name} at {this_time}.")
        dbm.record_completion(chore_id, this_time, "")
    log_msg(f"Added {len(intervals) + 1} intervals for {name}.")
    # sleep(0.5)
