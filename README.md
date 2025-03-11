
<div style="display: flex; align-items: center;">
  <div style="flex: 1;">
<H1>choremate</H1>
<p><b>choremate</b> is a simple application for tracking the sequence of occasions on which a task is completed and predicting when the next completion will likely be needed.
  </div>
  <div style="flex: 0; padding-left: 10px; padding-right: 6px;">
    <img src="tracker.png" alt="" style="max-width: 140px;">
  </div>
</div>

### Usage

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

How good is the **next** forecast? When three or more intervals have been recorded, ChoreMate separates the intervals into those that are *less* than the *mean interval* and those that are *more* than the *mean interval*. The average difference between an interval and the *mean interval* is then calculated for *each* of the two groups and labeled *mad_less* and *mad_more*, respectively. The column in the list view labeled **+/-** displays the range from `next - 2 × mad_less` to `next + 2 × mad_more`. The significance of this value is that at least 50% of the recorded intervals must lie within this range - a consquence of *Chebyshev's inequality*.

The chores are diplayed in the list view in one of seven possible colors based on the current datetime.  The diagram below shows the critical datetimes for a chore with `|`'s. The one labeled `N` in the middle corresponds to the value in the *next* column. The others, moving from the far left to the right represent offsets from *next*:  `next - 4 × mad_less`, `next - 3 × mad_less`, and so forth ending with `next + 4 × mad_more`. The numbers below the line represent the Color number used for the different intervals.
