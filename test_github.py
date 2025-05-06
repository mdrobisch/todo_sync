import json
from datetime import datetime
from requests import Session
from sgqlc.endpoint.requests import RequestsEndpoint
from sgqlc.operation import Operation

from github_schema import (
    AddProjectV2ItemByIdInput,
    CreateIssueInput,
    Mutation,
    Query)

# Access environment variables as if they came from the actual environment
sync_config : dict
sync_config = json.load(open("sync_config.json", "r"))


class GHClient():
    def __init__(self, access_token):
        self.url = "https://api.github.com/graphql"
        self.s = Session()
        self.s.headers.update({"Authorization": f"Bearer {access_token}"})

    def execute(self, op):
        endpoint = RequestsEndpoint(self.url, session=self.s)
        cont = endpoint(op)

        errors = cont.get("errors")
        if not errors:
            return (op + cont)
        else:
            print(errors)
            raise RuntimeError(errors[0]["message"])



client = GHClient(access_token=sync_config.get("global_github_token"))

op = Operation(Query)
q = op.user(login="mdrobisch")
q.__fields__("id")
q.__fields__("email")
q.__fields__("name")
q.__fields__("location")
r = client.execute(op)
print(r)
pass


op = Operation(Query)
q = op.repository(owner="mdrobisch", name="todo")
q.__fields__("id")
q.issues(first=100)
r = client.execute(op)
print(r)
pass

op = Operation(Mutation)
input = CreateIssueInput(title="From script", body="From script", repository_id=r.repository.id)
q = op.create_issue(input=input).issue()
q.__fields__("id")

r = client.execute(op)
print(r)
# See https://github.com/vavalomi/pygithubclient/blob/main/examples.py for further examples


'''
import requests

url = "https://api.github.com/graphql"
headers = {"Authorization": "Bearer YOUR_GITHUB_TOKEN"}

query = """
mutation {
  updateIssue(input: {
    id: "ISSUE_ID",
    body: "Updated issue description"
  }) {
    issue {
      id
      body
    }
  }
}
"""

response = requests.post(url, json={"query": query}, headers=headers)
print(response.json())
'''