""" Handling the Simplicate part of things """
import json
import os
import re

from justdays import Period, Day
from pysimplicate import Simplicate

# Simplicate singleton
from .utilities import get_report_mapping

_simplicate = None


def simplicate():
    global _simplicate
    if not _simplicate:
        key = os.environ["simplicate_api_key"]
        secret = os.environ["simplicate_api_secret"]
        domain = os.environ["simplicate_subdomain"]
        _simplicate = Simplicate(domain, key, secret)
    return _simplicate


# def all_simplicate_hours(period):
#     sim = simplicate()
#     filter = {"start_date": period.fromday, "end_date": period.untilday}
#     filename = f"cache/{period.fromday}_{period.untilday}.json"
#     if os.path.exists(filename):
#         print(f"Loading {filename}")
#         with open(filename, 'r') as f:
#             hours = json.load(f)
#     else:
#         hours = sim.hours(filter)
#         with open(filename, 'w') as f:
#             json.dump(hours, f)
#     return hours


# def hours_with_jira_origin(period: Period):
#     result = []
#     for hours_entry in all_simplicate_hours(period):
#         note = hours_entry.get('note', '')
#         if not note:
#             continue
#         project_number = hours_entry['project'].get('project_number')
#         if not project_number:
#             continue
#         values = {
#             'day': Day(hours_entry['start_date'].split()[0]),
#             'employee': hours_entry['employee']['name'],
#             'project': project_number,
#             'service': hours_entry['projectservice']['name'],
#             'comment': note,
#             'hours': hours_entry['hours'],
#             'simplicate_hours_id': hours_entry['id']
#         }
#         re_match = re.match("(^[A-Za-z]+-\d+) (.*)\((\d+)\)(.*)",
#                             note)  # Format TEX-123 bla bla (1234) And possible some more text
#         if re_match:
#             values['issue'], extra_text_1, values['jira_worklog_id'], extra_text2 = re_match.groups()
#             #values[
#             #    'note'] = f"{values['issue']} ({jira_worklog_id}) {extra_text_1.strip()} {extra_text2.strip()}".strip()
#         else:
#             re_match = re.match("(.*) \((\d+)\)(.*)", note)  # Format T0-123 (1234)
#             if re_match:
#                 values['issue'], values['jira_worklog_id'], extra_text2 = re_match.groups()
#                 #values['note'] = f"{values['issue']} ({jira_worklog_id}) {extra_text2.strip()}".strip()
#             else:
#                 continue
#         result += [values]
#     return result

def simplicate_hours( report_name, period:Period):
    sim = simplicate()
    report_mapping = get_report_mapping()[report_name]
    worklogs_by_id = {}
    unspecified_worklogs = []

    # Collect all Simplicate projects involved in this report
    simplicate_projects = []
    for jira_part, simplicate_part in report_mapping.items():
        simplicate_projects += simplicate_part.split(',')

    for simplicate_project in simplicate_projects:
        simplicate_project = simplicate_project.strip()
        if simplicate_project.count('/'):
            simplicate_project, simplicate_service = simplicate_project.split('/')
        else:
            simplicate_service = None
        filter = {'project': simplicate_project, "start_date": period.fromday, "end_date": period.untilday}
        filename = f"{simplicate_project}_{period.fromday}_{period.untilday}.json"
        if simplicate_service:
            filter['service'] = simplicate_service
            filename = filter['service'] + '_' + filename
        filename = 'cache/' + filename
        if os.path.exists(filename):
            #print(f"Loading {filename}")
            with open(filename, 'r') as f:
                hours = json.load(f)
        else:
            hours = sim.hours(filter)
            with open(filename, 'w') as f:
                json.dump(hours, f)
        for index in range(len(hours)):
            try:
                hours_entry = hours[index] # Kromme ouderwetse manier maar met for entry in hours crasht ie op de laatste
            except:
                continue
            note = hours_entry.get('note','')
            values = {
                'day': Day(hours_entry['start_date'].split()[0]),
                'employee' : hours_entry['employee']['name'],
                'project_and_service': hours_entry['project']['project_number'] + '/' + hours_entry['projectservice']['name'],
                'comment': note,
                'hours': hours_entry['hours'],
                'simplicate_hours_id': hours_entry['id']
            }

            re_match = re.match("(^[A-Za-z]+-\d+) (.*)\((\d+)\)(.*)", note)  # Format TEX-123 bla bla (1234) And possible some more text
            if re_match:
                values['issue_key'], extra_text_1, jira_worklog_id, extra_text2 = re_match.groups()
                values['note'] = f"{values['issue_key']} ({jira_worklog_id}) {extra_text_1.strip()} {extra_text2.strip()}".strip()
                worklogs_by_id[jira_worklog_id] = values
            else:
                re_match = re.match("(.*) \((\d+)\)(.*)", note)  #  Format T0-123 (1234)
                if re_match:
                    values['issue_key'], jira_worklog_id, extra_text2 = re_match.groups()
                    values['note'] = f"{values['issue_key']} ({jira_worklog_id}) {extra_text2.strip()}".strip()
                    worklogs_by_id[jira_worklog_id] = values
                elif hours_entry['hours'] == 0:
                    sim.delete_hours(hours_entry['id'])
                else:
                    unspecified_worklogs += [values]
    return worklogs_by_id, unspecified_worklogs


############ Below the line ##############

# def service_and_type_from_project(project_id: str, date_str: str):
#     try:
#         services = simplicate().service({"project_id": project_id, "status": "open"})
#     except:
#         print( f'Load Simplicate services for project {project_id}\n\n {simplicate().error}')
#         return "", ""
#
#     valid_services = []
#     for service in services:
#         print("SERVICE FOUND", service["name"], service["id"])
#         if service.get('write_hours_end_date') and service.get('write_hours_end_date') < date_str:
#             print('BUT SERVICE HAS ENDED')
#             continue
#         if service.get('write_hours_start_date') and service.get('write_hours_start_date') > date_str:
#             print('BUT SERVICE HAS NOT YET STARTED')
#             continue
#         valid_services += [service]
#
#     try:
#         first_valid_service = valid_services[0]
#         print("SERVICE", first_valid_service["name"], first_valid_service["id"])
#
#         hour_types = first_valid_service["hour_types"]
#
#         # If a hours type called development exists, use that one
#         if development := [ht for ht in hour_types if ht['hourstype']['label'] == 'Development']:
#             hour_types = development
#         elif misc := [ht for ht in hour_types if ht['hourstype']['label'] == 'Other / Unaccountable']:
#             hour_types = misc
#         first_hour_type = hour_types[0]["hourstype"]
#         print("HOUR_TYPE", first_hour_type["label"], first_hour_type["id"])
#         return first_valid_service["id"], first_hour_type["id"]
#     except:
#         print( f"Failed extract service and type from project: {project_id}")
#         return "", ""
#
#
# def employee_id_from_name(employee_name: str):
#     try:
#         employee = simplicate().employee({"full_name": employee_name})[0]
#         return employee["id"]
#     except:
#         print( f'Failed to get Simplicate employee id from name: {employee_name}\n\n{simplicate().error}')
#
#
# def project_id_from_number(project_number: str):
#     try:
#         project = simplicate().project({"project_number": project_number})[0]
#         return project["id"]
#     except:
#         print( f'Failed to get Simplicate project id from Jira project {project_number}\n\n{simplicate().error}')
#
#
# def post_hours(hours_data: dict):
#     sim = simplicate()
#     return sim.book_hours(hours_data)
