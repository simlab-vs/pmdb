"""Pay of hourly staff from their approved timesheets.

- Worked time is the shift length minus the break, paid at the hourly rate
  of the assignment in force on the shift's date.
- Night premium: minutes worked between ``night_from`` and ``night_to``.
- Sunday and holiday premium: every minute of a shift that starts on a
  Sunday or a public holiday (the holiday rate replaces the Sunday rate).
- Overtime premium: minutes worked in an ISO week beyond the contract's
  weekly hours (of the row in force at the week's first shift).  Weeks are
  cut at the period's boundaries, so a week spanning two months is checked
  in each month separately.
- Paid absences (sickness, vacation) on weekdays are paid at the contract's
  daily hours (weekly hours / 5).

Premiums are a percentage of the hourly rate, in basis points.
"""

import logging
from collections import Counter, defaultdict

from .employment import segment_at
from .models import HOURLY, HourlyPay
from .money import round_half_up
from .periods import is_weekday, iso_week, weekday
from .settings import minutes_of

log = logging.getLogger(__name__)

STATS = Counter()
MINUTES_PER_DAY = 24 * 60


def shift_window(shift):
    """(start, end) in minutes from the shift date's midnight; end > start."""
    start, end = minutes_of(shift.start), minutes_of(shift.end)
    if end <= start:
        end += MINUTES_PER_DAY
    return start, end


def worked_minutes(shift):
    start, end = shift_window(shift)
    return max(0, end - start - shift.break_minutes)


def overlap(a_start, a_end, b_start, b_end):
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def night_minutes(shift, night_from, night_to):
    """Minutes of the shift inside the night window (breaks are not deducted)."""
    start, end = shift_window(shift)
    total = 0
    for offset in (-MINUTES_PER_DAY, 0, MINUTES_PER_DAY):
        total += overlap(start, end, night_from + offset, night_to + MINUTES_PER_DAY + offset)
    return total


def premium_bp(shift, rules):
    if shift.date in rules.holidays:
        return rules.holiday_bp
    if weekday(shift.date) == 6:
        return rules.sunday_bp
    return 0


def contract_week_minutes(segment):
    return round(segment.weekly_hours * 60)


def hourly_pay(employment, days, shifts, paid_absences, rules):
    """HourlyPay for the person's shifts on employed days and their paid absences."""
    employed = set(days)
    pay = 0          # in cents × minutes
    premiums = 0     # in cents × minutes × basis points
    worked = night = sunday = 0
    weeks = defaultdict(list)
    for shift in sorted(shifts, key=lambda s: (s.date, s.start)):
        if shift.date not in employed:
            STATS["outside employment"] += 1
            continue
        segment = segment_at(employment.segments, shift.date)
        if segment.pay_type != HOURLY:
            STATS["on salaried row"] += 1
            continue
        minutes = worked_minutes(shift)
        rate = segment.hourly_rate
        pay += minutes * rate * 5
        nights = night_minutes(shift, rules.night_from, rules.night_to)
        premiums += nights * rate * rules.night_bp
        bp = premium_bp(shift, rules)
        if bp:
            premiums += minutes * rate * bp
            sunday += minutes
        worked += minutes
        night += nights
        weeks[iso_week(shift.date)].append((shift, segment, minutes))
    overtime = 0
    for entries in weeks.values():
        _, segment, _ = entries[0]
        extra = sum(minutes for _, _, minutes in entries) - round(segment.weekly_hours * 60)
        if extra > 0:
            premiums += extra * segment.hourly_rate * rules.overtime_bp
            overtime += extra
    absence_days = 0
    for day in paid_absences:
        if not is_weekday(day):
            continue
        segment = segment_at(employment.segments, day)
        if segment.pay_type != HOURLY:
            continue
        pay += contract_week_minutes(segment) * segment.hourly_rate
        absence_days += 1
    return HourlyPay(
        pay=round_half_up(pay, 300),
        premiums=round_half_up(premiums, 60 * 10_000),
        worked_minutes=worked,
        night_minutes=night,
        sunday_minutes=sunday,
        overtime_minutes=overtime,
        paid_absence_days=absence_days,
    )
