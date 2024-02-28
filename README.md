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
    pip3.9 install -r requirements.txt
    ```
5. Create an Alias in your terminal configuration file
    ```shell
    alias jks="python3.9 ~/.jks/jks.py"
    ```

---

## Arguments

| Arguments             | Description                  |
| :-------------------- | :--------------------------- |
| `start`               | start a GKE environment      |
| `create`              | create a GKE environment     |
| `drop`                | drop a GKE environment       |
| `cron`                | create a Jenkins cron        |
| `build`               | build product                |
| `open_mr`             | open a new MR                |
| `get_assigned_mr`     | Get a list of assigned MR    |
| `ask_validation`      | Ask validation (tests or PM) |
| `test`                | Run test on GKE environment  |

### Start Arguments

| Arguments             | Description                                                    |
| :-------------------- | :------------------------------------------------------------- |
| `-b, --branch`        | Branch name (if not specify use current branch)                |
| `-e, --env`           | GKE environment name (if not specify use current environment)  |

### Create Arguments

| Arguments                      | Description                                                                                                          |
| :----------------------------- | :------------------------------------------------------------------------------------------------------------------- |
| `-b, --branch`                 | Branch name (if not specify use current branch)                                                                      |
| `-e, --env`                    | GKE environment name (if not specify use current environment)                                                        |
| `-iid, --installation-id`      | A short name. In lower case only. (if not specify use current `saagie`)                                              |
| `-kv, --kubernetes-version`    | Set a custom kubernete version                                                                                       |
| `-tt, --test-types`            | Tests to run after test creation (UI / API / APIv2 / All)                                                            |
| `-p, --product_version`        | Use a specify product version                                                                                        |
| `-a, --auth`                   | Auth_mechanism: Which authentication mechanism to deploy (default: keycloak), [ldap, keycloak, freeipa, sso]         |
| `-f, --features`               | Features Comma-separated list of features to enable or disable (e.g.  "gpu", "external_ui_lib", "openai", "kyverno") |

### Drop Arguments

| Arguments             | Description                                                    |
| :-------------------- | :------------------------------------------------------------- |
| `-e, --env`           | GKE environment name (if not specify use current environment)  |

### Cron Arguments

| Arguments             | Description                |
| :-------------------- | :------------------------- |
| `start`               | start a GKE environment    |
| `create`              | create a GKE environment   |
| `build`               | build product              |

#### Cron Start Arguments

| Arguments                      | Required | Description                                                    |
| :----------------------------- | :------- | :------------------------------------------------------------- |
| `-f, --format`                 | true     | Setting up a Jenkins cron                                      |
| `-b, --branch`                 | false    | Branch name (if not specify use current branch)                |
| `-e, --env`                    | false    | GKE environment name (if not specify use current environment)  |

#### Cron Create Arguments

| Arguments                      | Required | Description                                                              |
| :----------------------------- | :------- | :----------------------------------------------------------------------- |
| `-f, --format`                 | true     | Setting up a Jenkins cron                                                |
| `-b, --branch`                 | false    | Branch name (if not specify use current branch)                          |
| `-e, --env`                    | false    | GKE environment name (if not specify use current environment)            |
| `-iid, --installation-id`      | false    | A short name. In lower case only. (if not specify use current `saagie`)  |

#### Cron Build Arguments

| Arguments                      | Required | Description                                      |
| :----------------------------- | :------- | :----------------------------------------------- |
| `-f, --format`                 | true     | Setting up a Jenkins cron                        |
| `-b, --branch`                 | false    | Branch name (if not specify use current branch)  |

### Build Arguments

| Arguments                      | Description                                      |
| :----------------------------- | :----------------------------------------------- |
| `-b, --branch`                 | Branch name (if not specify use current branch)  |

#### Open MR Arguments

| Arguments         | Required | Description                                      |
| :---------------- | :------- | :----------------------------------------------- |
| `-c, --card`      | true     | A Jira Card ID                                   |
| `-b, --branch`    | false    | Branch name (if not specify use current branch)  |

#### Get Assigned MR Arguments

No args

#### Ask Validation Arguments

TODO

#### Test Arguments

TODO

---

## Exemples

* Open an merge request
    ```bash
    jks open_mr -c id_of_your_ticket
    ```

* Setting up a cron (experimental)
    ```bash
    jks cron start -f '*/5 * * * *'
    jks cron start -f '*/5 * * * *' -b story/1234 -e dev1234
    ```

* Create / Deploy
    ```bash
    # Deploy current branch and current env
    jks create

    # Deploy current branch on a custom env
    jks create -e dev1234

    # Deploy a custom branch
    jks create -b story/1234

    # Deploy with a custom kubernetes version
    jks create -kv 1.26

    # Deploy with a custom installation id
    jks create -iid saagie

    # Deploy with test types
    jks create -tt UI,API,APIv2,ALL

    # Deploy with full customization
    jks create -b story/123 -e dev123 -kv 1.26 -tt UI,API,APIv2,ALL --iid saagie
    ```

* Start
    ```bash
    # Start current env with a current branch
    jks start

    # Start current env with a custom branch
    jks start story/1234

    # Start a custom env with current branch
    jks start -e dev1234

    # Start with full customization
    jks start -b story/1234 -e dev1234
    ```

* Remove
    ```bash
    # Remove current env
    jks drop

    # Remove custom env
    jks drop -e dev1234
    ```

* Build
    ```bash
    # Build current branch
    jks build

    # Build a custom branch
    jks build -b story/1234
    ```

* Get assigned MR
    ```bash
    jks get_assigned_mr
    ```
