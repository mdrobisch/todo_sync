from urllib.parse import urlparse
import re


def update_is_required(github_issue, caldav_todo):
    changes_found = False

    # check for changes in the description
    if github_issue.body != str(caldav_todo.icalendar_component["description"]):
        changes_found = True

    if github_issue.title != str(caldav_todo.icalendar_component["summary"]):
        changes_found = True


    todo_status = "NEEDS-ACTION"
    if "status" in caldav_todo.icalendar_component:
        todo_status = str(caldav_todo.icalendar_component["status"])
    if todo_status == "COMPLETED" or "completed" in caldav_todo.icalendar_component:
        if not github_issue.closed:
            changes_found = True
    else:
        if github_issue.closed:
            changes_found = True

    if changes_found:
        todo_last_update_date = caldav_todo.icalendar_component["dtstamp"].dt
        if "created" in caldav_todo.icalendar_component:
            todo_last_update_date = caldav_todo.icalendar_component["created"].dt
        if "last-modified" in caldav_todo.icalendar_component:
            todo_last_update_date = caldav_todo.icalendar_component["last-modified"].dt
        # the todo was updated lately => need to update the issue
        if todo_last_update_date > github_issue.updated_at:
            return False, True
        # the issue was updated lately => need to update the todo
        if todo_last_update_date< github_issue.updated_at:
            return True, False
          
    return False, False

def match_todos_and_issues(
    caldav_todo_dict,
    github_issues_dict,
    exclude_closed=False,
):
    github_issues_to_create_dict = {}
    github_issues_to_update_dict = {}
    caldav_todos_to_create_dict = {}
    caldav_todos_to_update_dict = {}
    referenced_issues_list = []

    for k_t, t in caldav_todo_dict.items():
        summary = str(t.vobject_instance.vtodo.summary.value).strip()
        if "description" in t.vobject_instance.vtodo.contents:
            description = str(t.vobject_instance.vtodo.description.value).strip()
            link = description.split("\n")[0].strip().lower()
            if link in github_issues_dict.keys():
                referenced_issues_list.append(link)
                issue = github_issues_dict[link]
                todo_update, issue_update = update_is_required(issue, t)
                if todo_update:
                    print(f"{summary} todo needs to be updated")
                    caldav_todos_to_update_dict[k_t] = issue
                else:
                    if issue_update:
                        print(f"{summary} issue needs to be updated")
                        github_issues_to_update_dict[link] = t

                continue
        if (
            exclude_closed
            and "completed" in t.vobject_instance.vtodo.contents
            and t.vobject_instance.vtodo.completed.value
        ):
            continue

        print(f"{summary} issue needs to be added")
        github_issues_to_create_dict[k_t] = t

    for k_i, i in github_issues_dict.items():
        if k_i in referenced_issues_list:
            continue
        print(f"{i.title} todo needs to be added")
        caldav_todos_to_create_dict[k_i] = i


    return {
        "github_issues_to_create_dict": github_issues_to_create_dict,
        "github_issues_to_update_dict": github_issues_to_update_dict,
        "caldav_todos_to_create_dict": caldav_todos_to_create_dict,
        "caldav_todos_to_update_dict": caldav_todos_to_update_dict,
    }
