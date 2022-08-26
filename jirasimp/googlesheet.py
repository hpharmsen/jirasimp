import os
import sys
import time
from pathlib import Path

import gspread  # https://github.com/burnash/gspread
from google.auth.transport import requests
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials
from gspread import Worksheet


def get_spreadsheet(sheet_name):
    # oAuth authentication. Json file created using explanation at:
    # http://gspread.readthedocs.org/en/latest/oauth2.html
    # Updated call since v2.0: See https://github.com/google/oauth2client/releases/tag/v2.0.0

    # Sheet should be shared with: 859748496829-pm6qtlliimaqt35o8nqcti0h77doigla@developer.gserviceaccount.com
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    # Latest version from:
    # https://stackoverflow.com/questions/51618127/credentials-object-has-no-attribute-access-token-when-using-google-auth-wi
    key_file = Path(__file__).resolve().parent / "oauth_key.json"
    credentials = Credentials.from_service_account_file(key_file)
    scoped_credentials = credentials.with_scopes(scopes)
    gc = gspread.Client(auth=scoped_credentials)
    gc.session = AuthorizedSession(scoped_credentials)

    newly_created = False
    try:
        spreadsheet = gc.open(sheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        spreadsheet = gc.create(sheet_name)
        newly_created = True
    except gspread.exceptions.APIError:
        print(
            "googlesheet.py",
            "get_spreasheeet()",
            "Could not open " + sheet_name,
        )
        sys.exit(1)

    if newly_created:
        spreadsheet.share('859748496829-pm6qtlliimaqt35o8nqcti0h77doigla@developer.gserviceaccount.com', perm_type="user",
                    role="writer")
        spreadsheet.share('hph@oberon.nl', perm_type="user", role="writer")
        for user in os.environ['SHARE_WITH'].split(','):
            spreadsheet.share(user.strip(), perm_type='user', role='writer')

    # Make sure there's a tab named 'inhoud
    try:
        sheet1 = spreadsheet.worksheet('inhoud')
    except gspread.exceptions.WorksheetNotFound:
        # Rename the standard 'Sheet1' worksheet to 'inhoud'
        try:
            sheet1 = spreadsheet.worksheet('Sheet1')
            sheet1.update_title("inhoud")
        except gspread.exceptions.WorksheetNotFound:
            try:
                blad1 = spreadsheet.worksheet('Blad1')
                blad1.update_title("inhoud")
            except gspread.exceptions.WorksheetNotFound:
                spreadsheet.add_worksheet('inhoud', rows=16, cols=6)

    return spreadsheet


def create_worksheet(spreadsheet_name, worksheet_name, rows, cols):
    spreadsheet = get_spreadsheet(spreadsheet_name)
    try:
        old_worksheet = spreadsheet.worksheet(worksheet_name)
        old_worksheet.update_title("old")
    except gspread.exceptions.WorksheetNotFound:
        pass
    worksheet = spreadsheet.add_worksheet(worksheet_name, rows=rows, cols=cols)
    try:
        spreadsheet.del_worksheet(old_worksheet)
    except (UnboundLocalError, gspread.exceptions.WorksheetNotFound):
        pass
    return worksheet


def fill_range(sheet_tab: Worksheet, row: int, col: int, data: list):
    if not data:
        return
    if not isinstance(data[0], list):
        data = [data]  # 1-dimensional, make 2-dimensional
    # Select a range
    cell_list = sheet_tab.range(
        row, col, row + len(data) - 1, col + len(data[0]) - 1
    )  # row, col, lastrow, lastcol
    for cell in cell_list:
        cell.simplicate_part = data[cell.row - row][cell.col - col]
    # Update in batch
    sheet_tab.update_cells(cell_list)


def format_range(sheet_tab: Worksheet, range:str, bold=None, font_size=None, align=None, font_color=None, background_color:tuple=None):
    format = {}
    if align:
        format["horizontalAlignment"] = align
    if bold is not None:
        if not "textFormat" in format:
            format["textFormat"] = {}
        format["textFormat"]["bold"] = bold
    if font_size is not None:
        if not "textFormat" in format:
            format["textFormat"] = {}
        format["textFormat"]["fontSize"] = font_size
    if font_color:
        if not "textFormat" in format:
            format["textFormat"] = {}
        format["textFormat"]["foregroundColor"] = {
            "red": font_color[0],
            "green": font_color[1],
            "blue": font_color[2],
            "alpha": 1
        }
    if background_color:
        format["backgroundColor"] = {
            "red": background_color[0],
            "green": background_color[1],
            "blue": background_color[2],
            "alpha": 1
        }

    sheet_tab.format(range, format)


