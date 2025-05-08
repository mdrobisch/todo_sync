import json
import asyncio
from github_client.client import Client
from github_client.custom_queries import Query
sync_config : dict
sync_config = json.load(open("sync_config.json", "r"))


async def fetch_user_data():
    client = Client("https://example.com/graphql", {"Authorization": f"Bearer {sync_config.get("global_github_token")}"})

    query = Query()
    query = query.user(login="mdrobisch").fields("login", "name", "bio", "url")
    r = await client.execute(query)
    print(r)

asyncio.run(fetch_user_data())
