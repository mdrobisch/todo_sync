import json
import os
import caldav

# Access environment variables as if they came from the actual environment
CALENDAR_URL = "https://cloud.fabba.space/remote.php/dav/calendars/mdrobisch@auphoria/dashboard-active/"

sync_config : dict
sync_config = json.load(open("sync_config.json", "r"))

with caldav.DAVClient(url=CALENDAR_URL, username=sync_config.get("global_caldav_username"), password=sync_config.get("global_caldav_password")) as client:
    my_principal = client.principal()
    calendars = my_principal.calendars()
    sel_cal = my_principal.calendar('Dashboard (active)')
    todos = sel_cal.todos(include_completed=True)
    print(todos[0].vobject_instance.vtodo.completed)
    
    sel_cal.add_todo(
        summary="Test3 sum",
        description="https://python.org\n\nAnd some more",
        status="NEEDS-ACTION",
        priority=5,
        percent_complete=0,
        completed=None,
        categories=[],
        url="https://google.com"
    )
    todos = sel_cal.todos()
    pass
print("Done")

'BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:+//IDN bitfire.at//ical4android (org.dmfs.tasks)\nBEGIN:VTODO\nCOMPLETED:20250506T090342Z\nDESCRIPTION:https://www.w3schools.com/python/ref_dictionary_get.asp\\n\\nAnd \n some mor\nDTSTAMP:20250506T090342Z\nLAST-MODIFIED:20250506T090342Z\nPERCENT-COMPLETE:100\nPRIORITY:5\nSEQUENCE:1\nSTATUS:COMPLETED\nSUMMARY:Test sum\nUID:159f5baf-2a56-11f0-9330-3c9c0f83f549\nURL:https://google.com\nEND:VTODO\nEND:VCALENDAR\n'