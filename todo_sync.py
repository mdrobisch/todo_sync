import json
import os
import caldav

# Access environment variables as if they came from the actual environment
CALENDAR_URL = "https://cloud.fabba.space/remote.php/dav/calendars/mdrobisch@auphoria/dashboard-active/"

sync_config : dict
sync_config = json.load(open("sync_config.json", "r"))

with caldav.DAVClient(url=CALENDAR_URL, username=sync_config.get("global_username"), password=sync_config.get("global_password")) as client:
    my_principal = client.principal()
    calendars = my_principal.calendars()
    sel_cal = my_principal.calendar('Dashboard (active)')
    
    sel_cal.add_todo(
        summary="Test2 sum",
        description="https://python.org\n\nAnd some more",
        status="",
        priority=5,
        percent_complete=0,
        completed=None,
        categories=[],
        url="https://google.com"
    )
    todos = sel_cal.todos()
    pass
print("Done")