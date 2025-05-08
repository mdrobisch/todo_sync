# todo_sync

A little script to sync caldav todos with github projects.
Meant to run as a service on a server as a cron-job.

Status:
  - at the moment only sync. a single repo with caldav 
  - will sync. in both directions on updates
  - the config json for multiple repository syncs is not used at the moment
  - custom properties of project are not fully implemented yet (fetching is there, logic behind not)

```
# Get the latest github grapql schema and convert it using introspection
uv run python -m sgqlc.introspection --exclude-deprecated --exclude-description -H "Authorization: bearer ${GH_TOKEN}" https://api.github.com/graphql github_schema.json
```

```
# Convert the schema.json to a python lib
uvx --from sgqlc sgqlc-codegen schema .\github_schema.json github_schema.pyrectory: '.\\github.schema.json'
```