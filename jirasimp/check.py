from jira import get_data_from_jira

if __name__=="__main__":
    from utilities import month_in_weeks, get_report_mapping
    from dotenv import load_dotenv
    load_dotenv()
    period = month_in_weeks(2022, 8)
    for report_name in get_report_mapping().keys():

        issues, jw, jira_labels = get_data_from_jira(report_name, period)
