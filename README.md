# Saagie Jenkins

Saagie Jenkins is a command-line tool used to manage Jenkins. It utilizes the current git and Kubernetes context in some cases to retrieve environment and branch names.

---

## Requirements

Ensure Python 3.9 and pip 3.9 are installed:

* Linux:
    ```shell
    sudo apt update
    sudo apt install python3.9 python3.9-venv

    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    sudo python3.9 get-pip.py
    ```

* MacOS:
    ```bash
    brew install python@3.9
    ```

---

## Installation Steps

1. Unzip the `jks-x.x.zip` archive in your terminal:
    ```shell
    unzip /path-to/jks-x.x.x.zip -d ~/.jks
    ```
2. Navigate to the unzipped directory and create a `.jks-env` file:
    ```shell
    cd ~/.jks
    touch .jks-env
    ```
3. Populate the `.jks-env` file with the following content:
    ```plaintext
    [JENKINS]
    ServerUrl = jenkinsUrl
    ApiKey = ApiKey
    Username = username

    [GITLAB]
    ServerUrl = https://gitlab.com
    ApiKey = ApiKey

    [SLACK]
    UserId = UserId
    ```
    > To get your Jenkins API Key: Go to <https://jenkins.devtools.saagie.tech/user/YOUR_ID/configure> and create a token
    > To get your Gitlab API Key: Go to <https://gitlab.com/-/profile/personal_access_tokens> and create a token
    > To get your Slack ID: Go to your Slack profile and look for the option that allows you to view or copy your member ID.
4. Install required dependencies:
    ```shell
    python3.9 install -r requirements.txt
    ```
5. Create an Alias in your terminal configuration file
    ```shell
    alias jks="python3.9 ~/.jks/jks.py"
    ```

---

## Arguments

|Arguments                     |Default                        | Description                                                    | Comments                                                               |
|------------------------------|-------------------------------|----------------------------------------------------------------|------------------------------------------------------------------------|
| `-v, --version`              |                               | Display program version                                        |                                                                        |
|`-c, --cron`                  |                               | Setting up a Jenkins cron                                      |                                                                        |
|`-mr, --open-mr`              |                               | Open an MR specified by card ID.                               |                                                                        |
|`-e, --env`                   |Current                        | Set environment.                                               |                                                                        |
|`-b, --build`                 |Current                        | Build current or specific branch.                              |                                                                        |
|`-d, --deploy`                |Current                        | Deploy current or specific branch.                             |                                                                        |
|`-s, --start`                 |Current                        | Start an environment with current or specific branch.          |                                                                        |
|`-rm, --remove`               |Current                        | Remove an environment with current or specific envId           |                                                                        |
|`-tt, --test-types`           |Current                        | Tests to run after test creation (UI|API|APIv2|All)            |                                                                        |
|`-iid, --installation_id`     |saagie                         | A short name. In lower case only.                              |                                                                        |
|`-gamr, --get-assigned-mr`    |                               | Get assigned MR with less than 2 upvotes                       |                                                                        |
|`-kv, --kubernetes-version`   |                               | Set a custom kubernete version                                 |                                                                        |

---

## Exemples

* Open an merge request
    ```bash
    jks -mr id_of_your_ticket
    ```

* Setting up a cron (experimental)
    ```bash
    jks -c '*/5 * * * *' -s -d -b
    jks -c '*/5 * * * *' -s -e dev1234
    jks -c '*/5 * * * *' -s story/1234 -d story/1234 -b story/1234
    ```

* Deploy
    ```bash
    # Deploy current branch and current env
    jks -d

    # Deploy current branch on a custom env
    jks -d -e dev1234

    # Deploy a custom branch
    jks -d story/1234

    # Deploy with a custom kubernetes version
    jks -d -kv 1.26

    # Deploy with a custom installation id
    jks -d -iid saagie

    # Deploy with test types
    jks -d -tt UI,API,APIv2,ALL

    # Deploy with full customization
    jks -d story/123 -e dev123 -kv 1.26 -tt UI,API,APIv2,ALL --iid saagie
    ```

* Start
    ```bash
    # Start current env with a current branch
    jks -s

    # Start current env with a custom branch
    jks -s story/1234

    # Start a custom env with current branch
    jks -s -e dev1234

    # Start with full customization
    jks -s story/1234 -e dev1234
    ```

* Remove
    ```bash
    # Remove current env
    jks -rm

    # Remove custom env
    jks -rm -e dev1234
    ```

* Build
    ```bash
    # Build current branch
    jks -b

    # Build a custom branch
    jks -b story/1234
    ```

* Get assigned MR
    ```bash
    jks -gamr
    ```
