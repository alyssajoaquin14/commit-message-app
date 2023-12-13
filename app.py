import requests
import streamlit as st
import openai
from github import Github

openai.api_key = st.secrets["OPENAI_API_KEY"]
correct_password = st.secrets["password"]

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
        # commit_sha1 - older commit, commit_sha2 - newer commit
        commit_sha1, commit_sha2 = commits_info[i + 1][0], commits_info[i][0]

        # Make request to GitHub REST API to get diff
        url = f"https://api.github.com/repos/{username}/{repo_name}/compare/{commit_sha1}...{commit_sha2}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
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
    llm_commit_messages = []

    for i in range(min(len(original_commit_messages), len(diffs))):
        # Construct a prompt with the original commit message and diff content
        prompt = f"Original Commit Message: {original_commit_messages[i]}\nDiff:\n{diffs[i]}\nImprove the commit message:"

        # Generate new commit message
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a commit message assistant."},
                {"role": "user", "content": f"{prompt}\n"}
            ]
        )
            
        generated_better_message = response.choices[0].message.content.strip()
            
        llm_commit_messages.append(generated_better_message)

    
    return llm_commit_messages


def main():

    password = st.text_input("Enter the password:", type="password")

    if st.button("Submit"):

        if password == correct_password:
            
            st.success("Correct password! Access granted.")

            st.title("Github Commit Message Generator")

            repo_link = st.text_input("Enter Github repo link")

            if st.button("Generate better commit messages"):
                commits_info, diffs = get_commit_history_and_diffs(repo_link)
                # separate messages from the info
                original_commit_messages = [commit_info[1] for commit_info in commits_info]
                
                better_commit_messages = generate_better_commit_messages(original_commit_messages, diffs)
                col1, col2 = st.columns(2)
                for i in range(min(len(original_commit_messages), len(better_commit_messages))):
                    with col1:
                        st.write(f"Original Commit Message: {original_commit_messages[i]}\n")
                    with col2:
                        st.write(f"Generated Commit Messages: {better_commit_messages[i]}\n")
        
        elif password == "":
            pass
        
        else:
            st.error("Incorrect password. Please try again.")

if __name__ == "__main__":
    main()
