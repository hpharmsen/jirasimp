import json

from justdays import Day, Period

USER_MAPPING = {
    "geertjan": "geert-jan",
    "raymond": "ray",
    "jeroen": "jeroens",
    "robinveer": "robin",
}  # Map Simplicate name to oberon id


def get_report_mapping():
    with open('mapping.json') as mapping_file:
        reporting_units = json.load(mapping_file)
    return reporting_units


def month_in_weeks(year: int, month: int) -> Period:
    """Returns a period spanning a fixed number of weeks which roughly cover the month"""
    def snap_to_closest_monday(day: Day) -> Day:
        if day.day_of_week() in (1, 2):  # Tuesday or Wednesday
            day = day.last_monday()  # Move start of the period back to the last Monday
        elif day.day_of_week() >= 3:  # Thursday to Sunday
            day = day.plus_weeks(1).last_monday()  # Move start of the period forward to the next Monday
        return day

    first_day = snap_to_closest_monday(Day(year, month, 1))
    last_day = snap_to_closest_monday(Day(year, month, 1).plus_months(1))  # First day of next month

    return Period(first_day, last_day)


def format_item(item):
    if item.get('old_project_and_service'):
        item['project_and_service'] = f"{item['old_project_and_service']} -> {item['new_project_and_service']}"
    if item.get('old_hours'):
        item['hours'] = f"{item['old_hours']}h -> {item['new_hours']}"
    return f"{item['day']} {item['issue_key']:<8} {item['project_and_service']}, {item['employee']} ({item['hours']}h)"
