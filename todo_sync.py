import json
import traceback
import caldav
from icalendar import vDatetime, vDDDTypes
from sync import match_todos_and_issues, merge_issues_and_project_items
from copy import deepcopy, copy
from datetime import datetime, timezone, timedelta
from github_client import GHClient
from time import sleep

# 'https://cloud.fabba.space:443/remote.php/dav/calendars/mdrobisch%40auphoria/personal_shared_by_mdrobisch/2d491c05-2cf6-4518-b580-9b495afdc78e.ics'
# Access environment variables as if they came from the actual environment
sync_config: dict
sync_config = json.load(open("sync_config.json", "r"))


def check_and_delete_inactive_todo(caldav_todo):
    todo_status = "NEEDS-ACTION"
    if "status" in caldav_todo.icalendar_component:
        todo_status = str(caldav_todo.icalendar_component["status"])
    if todo_status == "COMPLETED" or "completed" in caldav_todo.icalendar_component:
        now = datetime.now()
        if caldav_todo.icalendar_component["completed"].dt.tzinfo:
            now = datetime.now(tz=timezone.utc)
        if now > caldav_todo.icalendar_component["completed"].dt + timedelta(days=60):
            caldav_todo.delete()
            pass


while True:
    # sleep(42)
    try:
        CALENDAR_USER_BASE_URL = (
            "https://cloud.fabba.space/remote.php/dav/calendars/mdrobisch@auphoria/"
        )
        CALENDAR_NAME = "mdrobisch@fabba.cloud"
        REPOSITORY_NAME = "todo"
        GITHUB_PROJECT_NAME = "Dashboard"

        # collect all todos of the calendar and copy them
        caldav_todo_dict = {}
        with caldav.DAVClient(
            url=CALENDAR_USER_BASE_URL,
            username=sync_config.get("global_caldav_username"),
            password=sync_config.get("global_caldav_password"),
        ) as client:
            my_principal = client.principal()
            calendars = my_principal.calendars()
            sel_cal = my_principal.calendar(CALENDAR_NAME)
            todos = sel_cal.todos(include_completed=True)

            for t in todos:
                caldav_todo_dict[str(t.canonical_url).lower()] = copy(t)

        # collect all todos of the calendar and copy them
        github_issues_dict = {}
        github_client = GHClient(
            user_login="mdrobisch", access_token=sync_config.get("global_github_token")
        )
        repo_id, repo_issues = github_client.get_repository_issues(REPOSITORY_NAME)
        project_id, project_items = github_client.get_project(GITHUB_PROJECT_NAME)
        extended_repo_issues = merge_issues_and_project_items(
            repo_issues, project_items
        )

        for i in extended_repo_issues:
            github_issues_dict[str(i.url).lower()] = copy(i)

        sync_dict = match_todos_and_issues(
            caldav_todo_dict,
            github_issues_dict,
            exclude_closed=True,
            exclude_backlog=True
        )

        with caldav.DAVClient(
            url=CALENDAR_USER_BASE_URL,
            username=sync_config.get("global_caldav_username"),
            password=sync_config.get("global_caldav_password"),
        ) as client:
            my_principal = client.principal()
            calendars = my_principal.calendars()
            sel_cal = my_principal.calendar(CALENDAR_NAME)
            todos = sel_cal.todos(include_completed=True)

            for t in todos:
                todo_id = str(t.canonical_url).lower()
                actual_todo_description = ""
                if "description" in t.icalendar_component:
                    actual_todo_description = str(t.icalendar_component["description"])

                # create a new github issue and update the todo with its link
                if todo_id in sync_dict["github_issues_to_create_dict"].keys():
                    r = github_client.create_issue(
                        repo_id,
                        t.icalendar_component["summary"],
                        actual_todo_description,
                    )
                    t.icalendar_component["description"] = (
                        f"{r.create_issue.issue.url}\n-\n" + actual_todo_description
                    )
                    t.save()
                    github_client.update_issue(
                        issue_id=r.create_issue.issue.id,
                        body=f"{r.create_issue.issue.url}\n-\n"
                        + actual_todo_description,
                    )

                if todo_id in sync_dict["caldav_todos_to_update_dict"].keys():
                    updates_needed_dict = sync_dict["caldav_todos_to_update_dict"][
                        todo_id
                    ]
                    if "due_date" in updates_needed_dict:
                        if updates_needed_dict["due_date"]:
                            t.icalendar_component["due"] = vDDDTypes(
                                updates_needed_dict["due_date"]
                            )
                        else:
                            if "due" in t.icalendar_component:
                                del t.icalendar_component["due"]

                    if "description" in updates_needed_dict:
                        t.icalendar_component["description"] = updates_needed_dict[
                            "description"
                        ]

                    if "title" in updates_needed_dict:
                        t.icalendar_component["summary"] = updates_needed_dict["title"]

                    if "close" in updates_needed_dict:
                        t.icalendar_component["status"] = "COMPLETED"
                        t.icalendar_component["completed"] = vDatetime(
                            datetime.now(tz=timezone.utc)
                        )

                    if "reopen" in updates_needed_dict:
                        if "completed" in t.icalendar_component:
                            t.icalendar_component["status"] = "NEEDS-ACTION"
                            t.icalendar_component["percent-complete"] = 0
                            del t.icalendar_component["completed"]

                    t.save()
                    pass
                    """
                    t.icalendar_component["summary"] = sync_dict[
                        "caldav_todos_to_update_dict"
                    ][todo_id].title
                    t.save()
                    if issue.closed:  # we need to close the todo
                        t.icalendar_component["status"] = "COMPLETED"
                        if "completed" not in t.icalendar_component:
                            t.icalendar_component.add(
                                "completed", vDatetime(datetime.now())
                            )
                        else:
                            if t.icalendar_component["completed"] is None:
                                t.icalendar_component["completed"] = vDatetime(
                                    datetime.now()
                                )
                            else:
                                t.icalendar_component["completed"].dt = datetime.now()
                        t.save()
                    else:
                        if "completed" in t.icalendar_component:
                            t.icalendar_component["status"] = "NEEDS-ACTION"
                            del t.icalendar_component["completed"]
                            t.save()
                            pass

                    pass
                    """

                check_and_delete_inactive_todo(t)

        for k_i, updates_dict in sync_dict["github_issues_to_update_dict"].items():
            issue = github_issues_dict[k_i]

            if "description" in updates_dict:
                github_client.update_issue(
                    issue_id=issue.id,
                    body=str(updates_dict["description"]),
                )

            if "title" in updates_dict:
                github_client.update_issue(
                    issue_id=issue.id,
                    title=str(updates_dict["title"]),
                )

            if "close" in updates_dict:
                github_client.close_issue(issue.id)

            if "reopen" in updates_dict:
                github_client.reopen_issue(issue.id)

        with caldav.DAVClient(
            url=CALENDAR_USER_BASE_URL,
            username=sync_config.get("global_caldav_username"),
            password=sync_config.get("global_caldav_password"),
        ) as client:
            my_principal = client.principal()
            calendars = my_principal.calendars()
            sel_cal = my_principal.calendar(CALENDAR_NAME)
            todos = sel_cal.todos(include_completed=True)

            for k_i, i in sync_dict["caldav_todos_to_create_dict"].items():
                description = f"{i.url}\n-\n{i.body}"

                sel_cal.add_todo(
                    summary=i.title,
                    description=description,
                    status="NEEDS-ACTION",
                    priority=5,
                    percent_complete=0,
                    completed=None,
                    categories=[],
                    url=str(i.url),
                )
                github_client.update_issue(issue_id=i.id, body=str(description))

                pass
        print()
    except Exception as e:
        print(e)
        traceback.print_exc()
