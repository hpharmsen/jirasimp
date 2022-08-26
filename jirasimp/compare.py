def comparison(jira_worklogs: dict, simplicate_worklogs: dict):
    missing_from_simplicate = []
    missing_from_jira = []
    update_in_simplicate = []

    keys = list(set(simplicate_worklogs.keys()) | set(jira_worklogs.keys()))
    keys.sort()
    for key in keys:
        # Nu kunnen er vier dingen het geval zijn:
        # 1. key zit helemaal niet in Jira → Report en vraag wat nu?
        # 2. key zit helemaal niet in Simplicate → Report en vraag wat nu?
        # 3. key zit in Jira+tag en in Simplicate+service en de uren kloppen → Doe niks
        # 4. key zit in Jira+tag en in Simplicsate+service en de uren kloppen niet → Update de uren in Simplicate
        # 5. Mismatch tussen Jira+tag en Simplicate+service -> Omboeken in Simplicate

        jira = jira_worklogs.get(key)
        simp = simplicate_worklogs.get(key)
        if not jira:
            # Ad 1. key zit helemaal niet in Jira → Report en vraag wat nu?
            missing_from_jira += [key]
            continue

        if not simp:
            # Ad 2. key zit helemaal niet in Simplicate → Report en vraag wat nu?
            missing_from_simplicate += [key]
            continue

        assert (jira['employee'] == simp['employee'])
        assert (jira['day'] == simp['day'])

        if simp['project_and_service'].startswith(
                jira['project_and_service']):  # Simplicate can contain a service where Jira doesn't
            if jira['hours'] == simp['hours']:
                # Ad 3. key zit in Jira+tag en in Simplicate+service en de uren kloppen → Doe niks
                continue
            else:
                # 4. key zit in Jira+tag en in Simplicsate+service en de uren kloppen niet → Update uren in Simplicate
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
