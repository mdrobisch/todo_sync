from urllib.parse import urlparse
from datetime import timedelta


def get_updates_required(
    github_issue,
    caldav_todo,
    exclude_closed,
    exclude_backlog,
    exclude_active,
):
    todo_last_update_date = caldav_todo.icalendar_component["dtstamp"].dt
    todo_status = "NEEDS-ACTION"
    if "status" in caldav_todo.icalendar_component:
        todo_status = str(caldav_todo.icalendar_component["status"])

    # check for updates
    if "created" in caldav_todo.icalendar_component:
        todo_last_update_date = caldav_todo.icalendar_component["created"].dt
    if "last-modified" in caldav_todo.icalendar_component:
        todo_last_update_date = caldav_todo.icalendar_component["last-modified"].dt
    # the todo was updated lately => need to update the issue
    if todo_last_update_date > github_issue.updated_at:
        issue_to_update_dict = {}

        # check for changes in the description
        if github_issue.body != str(caldav_todo.icalendar_component["description"]):
            issue_to_update_dict["description"] = str(
                caldav_todo.icalendar_component["description"]
            )
        # check for title changes
        if github_issue.title != str(caldav_todo.icalendar_component["summary"]):
            issue_to_update_dict["title"] = str(
                caldav_todo.icalendar_component["summary"]
            )
        # check for todo is done
        if todo_status == "COMPLETED" or "completed" in caldav_todo.icalendar_component:
            if not github_issue.closed:
                issue_to_update_dict["close"] = True
        else:
            if github_issue.closed:
                issue_to_update_dict["reopen"] = True

        if len(issue_to_update_dict) == 0:
            issue_to_update_dict = None
        return None, issue_to_update_dict

    # the issue was updated lately => need to update the todo
    if todo_last_update_date < github_issue.updated_at:
        todo_to_update_dict = {}

        # check for iteration updates
        if "due" in caldav_todo.icalendar_component:
            if (
                github_issue.project_iteration_due_date
                != caldav_todo.icalendar_component["due"].dt
            ):
                todo_to_update_dict["due_date"] = (
                    github_issue.project_iteration_due_date
                )
        else:
            if github_issue.project_iteration_due_date:
                if not github_issue.closed:
                    todo_to_update_dict["due_date"] = (
                        github_issue.project_iteration_due_date
                    )

        # check for changes in the description
        if github_issue.body != str(caldav_todo.icalendar_component["description"]):
            todo_to_update_dict["description"] = github_issue.body
        # check for title changes
        if github_issue.title != str(caldav_todo.icalendar_component["summary"]):
            todo_to_update_dict["title"] = github_issue.title
        # check for issue is done
        if todo_status == "COMPLETED" or "completed" in caldav_todo.icalendar_component:
            if not github_issue.closed:
                # check for project status updates
                if exclude_backlog:
                    if github_issue.project_status.lower() != "backlog":
                        todo_to_update_dict["reopen"] = True
                else:
                    todo_to_update_dict["reopen"] = True
        else:
            if github_issue.closed:
                todo_to_update_dict["close"] = True
            else:
                # check for project status updates
                if exclude_backlog:
                    if github_issue.project_status.lower() == "backlog":
                        todo_to_update_dict["close"] = True                   


        if len(todo_to_update_dict) == 0:
            todo_to_update_dict = None
        return todo_to_update_dict, None

    return None, None


def merge_issues_and_project_items(repo_issues, project_items):
    item_dict = {}
    for item in project_items:
        item_dict[item.content.id] = {"_updated_at": item.updated_at}
        for n in item.field_values.nodes:
            try:
                if n.field.data_type == "SINGLE_SELECT":
                    item_dict[item.content.id][str(n.field.name).lower()] = n.name
                if n.field.data_type == "ITERATION":
                    item_dict[item.content.id][str(n.field.name).lower()] = n
            except Exception as e:
                pass
    for issue in repo_issues:
        matched = item_dict.get(issue.id, None)
        if matched:
            status = matched.get("status", None)
            workspace = matched.get("workspace", None)
            iteration = matched.get("iteration", None)

            if matched["_updated_at"] > issue.updated_at:
                issue.updated_at = matched["_updated_at"]

            if status:
                issue.project_status = status
            else:
                issue.project_status = None

            if workspace:
                issue.project_workspace = workspace
            else:
                issue.project_workspace = None

            if iteration:
                issue.project_iteration_name = iteration.title
                issue.project_iteration_due_date = iteration.start_date + timedelta(
                    days=iteration.duration - 1
                )
            else:
                issue.project_iteration_name = None
                issue.project_iteration_due_date = None
                pass
            pass
    return repo_issues


def match_todos_and_issues(
    caldav_todo_dict,
    github_issues_dict,
    exclude_closed=False,
    exclude_backlog=False,
    exclude_active=False,
):
    github_issues_to_create_dict = {}
    github_issues_to_update_dict = {}
    caldav_todos_to_create_dict = {}
    caldav_todos_to_update_dict = {}

    referenced_issues_list = []
    todo_issue_pair_list = []

    # check for gitlab issues to add
    for k_t, t in caldav_todo_dict.items():
        summary = str(t.vobject_instance.vtodo.summary.value).strip()
        if "description" in t.vobject_instance.vtodo.contents:
            description = str(t.vobject_instance.vtodo.description.value).strip()
            link = description.split("\n")[0].strip().lower()
            if link in github_issues_dict.keys():
                referenced_issues_list.append(link)
                todo_issue_pair_list.append(
                    ((k_t, t), (link, github_issues_dict[link]))
                )
                continue
        if (
            exclude_closed
            and "completed" in t.vobject_instance.vtodo.contents
            and t.vobject_instance.vtodo.completed.value
        ):
            continue
        print(f"{summary} issue needs to be added")
        github_issues_to_create_dict[k_t] = t

    # check for caldav todos to add
    for k_i, i in github_issues_dict.items():
        if i.project_status.lower() not in ["done", "canceled"]:
            if i.closed:
                print(f"{i.title} issue needs to be reopened")
                github_issues_to_update_dict[k_i] = {"reopen": True}
        if k_i in referenced_issues_list:
            continue
        if exclude_closed and i.closed:
            continue
        print(f"{i.title} todo needs to be added")
        caldav_todos_to_create_dict[k_i] = i

    # check for updates needed
    for (k_t, t), (k_i, i) in todo_issue_pair_list:
        summary = str(t.vobject_instance.vtodo.summary.value).strip()
        todo_updates, issue_updates = get_updates_required(
            i, t, exclude_closed, exclude_backlog, exclude_active
        )
        if todo_updates:
            print(f"{summary} todo needs to be updated {list(todo_updates.keys())}")
            caldav_todos_to_update_dict[k_t] = todo_updates
        else:
            if issue_updates:
                print(
                    f"{summary} issue needs to be updated {list(issue_updates.keys())}"
                )
                github_issues_to_update_dict[k_i] = issue_updates

    return {
        "github_issues_to_create_dict": github_issues_to_create_dict,
        "github_issues_to_update_dict": github_issues_to_update_dict,
        "caldav_todos_to_create_dict": caldav_todos_to_create_dict,
        "caldav_todos_to_update_dict": caldav_todos_to_update_dict,
    }
