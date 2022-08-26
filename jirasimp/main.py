#!/usr/bin/env python3

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

from .jira_part import get_data_from_jira
from .simplicate import simplicate_hours
from .utilities import month_in_weeks, get_report_mapping, format_item


def comparison(jira_worklogs: dict, simplicate_worklogs: dict):
    missing_from_simplicate = []
    missing_from_jira = []
    update_in_simplicate = []

    keys = list(set(simplicate_worklogs.keys()) | set(jira_worklogs.keys()))
    keys.sort()
    for key in keys:
        # Nu kunnen er vier dingen het geval zijn:
        # 1. key zit helemaal niet in Jira -> Report en vraag wat nu?
        # 2. key zit helemaal niet in Simplicate -> Report en vraag wat nu?
        # 3. key zit in Jira+tag en in Simplicate+service en de uren kloppen -> Doe niks
        # 4. key zit in Jira+tag en in Simplicsate+service en de uren kloppen niet -> Update de uren in Simplicate
        # 5. Mismatch tussen Jira+tag en Simplicate+service -> Omboeken in Simplicate

        jira = jira_worklogs.get(key)
        simp = simplicate_worklogs.get(key)
        if not jira:
            # Ad 1. key zit helemaal niet in Jira -> Report en vraag wat nu?
            missing_from_jira += [key]
            continue

        if not simp:
            # Ad 2. key zit helemaal niet in Simplicate -> Report en vraag wat nu?
            missing_from_simplicate += [key]
            continue

        assert (jira['employee'] == simp['employee'])
        assert (jira['day'] == simp['day'])

        if simp['project_and_service'].startswith(
                jira['project_and_service']):  # Simplicate can contain a service where Jira doesn't
            if jira['hours'] == simp['hours']:
                # Ad 3. key zit in Jira+tag en in Simplicate+service en de uren kloppen -> Doe niks
                continue
            else:
                # 4. key zit in Jira+tag en in Simplicsate+service en de uren kloppen niet -> Update de uren in Simplicate
                update = {
                    'simplicate_hours_id': simp['simplicate_hours_id'],
                    'old_hours': simp['hours'],
                    'new_hours': jira['hours'],
                    'day': jira['day'],
                    'employee': jira['employee'],
                    'project_and_service': jira['project_and_service']
                }
                update_in_simplicate += [update]
        else:
            # 5. Mismatch tussen Jira+tag en Simplicate+service -> Omboeken in Simplicate
            update = {
                'simplicate_hours_id': simp['simplicate_hours_id'],
                'day': jira['day'],
                'employee': jira['employee'],
                'issue_key': jira['issue_key'],
                'old_project_and_service': simp['project_and_service'],
                'new_project_and_service': jira['project_and_service']
            }
            if jira_worklogs[key]['hours'] != simp['hours']:
                update['old_hours'] = simp['hours']
                update['new_hours'] = jira['hours']
            else:
                update['hours'] = jira['hours']

            update_in_simplicate += [update]

    #     jira_worklogs.keys():
    #     if key in simplicate_worklogs.keys():
    #         if jira_worklogs[key]['hours'] != simplicate_worklogs[key].hours:
    #         print(key, format_item(jira_worklogs[key]) )
    #         print( ' Hours differ')
    # else:
    #     print(key, format_item(simplicate_worklogs[key]))
    #     print(' Delete from Simplicate')
    return missing_from_simplicate, missing_from_jira, update_in_simplicate


def get_jira_worklogs(year, month):
    period = month_in_weeks(year, month)
    jira_worklogs = {}
    report_data = {}
    for report_name in get_report_mapping().keys():
        issues, jw, jira_labels = get_data_from_jira(report_name, period)
        jira_worklogs.update(jw)
        report_data[report_name] = {}
        report_data[report_name]['issues'] = issues
        report_data[report_name]['jira_labels'] = jira_labels
    return jira_worklogs, report_data


def get_simplicate_worklogs(year, month):
    period = month_in_weeks(year, month)
    simplicate_worklogs = {}
    for report_name in get_report_mapping().keys():
        sw, unspecified_worklogs = simplicate_hours(report_name, period)
        simplicate_worklogs.update(sw)
    return simplicate_worklogs



if __name__ == "__main__":
    load_dotenv()
    year = 2022
    month = 7

    #period = month_in_weeks(year, month)
    #period = Period('2022-05-02','2022-05-03')

    jira_worklogs, report_data = get_jira_worklogs(year, month)
    simplicate_worklogs = get_simplicate_worklogs(year, month)

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