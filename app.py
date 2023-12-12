from github import Github

def get_commit_history_and_diffs(repo_link):
    # Extract username and repo name from link
    username, repo_name = extract_username_and_repo(repo_link)

    g = Github()

    # Get repository
    repo = g.get_repo(f"{username}/{repo_name}")

    # Get commit history
    commits_info = [(commit.sha, commit.commit.message) for commit in repo.get_commits()]

    # Get commit diffs
    diffs = []
    for i in range(len(commits_info) - 1):
        diff = repo.compare(commits_info[i + 1][0], commits_info[i][0]).diff
        diffs.append(diff)
    
    return commits_info, diffs


def extract_username_and_repo(repo_link):
    
    parts = repo_link.strip("/").split("/")
    username, repo_name = parts[-2], parts[-1]
    
    return username, repo_name