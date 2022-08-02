import re

from fastapi import FastAPI, Form, Request
from fastapi.templating import Jinja2Templates
from gitea import Gitea
from github import Github, Repository

app = FastAPI()
templates = Jinja2Templates(directory="templates/")


async def make_github_msg(repo: Repository) -> str:
    forks = f"{repo.forks_count} fork{'s' if repo.forks_count != 1 else ''}"
    issues = (
        f"{repo.open_issues_count} issue{'s' if repo.open_issues_count != 1 else ''}"
    )
    full_name = repo.full_name
    return (
        f"Found {full_name} ({forks}, {issues}) on Github, now trying to clone it...\n"
    )


async def new_repo(url: str) -> str:
    msg = ""
    url = url.replace(" ", "")
    result = re.match(r"https://github.com/(\w*)/(\S*)", url)

    if result is None:
        return "Could not parse URL"

    # Get the owner and repo name
    github_username = result.group(1)
    github_repo = result.group(2)
    print(f"Github Username: {github_username}")
    print(f"Github Repo: {github_repo}")

    github_token = open(".github_token", "r").read().strip()
    github = Github(github_token)
    repo = github.get_repo(f"{github_username}/{github_repo}")

    repo_msg = await make_github_msg(repo)
    msg = msg + repo_msg

    gitea_token = open(".gitea_token", "r").read().strip()
    gitea = Gitea("https://git.lovinator.space", gitea_token, log_level="DEBUG")
    orgs = gitea.get_orgs()
    print(f"Gitea orgs: {orgs}")

    if github_username not in [org.username for org in orgs]:
        gitea_org = gitea.create_org(
            owner=gitea.get_user(),
            orgName=github_username,
            description="User is archived from Github.",
            website=f"https://github.com/{github_username}",
        )
        print(f"Gitea new org: {gitea_org}")
        msg = msg + f"Created new Gitea org for {github_username}...\n"

    gitea.create_repo(
        repoOwner=gitea_org,
        repoName=github_repo,
        description=repo.description,
        website=repo.html_url,
        autoInit=False,
        mirror=True,
    )

    return msg


@app.get("/")
async def get_index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        context={"request": request},
    )


@app.post("/")
async def post_index(request: Request, repository: str = Form(...)):
    result = await new_repo(repository)

    return templates.TemplateResponse(
        "index.html",
        context={"request": request, "result": result},
    )
