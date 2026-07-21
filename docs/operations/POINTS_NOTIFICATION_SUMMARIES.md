# Points notification summaries

Point events are always stored immediately and continue to feed the normal points history,
totals, reports and charts. The school-scoped points notification policy changes push timing
only.

- `summaries` can independently enable daily, weekly and monthly summaries.
- `immediate` keeps the established short-window FHH bundle.
- `off` creates no points push rows.

All period boundaries use the saved IANA school timezone. Daily periods run from local
midnight through the configured send time. Monthly periods run from the first calendar day
through the configured time on the final calendar date, including weekends and closed days;
contact-hour exceptions and holiday data are not consulted.

The weekly period starts on `week_starts_on` and ends on `week_ends_on`. Its end is capped at
the first local midnight after the configured end day. Events on days outside that interval
remain fully visible and reportable but are intentionally excluded from the school-week
summary. `weekly_summary_day` and its time are saved separately and normally match the week
end; if dispatch is configured after the end day, the total still stops at the school-week
boundary.

One immutable aggregate exists per school, child, summary type and period key. Delivery to
each active FHH link reuses the notification outbox and signed bridge. A later point event is
retained and diagnosed against any already-generated matching daily, weekly or monthly key;
it never causes a correction or second summary.
