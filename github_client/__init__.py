from datetime import datetime
from requests import Session
from sgqlc.endpoint.requests import RequestsEndpoint
from sgqlc.operation import Operation
from .github_schema import (
    CreateIssueInput,
    UpdateIssueInput,
    CloseIssueInput,
    ReopenIssueInput,
    ProjectV2SingleSelectField,
    ProjectV2ItemFieldTextValue,
    ProjectV2IterationField,
    ProjectV2SingleSelectField,
    ProjectV2ItemFieldSingleSelectValue,
    ProjectV2Field,
    ProjectV2,
    Mutation,
    Query)

class NoUpdate():
    pass

class GHClient():
    def __init__(self, org_login=None, user_login=None, access_token=None):
        if not org_login and not user_login:
            raise Exception("Unable to initialize client. Neither org_login nor user_login was given") 
        self.url = "https://api.github.com/graphql"
        self.user_id = None
        self.user_login = user_login
        self.s = Session()
        self.s.headers.update({"Authorization": f"Bearer {access_token}"})

        op = Operation(Query)
        if user_login:
            print("Use Github client with user login")
            q = op.user(login=user_login)
        else:
            print("Use Github client with organization login")
            q = op.organization(login=org_login)

        q.__fields__("id")
        q.__fields__("name")
        q.projects_v2(first=100) 
        u = self.execute(op).user
        self.user_id = u.id
        self.projects = u.projects_v2.nodes
        print()
        self.get_project("Dashboard")
        pass

    def execute(self, op):
        endpoint = RequestsEndpoint(self.url, session=self.s)
        cont = endpoint(op)

        errors = cont.get("errors")
        if not errors:
            return (op + cont)
        else:
            print(errors)
            raise RuntimeError(errors[0]["message"])


    def get_project(self, title):
        project_id = None
        for p in self.projects:
            if p.title == title:
                project_id = p.id
        if not project_id:
            raise Exception(f"No project '{title}' found in the users project list")
        # We can query the project by the number like
        #     op2 = Operation(Query)
        #     project_query = op2.user(login=user_login).project_v2(number=number)
        # but we will use the query by id here
        op2 = Operation(Query)
        project_query = op2.node(id=project_id).__as__(ProjectV2)
        project_query.__fields__("id", "title")
        fields = project_query.fields(first=100)
        fields.nodes.__as__(ProjectV2SingleSelectField).__fields__("id", "name", "data_type")
        fields.nodes.__as__(ProjectV2Field).__fields__("id", "name", "data_type")
        #fields.nodes.__fields__("name")
        items_query = project_query.items(first=100)  # Adjust the number as needed
        project_item = items_query.nodes.__fields__("id")
        field_value = items_query.nodes.field_values(first=100)
        field_value.nodes.__as__(ProjectV2ItemFieldTextValue).__fields__("text", "field")
        field_value.nodes.__as__(ProjectV2ItemFieldSingleSelectValue).__fields__("name", "field")
        #field_value.nodes.__fields__("text")
        items_query.nodes.__fields__("content")
        items_query.nodes.field_value_by_name(name="Status")
        #project_item.field_values(first=100)
        r = self.execute(op2).node
        print(r)


    def get_repository_issues(self, repository_name : str):
        repo_token = repository_name.strip().split("/")
        if len(repo_token) == 1:
            owner = self.user_login
        if len(repo_token) == 2:
            owner = self.user_login
            repository_name = repo_token[1]
        if len(repo_token) > 2:
            raise Exception("Invalid repository name. Expect either 'org/name' or 'name' (for user repositories)")

        op = Operation(Query)
        q = op.repository(owner=owner, name=repository_name)
        q.__fields__("id")
        q.__fields__("name")
        q.issues(first=100)
        r = self.execute(op)
        for i in r.repository.issues.nodes:
            i.repository_id = r.repository.id
        return (r.repository.id, r.repository.issues.nodes)

    def create_issue(self, repository_id, title, body, assignee_ids=None):
        if assignee_ids == None:
            assignee_ids = [self.user_id]
        op = Operation(Mutation)
        input = CreateIssueInput(title=title, body=body, assignee_ids=assignee_ids, repository_id=repository_id)
        q = op.create_issue(input=input).issue()
        q.__fields__("id")
        q.__fields__("url")
        r = self.execute(op)
        return r

    def reopen_issue(self, issue_id):
        op = Operation(Mutation)
        input = ReopenIssueInput(issue_id = issue_id)
        q = op.reopen_issue(input=input).issue()
        q.__fields__("id")
        q.__fields__("url")
        r = self.execute(op)
        return r

    def close_issue(self, issue_id):
        op = Operation(Mutation)
        input = CloseIssueInput(issue_id = issue_id)
        q = op.close_issue(input=input).issue()
        q.__fields__("id")
        q.__fields__("url")
        r = self.execute(op)
        return r

    def update_issue(self, issue_id : str, body = NoUpdate, title = NoUpdate):
        update_dict : dict
        update_dict = {}
        update_dict['id'] = issue_id
        if body != NoUpdate:
            update_dict['body'] = body
        if title != NoUpdate:
            update_dict['title'] = title
        op = Operation(Mutation)        
        input = UpdateIssueInput(update_dict)
        q = op.update_issue(input=input).issue()
        q.__fields__("id")
        q.__fields__("url")
        r = self.execute(op)
        return r