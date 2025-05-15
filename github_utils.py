# Goal of this function:
# To download a CSV file from your GitHub repo, and load it into a pandas DataFrame — or return a blank DataFrame if the file doesn't exist.

def load_df_from_github(repo, path, token):
    import requests
    from io import StringIO
    import pandas as pd
    import time

    # Add a fake query param to bust HTTP caching
    timestamp = int(time.time())
    url = f"https://raw.githubusercontent.com/{repo}/main/{path}?nocache={timestamp}"
    
    headers = {"Authorization": f"token {token}"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return pd.read_csv(StringIO(response.text))
    else:
        return pd.DataFrame(columns=["short_name", "Adjustment", "Analyst Comment"])

#This defines the function with 3 parameters:
#repo: Your GitHub repo name, like "kaimin86/credit-rating-deploy"
#path: The path to the CSV file inside your repo, e.g. "overrides/USA_2024.csv"
#token: Your GitHub personal access token, used to authenticate

#This function safely:
#Downloads your override CSV from GitHub
#Returns a usable DataFrame
#Falls back to a blank frame if the file doesn’t exist yet

#requests → makes the web request to GitHub
#StringIO → treats text like a file (so pandas can read it)
#pandas → to parse the CSV
#Even though you're likely importing these at the top of the file too, having them here makes the function more self-contained

#This builds the URL to the raw file on GitHub.
#URL becomes: https://raw.githubusercontent.com/kaimin86/credit-rating-deploy/main/overrides/USA_2024.csv
#This is a direct public URL to the raw file content.

#This sets the header to include your GitHub token.
#Even if your repo is public, this makes it more secure and avoids any rate limits from GitHub.

#Makes a GET request to fetch the CSV file from GitHub.
#If the file exists → you get a 200 response and file content
#If the file doesn’t exist → you get a 404

#Checks if the file was successfully found and loaded
# If it exists, it:
#Turns the text content into a file-like object (StringIO)
#Loads it as a DataFrame with pd.read_csv(...)
#Returns the resulting DataFrame

#If the file does not exist (404 error), return an empty DataFrame with the right column structure — so the rest of your app won’t crash.

#Special Note: In the middle of the code. I had to tweak the URL because of the time taken for Github to push/pull edits
#It adds a "fake" query parameter (?nocache=timestamp) to your GitHub raw file URL to bypass HTTP caching.
#when you request https://raw.githubusercontent.com/kaimin86/credit-rating-deploy/main/overrides/USA_2024.csv
#Streamlit Cloud (or requests) might reuse a cached version — especially if it just downloaded that URL seconds ago.
#Even if the GitHub file was updated, your app may still see the "old" version from memory or a CDN.
#url = f"https://raw.githubusercontent.com/{repo}/main/{path}?nocache={int(time.time())}" --> what we do instead
#Every time you reload, the nocache value changes (based on time)
#This tricks GitHub/CDN/requests into treating it as a new URL
#Result: you always get the freshest version of the override file

# Goal of this function:
# Uploads a pandas DataFrame to a GitHub repository as a CSV file.
# If the file already exists, it will be updated (overwrite).

#Parameters:
#df: The DataFrame to upload
#repo: GitHub repo in the format 'username/repo-name'
#path: Path to save the file in the repo, e.g., 'overrides/USA_2024.csv'
#commit_message: The commit message to show in GitHub
#token: GitHub personal access token (ideally from st.secrets)

#Returns:
#True if successful, False otherwise

def push_df_to_github(df, repo, path, commit_message, token):
    import base64
    import requests
    import time

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    csv_string = df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_string.encode()).decode()

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)
    sha = response.json().get("sha") if response.status_code == 200 else None

    data = {
        "message": commit_message,
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    put_response = requests.put(url, headers=headers, json=data)

    if put_response.status_code in (200, 201):
        return True
    else:
        print("Error pushing to GitHub:", put_response.json())
        return False


#Build the API URL for the file.
#If you’re saving to kaimin86/credit-rating-deploy, and path = overrides/USA_2024.csv,
#then this URL becomes: https://api.github.com/repos/kaimin86/credit-rating-deploy/contents/overrides/USA_2024.csv

#Convert the DataFrame into CSV format (as a plain text string).
#index=False omits the row numbers.

#GitHub's API requires file contents to be base64-encoded.
#Converts the string to bytes
#Encodes the bytes in base64
#Decodes it back to a string (to include in the JSON payload)

#Build the request headers:
#Authorization: your GitHub token to prove you have write access
#Accept: tells GitHub which version of their API you want

#Try to fetch the file in case it already exists.
#Why? Because GitHub needs the file’s SHA if you're updating it.

#If the file exists, grab its SHA.
#You need this to tell GitHub: "I want to overwrite this exact file."
#If the file doesn’t exist yet (e.g., first save), sha will be None.

#Build the JSON payload to send to GitHub:
#"message": commit message (appears in repo history)
#"content": your CSV, in base64 format
#"branch": which branch to push to (usually "main")

#If you're overwriting an existing file, include its SHA.
#GitHub requires this to avoid accidental overwrites or conflicts.

#Send a PUT request to GitHub with the payload.
#This either: Creates the file (if it didn’t exist) or Overwrites it (if it did)

#Return True if:
#201: file was created
#200: file was updated
#Otherwise, return False.

#one minor edit at the end st.rerun() is too fast. It takes time to send and the new analyst input data to Github and get it updated
#Add time.sleep(1.5) before rerun to see freshest output

## Special note on token: This is specially generated by Github and unique to this particular repository
## saved in a secrets.toml file that streamlit recognizes
## Do this as you dont want unauthorized read/write to your app and code base

# Goal of this function:
# Only allows re run once github properly updates
# Helps my analyst see fresh updated data once they click save. else it was showing stale data

def wait_for_override_to_update(repo, path, token, df_before, max_retries=10):
    
    import time
    import pandas as pd
    
    """
    Polls GitHub until the override file visibly changes from its prior state.
    Returns True if update detected, False if timed out.
    """
    for attempt in range(max_retries):
        time.sleep(1)

        df_after = load_df_from_github(repo, path, token)
        if not df_after.equals(df_before):
            return True  # Detected update

    return False  # Timeout