# do not use with bad intentions i do not encourage any api abuse using this
import asyncio
import base64
import time

import aiohttp

#IMPORTANT
GITHUB_USERNAME = ""
GITHUB_TOKEN = ""
NUMBER_OF_REPOS = 100
COMMITS_PER_REPO = 1
#IMPORTANT








headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "aiohttp-client",
}


async def handle_rate_limit(resp):
    if resp.status == 403:
        data = await resp.json()
        msg = data.get("message", "")
        if "secondary rate limit" in msg.lower():
            retry_after = resp.headers.get("Retry-After")
            wait_time = int(retry_after) if retry_after else 60
            print(f"⚠️ Secondary rate limit hit. Sleeping for {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            return True
    return False


async def create_repo(session, repo_name):
    url = "https://api.github.com/user/repos"
    payload = {
        "name": repo_name,
        "private": False,
        "description": "github.com/JinxedUp MADE THIS",
        "auto_init": False,
    }

    for attempt in range(5):
        async with session.post(url, json=payload) as resp:
            if resp.status == 201:
                print(f"✅ Created repo: {repo_name}")
                return True
            elif await handle_rate_limit(resp):
                continue  # retry after sleep
            else:
                text = await resp.text()
                print(f"❌ Repo create error: {resp.status} {text}")
                return False
    print(f"❌ Repo create error: exceeded retries for {repo_name}")
    return False


async def create_initial_commit(session, repo):
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo}/contents/README.md"
    payload = {
        "message": "Initial commit",
        "content": base64.b64encode(b"# Auto Repo\n").decode("utf-8"),
        "branch": "main",
    }

    for attempt in range(5):
        async with session.put(url, json=payload) as resp:
            if resp.status == 201:
                return True
            elif await handle_rate_limit(resp):
                continue
            else:
                text = await resp.text()
                print(f"❌ Initial commit error ({repo}): {resp.status} {text}")
                return False
    return False


async def add_commit(session, repo, message, content):
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo}/contents/README.md"

    for attempt in range(5):
        async with session.get(url) as get_resp:
            if get_resp.status == 200:
                data = await get_resp.json()
                sha = data["sha"]
                old_content = base64.b64decode(data["content"]).decode("utf-8")
                new_content = old_content + f"\n{content}"
            elif await handle_rate_limit(get_resp):
                await asyncio.sleep(2)
                continue
            else:
                print(f"❌ Failed to fetch README for {repo}")
                return False

        payload = {
            "message": message,
            "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
            "sha": sha,
            "branch": "main",
        }
        async with session.put(url, json=payload) as put_resp:
            if put_resp.status == 200:
                return True
            elif await handle_rate_limit(put_resp):
                continue
            else:
                text = await put_resp.text()
                print(f"❌ Commit error ({repo}): {put_resp.status} {text}")
                return False
    return False


import asyncio


async def process_repo(session, index):
    repo_name = f"api-repo-{index}"
    if await create_repo(session, repo_name):
        if await create_initial_commit(session, repo_name):
            for j in range(COMMITS_PER_REPO):
                msg = f"Update {j + 1}"
                line = f"Contribution line {j + 1} at {time.ctime()}"
                success = await add_commit(session, repo_name, msg, line)
                if success:
                    print(f"✅ Commit {j + 1} to {repo_name}")
                else:
                    print(f"❌ Commit failed to {repo_name}")
    await asyncio.sleep(5)


async def main():
    conn = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(headers=headers, connector=conn) as session:
        tasks = [process_repo(session, i) for i in range(1, NUMBER_OF_REPOS + 1)]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    print(f"\n🚀 All done in {time.time() - start:.2f} seconds")
