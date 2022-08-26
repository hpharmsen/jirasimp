""" Handling the Jira side of things """
import json
import os
import sys
import requests
from requests.auth import HTTPBasicAuth

from justdays import Day, Period

from .utilities import get_report_mapping


class Jira:
    def __init__(self, server=None, token=None, email=None):
        if not server:
            server = os.environ['JIRA_SERVER']
            token = os.environ['JIRA_API_TOKEN']
            email = os.environ['JIRA_API_EMAIL']

        self.auth = HTTPBasicAuth(email, token)
        self.headers = {"Accept": "application/json"}
        self.base_url = f"{server}rest/api/3/"

    def request(self, endpoint: str, collect_field:str):
        url = self.base_url + endpoint
        full_result = []
        start_at = 0
        max_results = 200
        while True:
            connector = '&' if url.count('?') else '?'
            full_url = f'{url}{connector}startAt={start_at}&maxResults={max_results}'
            response = requests.request("GET", full_url, headers=self.headers, auth=self.auth)
            result = json.loads(response.text)
            if result.get('errorMessages'):
                for message in result['errorMessages']:
                    print('jira_request:', message)
                sys.exit(1)
            full_result += result[collect_field]
            amount_returned = len(result[collect_field])
            total = result['total']
            if start_at + amount_returned >= total:
                break
            start_at += amount_returned
        return full_result

def get_data_from_jira(report_name, period):
    issues = {}
    worklogs = {}
    jira_labels = []
    report_mapping = get_report_mapping()[report_name]
    for jira_part, simplicate_part in report_mapping.items():
        try:
            jira_project, jira_label = jira_part.split('/')
        except ValueError:
            jira_project = jira_part
            jira_label = ""
        if not jira_project:
            continue # Entry met alleen Simplicate part. Is om Simplicate issues daaruit te moven
        project_issues = jira_issues_with_worklogs(jira_project, jira_label, period)
        worklogs.update(worklogs_with_services(project_issues, jira_project, period))
        issues.update(project_issues)
        if jira_label:
            jira_labels += [jira_label]
    return issues, worklogs, jira_labels



def jira_issues_with_worklogs(project:str, label:str, period:Period):
    jira = Jira()
    jql = f'search?jql=project={project} AND worklogDate>="{period.fromday}" AND worklogDate<"{period.untilday}"' + \
        f'&fields=worklog,labels,summary,status,timespent,priority,issuetype,customfield_10447'
    issues = jira.request(jql, collect_field = 'issues')

    # Filter on labels
    if label:
        issues = [issue for issue in issues if label in issue['fields']['labels']]

    for issue in issues:

        del(issue['expand'])
        del(issue['self'])

        # Mmm, it appears that this query returns a maximum amount of worklogs per issue
        # If there are more, request the full set of worklogs separately
        if issue['fields']['worklog']['total'] > issue['fields']['worklog']['maxResults']:
            issue['fields']['worklog']['worklogs'] = get_full_worklog_from_issue(issue['key'])
        issue['worklogs'] = issue['fields']['worklog']['worklogs']

        if issue['fields']['customfield_10447']:
            issue['tshirt_size'] = issue['fields']['customfield_10447']['value']
            del(issue['fields']['customfield_10447'])
        else:
            issue['tshirt_size'] = ''

        issue['priority'] = issue['fields']['priority']['name']
        del(issue['fields']['priority'])

        issue['issuetype'] = issue['fields']['issuetype']['name']
        del(issue['fields']['issuetype'])

        issue['status'] = issue['fields']['status']['name']
        del(issue['fields']['status'])

        issue['summary'] = issue['fields']['summary']
        issue['labels'] = issue['fields']['labels']
        issue['timespent_total'] = issue['fields']['timespent'] / 3600
        del(issue['fields'])

    return {issue['key']:issue for issue in issues}


def get_full_worklog_from_issue(issue_key:str):
    """Returns all worklogs for an issue"""
    jira = Jira()
    # todo: add startedAfter en startedBefore Unix timestamp parameters
    res = jira.request(f'issue/{issue_key}/worklog', collect_field='worklogs')
    return res


def worklogs_with_services(issues:dict, jira_project:str, period:Period):
    """ Returns a list of JiraWorklog named tuples """

    mapping = read_flattened_mapping()

    worklogs = {}
    for issue_key in issues.keys():
        issue = issues[issue_key]

        # Check the labels for a matching Simplicate service
        labels = issue['labels']
        if not labels:
            # todo: Later willen we dat ieder issue een label heeft
            #print( f'Issue {issue_key} has no labels')
            #continue
            labels = [""] # Add default empty label
        projects_and_services = []
        for label in labels:
            mapping_key = f'{jira_project}/{label}'
            if mapping_key in mapping:
                projects_and_services += [mapping[mapping_key]]
        if not projects_and_services:
            #print( f'Issue {issue_key} has no valid labels. Labels found: {labels}')
            #continue
            try:
                projects_and_services = mapping[jira_project+'/']
            except KeyError:
                projects_and_services = mapping[jira_project] # Add default empty label
            if type(projects_and_services) != list:
                projects_and_services = [projects_and_services]
        elif len(projects_and_services) > 1:
            print( f'Issue {issue_key} has multiple matching services. Labels: {labels} Services found: {projects_and_services}')
            continue
        project_and_service = projects_and_services[0]
        #simplicate_project, simplicate_service = project_and_service.split('/') if project_and_service.count('/') else project_and_service, ''
        # Process the worklogs
        for worklog in issue['worklogs']:
            day = Day(worklog['started'].split('T')[0])

            # Query returned all issues that have worklogs within the specified period
            # However not all worklogs from these issues are necessarily within this period
            if not day in period:
                continue

            if worklog.get('comment'):
                comment = parse_comment(worklog['comment'])
            else:
                comment = ''

            id = worklog['id']
            time_spent = worklog['timeSpentSeconds'] / 3600
            employee = worklog['author']['displayName']
            values = {'day': day, 'employee': employee, 'project_and_service': f"{project_and_service}",  #'project': project, 'service': service,
                      'issue_key': issue_key, 'hours': time_spent, 'comment': comment}
            worklogs[id] = values

            # !! Tijdelijk uitgecomm
            old_timespent = issues[issue_key].get('timespent', 0)
            issues[issue_key]['timespent'] = old_timespent + time_spent
    return worklogs


def read_flattened_mapping():
    """ Reads the jira projects+keys and simplicate services from the mapping file
        and returns them in a single dictionary """

    with open('mapping.json') as mapping_file:
        projects = json.load(mapping_file).values()
        mapping = {}
        for project_dict in projects:
            mapping.update(project_dict)
    return mapping


def parse_comment(comment):
    if comment.get('text'):
        return comment['text']
    for content in comment['content']:
        if content.get('text'):
            return content['text']
        return " ".join([parse_comment(subcontent) for subcontent in content['content']])


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
