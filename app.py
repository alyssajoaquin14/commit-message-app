import requests
import streamlit as st
import openai
import json
from github import Github

openai.api_key = st.secrets["OPENAI_API_KEY"]
github_token = st.secrets["token"]

def get_commit_history_and_diffs(repo_link):
    # Extract username and repo name from link
    username, repo_name = extract_username_and_repo(repo_link)

    g = Github(github_token)

    # Get repository
    repo = g.get_repo(f"{username}/{repo_name}")

    # Get commit history
    commits_info = [(commit.sha, commit.commit.message) for commit in repo.get_commits()]

    # Get commit diffs
    diffs = []
    for i in range(len(commits_info) - 1):
        # commit_sha1 - older commit, commit_sha2 - newer commit
        commit_sha1, commit_sha2 = commits_info[i + 1][0], commits_info[i][0]

        # Make request to GitHub REST API to get diff
        url = f"https://api.github.com/repos/{username}/{repo_name}/compare/{commit_sha1}...{commit_sha2}"
        headers = {"Accept": "application/vnd.github.v3.diff",
                   "Authorization": f"Bearer {github_token}"}
        
        response = requests.get(url, headers=headers)

        # Check if request was successful
        if response.status_code == 200:
            diff_content = response.text
            diffs.append(diff_content)
        else:
            print(f"Failed to retrieve diff for commits {commit_sha1} and {commit_sha2}")

    return commits_info, diffs


def extract_username_and_repo(repo_link):
    
    parts = repo_link.strip("/").split("/")
    username, repo_name = parts[-2], parts[-1]
    
    return username, repo_name


def generate_better_commit_messages(g, repo_link, commits_info, diffs):
    #generated_detailed_messages = []
    # separate messages from the info
    original_commit_messages = [commit_info[1] for commit_info in commits_info]

    for i in range(min(len(original_commit_messages), len(diffs))):
        # Construct a prompt with the original commit message and diff content
        commit_sha = commits_info[i][0]
        prompt = f"Original Commit Message: {original_commit_messages[i]}\nDiff:\n{diffs[i]}\nImprove the commit message:"

        # call model with user query and functions
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a commit message assistant. Generate one short and one detailed commit message, in present tense."},
                {"role": "user", "content": f"{prompt}\n"}
            ],
            functions=[
                {
                    "name": "new_commit_messages",
                    "description": "List of commit messages.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "original_message": {
                                "type": "string",
                                "description": "The original commit message"
                            },
                            "short_message": {
                                "type": "string",
                                "description": "An improved short commit message"
                            },
                            "detailed_message": {
                                "type": "string",
                                "description": "An improved detailed commit message"
                            }
                        },
                        "required": ["short_message", "detailed_message"]
                    }
                }
            ],
            function_call={"name": "new_commit_messages"}
        )
        # load as a JSON object
        json_response = json.loads(response.choices[0].message.function_call.arguments)
        # write to streamlit app
        st.json(json_response)

        # append detailed message to list
        #generated_detailed_messages.append(json_response["detailed_message"])

        # update commit message
        update_commit_messages(g, repo_link, commit_sha, json_response["detailed_message"])        
    


def update_commit_messages(g, repo_link, commit_sha, new_message):
    username, repo_name = extract_username_and_repo(repo_link) 
    repo = g.get_repo(f"{username}/{repo_name}")

    # get the commit
    commit = repo.get_commit(sha=commit_sha)

    # get tree associated with commit
    commit_tree = repo.get_git_tree(commit_sha)

    # get parent commit(s)
    parents = [repo.get_commit(sha=parent_sha) for parent_sha in commit.parents]

    # create new commit with new message
    repo.create_git_commit(
        message=new_message,
        author={
            "name": commit.commit.author.name,
            "email": commit.commit.author.email,
        },
        committer={
            "name": commit.commit.committer.name,
            "email": commit.commit.committer.email,
        },
        tree=commit_tree,
        parents=parents,
    )

    # update reference to point to new commit
    repo.get_git_ref(f"heads/{repo.default_branch}").edit(
        sha=commit, force=True
    )


def main():
   
    st.title("Github Commit Message Generator")

    repo_link = st.text_input("Enter Github repo link")

    placeholder = st.empty()
    btn = placeholder.button("Generate better commit messages", disabled=False, key="1")
    
    
    # if generate button
    if btn:
        # disable button
        placeholder.button("Generate better commit messages", disabled=True, key="2" )

        with st.spinner("Generating messages. Please wait..."):
             # Integrate github API object
            g = Github(github_token)

            commits_info, diffs = get_commit_history_and_diffs(repo_link)
            # separate messages from the info
            #original_commit_messages = [commit_info[1] for commit_info in commits_info]
                    
            generate_better_commit_messages(g, repo_link, commits_info, diffs)

        st.write("exited spinner") 
        st.success("Commit messages updated successfully!")   
        # re-enable button
        placeholder.button("Generate better commit messages", disabled=False, key="3")
    

if __name__ == "__main__":
    main()
