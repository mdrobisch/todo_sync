# todo_sync


```
# Get the latest github grapql schema and convert it using introspection
uv run python -m sgqlc.introspection --exclude-deprecated --exclude-description -H "Authorization: bearer ${GH_TOKEN}" https://api.github.com/graphql github_schema.json
```

```
# Convert the schema.json to a python lib
uvx --from sgqlc sgqlc-codegen schema .\github_schema.json github_schema.pyrectory: '.\\github.schema.json'
```