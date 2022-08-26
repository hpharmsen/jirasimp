#!/usr/bin/env python3
import json

# todo: - Label per klant
# - Apart label voor Doorontwikkelbudget,
# - labels kunnen hoofdletters hebben
# - Er zijn ook allerlei labels die niet gebruikt worden
# - Indeling gaat per week dus een maand heeft 4 of 5 hele weken
# - Script dagelijks, of iig wekelijks kunnen runnen
# - Lijst maken met errors (bv missend label of twee eilandlabels)
# - Script genereert overzicht zoals Miek dat heeft in Excel maar dan in Google sheets
# - Splitsen tussen besteed deze maand en besteed totaal op de issue
# - T-shirt sizes erbij

from dotenv import load_dotenv

from jirasimp import get_jira_worklogs, Jira
from jirasimp.compare import comparison
from simplicate import get_simplicate_worklogs, simplicate
from utilities import format_item


def get_report_mapping():
    with open('mapping.json') as mapping_file:
        reporting_units = json.load(mapping_file)
    return reporting_units


if __name__ == "__main__":
    load_dotenv()
    year = 2022
    month = 7

    #period = month_in_weeks(year, month)
    #period = Period('2022-05-02','2022-05-03')

    report_mapping = get_report_mapping()
    jira = Jira()
    jira_worklogs, report_data = get_jira_worklogs(jira, year, month, report_mapping)
    sim = simplicate()
    simplicate_worklogs = get_simplicate_worklogs(sim, year, month, report_mapping)

    #for report_name in get_report_mapping().keys():
        #report(report_name, year, month, jira_labels, issues)

    missing_from_simplicate, missing_from_jira, update_in_simplicate = comparison(jira_worklogs, simplicate_worklogs)

    if missing_from_simplicate:
        print( '\nFOUND IN JIRA BUT MISSING FROM SIMPLICATE')
        for key in missing_from_simplicate:
            print(key, format_item(jira_worklogs[key]))

    if missing_from_jira:
        print( '\nFOUND IN SIMPLICATE BUT MISSING FROM JIRA')
        for key in missing_from_jira:
            print(key, format_item(simplicate_worklogs[key]))

    if update_in_simplicate:
        print( '\nTO UPDATE IN SIMPLICATE')
        for item in update_in_simplicate:
            print(format_item(item))
    pass