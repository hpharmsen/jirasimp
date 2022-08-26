import datetime

from gspread_formatting import set_column_width

from googlesheet import fill_range, format_range, create_worksheet, get_spreadsheet

from .utilities import month_in_weeks


def report(report_name, year, month, labels, issues: dict):

    period = month_in_weeks(year, month)

    start_week = period.fromday.week_number()
    end_week = period.untilday.prev().week_number()
    maand_naam = ['Januari', 'Februari', 'Maart', 'April', 'Mei', 'Juni', 'Juli', 'Augustus', 'September', 'Oktober', 'November', 'December'][month - 1]

    spreadsheet_name = f'Travelbase maandrapporten - {report_name}'
    print(spreadsheet_name)
    worksheet_name = f'{maand_naam} {year} '
    worksheet = create_worksheet(spreadsheet_name, worksheet_name, rows=len(issues) + 6, cols=8)

    # Header
    fill_range(worksheet, 2, 1, [f'{", ".join(labels)} - {maand_naam} {year}'])
    format_range(worksheet, "A2:A2", font_size=18, bold=True)

    # Subtitle
    fill_range(worksheet, 3, 1, [f"Werkzaamheden van week {start_week} t/m {end_week} ({period.fromday.strftime('%d-%m')} t/m {period.untilday.prev().strftime('%d-%m')})"])

    # Column headers
    first_data_row = 5
    fill_range(worksheet, first_data_row, 1, ['Jira issue', 'Type', 'Summary', 'Total time spent', 'Time spent', 'T-shirt size', 'Status', 'Labels'])
    format_range(worksheet, f"A{first_data_row}:H{first_data_row}", bold=True)

    # Issue keys
    for index, jira_key in enumerate(issues.keys()):
        row = index + first_data_row + 1
        worksheet.update_cell(row, 1, f'=HYPERLINK("https://teamoberon.atlassian.net/browse/{jira_key}","{jira_key}")')

    # Data
    data = [[issue['issuetype'], issue['summary'], issue['timespent_total'], issue['timespent'], issue['tshirt_size'], issue['status'], ', '.join(issue['labels'])] for issue in issues.values()]
    fill_range(worksheet, first_data_row+1, 2, data)
    set_column_width(worksheet, 'C', 500)
    set_column_width(worksheet, 'D', 120)
    format_range(worksheet, f"D{first_data_row}:E200", align="RIGHT")
    format_range(worksheet, f"F{first_data_row}:G200", align="CENTER")

    # Total
    if data:
        total_row = first_data_row + len(issues) + 1
        worksheet.update(f"E{total_row}", f'=SUM(E{first_data_row+1}:E{total_row-1})', value_input_option='USER_ENTERED')
        format_range(worksheet, f"E{total_row}", bold=True)

    # Timestamp
    worksheet.update("H1", datetime.datetime.now().strftime("%d-%m-%y %H:%M"))
    format_range(worksheet, f"H1:H1", font_size=8, font_color=(127, 127, 127), align="RIGHT")

    # Inhoudsopgave
    spreadsheet = get_spreadsheet(spreadsheet_name)
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/%s" % spreadsheet.id
    worksheet_url = f"{spreadsheet_url}/edit#gid={worksheet.id}"
    contents_sheet = spreadsheet.worksheet('inhoud')
    contents_sheet.update('A2', f'Travelbase werkzaamheden voor label {report_name}')
    format_range(contents_sheet, "A2", font_size=18, bold=True)
    contents_sheet.update_cell(month+3, year-2021, f'=HYPERLINK("{worksheet_url}","{worksheet_name}")')
