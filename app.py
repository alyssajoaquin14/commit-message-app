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


def generate_better_commit_messages(original_commit_messages, diffs):
    #llm_commit_messages = []
    #json_commit_messages = []

    for i in range(min(len(original_commit_messages), len(diffs))):
        # Construct a prompt with the original commit message and diff content
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
        
        st.json(json_response)
        
        #json list
        #json_commit_messages.append(json_response)

        #generated_better_message = response.choices[0].message.content.strip()
            
        #llm_commit_messages.append(generated_better_message)

    
    #return llm_commit_messages

    
def main():
   
    st.title("Github Commit Message Generator")

    repo_link = st.text_input("Enter Github repo link")

    # initialize session state
    if "button_state" not in st.session_state:
        st.session_state.button_state = "enabled"

     # Enable or disable the button based on the session state
    generate_button_enabled = st.button("Generate better commit messages", key="generate_button", on_click=None)

    if generate_button_enabled:
        # disable button
        st.session_state.button_state = "disabled"
        st.button("Generating messages. Please wait...", key="generate_button_disabled", on_click=None, help="Please Wait")

        with st.spinner("Generating messages. Please wait..."):
            commits_info, diffs = get_commit_history_and_diffs(repo_link)
            # separate messages from the info
            original_commit_messages = [commit_info[1] for commit_info in commits_info]
                    
            generate_better_commit_messages(original_commit_messages, diffs)
            
        # re-enable button
        st.session_state.button_state = "enabled"


if __name__ == "__main__":
    main()
