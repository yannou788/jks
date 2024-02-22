import re
import sys
import time
import gitlab
import jenkins
import logging
import pathlib
import argparse
import subprocess
import configparser
from croniter import croniter
from termcolor import colored
from rich.console import Console
from urllib.parse import quote_plus
from kubernetes import client, config

# Logging
logging.basicConfig(filename='/tmp/jks.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)

# Templates
pipeline_template = """
  <flow-definition plugin="workflow-job@1268.v6eb_e2ee1a_85a">
    <actions>
      <org.jenkinsci.plugins.pipeline.modeldefinition.actions.DeclarativeJobAction plugin="pipeline-model-definition@2.2118.v31fd5b_9944b_5"/>
      <org.jenkinsci.plugins.pipeline.modeldefinition.actions.DeclarativeJobPropertyTrackerAction plugin="pipeline-model-definition@2.2118.v31fd5b_9944b_5">
        <jobProperties/>
        <triggers/>
        <parameters/>
        <options/>
      </org.jenkinsci.plugins.pipeline.modeldefinition.actions.DeclarativeJobPropertyTrackerAction>
    </actions>
    <description/>
    <keepDependencies>false</keepDependencies>
    <properties>
      <com.dabsquared.gitlabjenkins.connection.GitLabConnectionProperty plugin="gitlab-plugin@1.7.5">
        <gitLabConnection>Saagie-gitlab</gitLabConnection>
        <jobCredentialId/>
        <useAlternativeCredential>false</useAlternativeCredential>
      </com.dabsquared.gitlabjenkins.connection.GitLabConnectionProperty>
      <com.sonyericsson.rebuild.RebuildSettings plugin="rebuild@1.34">
        <autoRebuild>false</autoRebuild>
        <rebuildDisabled>false</rebuildDisabled>
      </com.sonyericsson.rebuild.RebuildSettings>
      {cron}
    </properties>
    <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps@3616.vb_2e7168f4b_0c">
      <script>
        {script}
      </script>
      <sandbox>true</sandbox>
    </definition>
    <triggers/>
    <disabled>false</disabled>
  </flow-definition>
"""
cron_template = """
  <org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
    <triggers>
      <hudson.triggers.TimerTrigger>
        <spec>{cron}</spec>
      </hudson.triggers.TimerTrigger>
    </triggers>
  </org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
"""

# Stage templates
start_stage_template = """
  stage('Start') {{
    steps {{
      build job: 'Ondemand/GKE/Start/{branch_name}', parameters: [
        [$class: 'StringParameterValue', name: 'prefix_name', value: '{env_name}' ],
        [$class: 'BooleanParameterValue', name: 'confirm', value: true]
      ]
    }}
  }}
"""
build_stage_template = """
  stage('Build') {{
    steps {{
      build job: 'Product/Build/{branch_name}'
    }}
  }}
"""
deploy_stage_template = """
  stage('Deploy') {{
    steps {{
      build job: 'Ondemand/GKE/Create/{branch_name}', parameters: [
        [$class: 'StringParameterValue', name: 'prefix_name', value: '{env_name}' ],
        [$class: 'BooleanParameterValue', name: 'confirm', value: true],
        [$class: 'BooleanParameterValue', name: 'create_env', value: true],
        [$class: 'BooleanParameterValue', name: 'install_product', value: true]
      ]
    }}
  }}
"""

# Post Build
post_slack_notification = """
  always {{
    script {{
      def message = "Cron: ${{currentBuild.currentResult}} [${{env.JOB_NAME}}]."
      slackSend(color: "white", channel: "@{username}", message: message)
    }}
  }}
"""

def confirm(question):
  answer = ""
  while answer not in ["y", "n"]:
      answer = input(question).lower()
  return answer == "y"

def get_gitlab_user_id(server_url, token):
  try:
    gl = gitlab.Gitlab(server_url, private_token=token)

    gl.auth()

    return gl.user.id
  except Exception as e:
    print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
    logger.error(e)
    sys.exit(1)

def read_config_file(file_path):
  config = configparser.ConfigParser()
  try:
    with open(file_path, 'r') as file:
      config.read_file(file)
      return config
  except Exception as e:
    print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
    logger.error(e)
    sys.exit(1)

def connect_to_jenkins(credentials):
  console = Console()
  with console.status("[bold cyan]Connecting to jenkins...") as status:
    time.sleep(1)
    try:
      server = jenkins.Jenkins(credentials.get('ServerUrl'), username=credentials.get('Username'), password=credentials.get('ApiKey'))
      server.get_whoami()
      return server
    except jenkins.JenkinsException as e:
      print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
      logger.error(e)
      sys.exit(1)

def get_git_branch_name():
  try:
    # Exécuter la commande git pour obtenir le nom de la branche
    result = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('utf-8').strip()
    return result
  except subprocess.CalledProcessError:
    print(f"{colored('[Error]', 'red')} Git branch name not found")
    logger.error('Git branch name not found')
    sys.exit(1)

def get_branch_name(default):
  branch_name = default

  if default == 'current':
    # Get current branch name
    branch_name = get_git_branch_name()

    # Check branch name
    check_git_branch_name(branch_name);

  return branch_name

def check_git_branch_name(branch_name):
  if branch_name is None:
    print(colored('[Error]', 'red') + ' Git branch name not found')
    sys.exit(1)
  elif branch_name == 'master':
    print(colored('[Error]', 'red') + ' You can\'t deploy master branch')
    sys.exit(1)

def check_equal_values(dict):
    # Get all values from dict filter None
    filtered_values = [value for value in dict.values()]

    # Check if all values are equal
    return len(set(filtered_values)) <= 1

# To do : get build progression
def get_build_progresion(server, project_name, build_number):
  console = Console()
  with console.status("[bold green]Waiting...") as status:
    while True:
      queue_info = server.get_queue_item(build_number)

      if queue_info['why'] is None:
        if queue_info['cancelled']:
          print(colored('[Error]', 'red') + ' Build cancelled')
        else:
          print(f"{colored('[Success]', 'green')} {queue_info['executable']['url']}")
        break
      time.sleep(5)

    build_info = server.get_build_info(project_name, queue_info['executable']['number'])
    print(build_info)

def create_pipeline(server, name, env, cron, slack_user_id, type):
  stages = []
  postBuild = [];

  if 'build' in type:
    stages.append(build_stage_template.format(branch_name=quote_plus(type['build']), env_name=env))
  if 'deploy' in type:
    stages.append(deploy_stage_template.format(branch_name=quote_plus(type['deploy']), env_name=env))
  if 'start' in type:
    stages.append(start_stage_template.format(branch_name=quote_plus(type['start']), env_name=env))

  if slack_user_id:
    postBuild.append(post_slack_notification.format(username=slack_user_id))

  script_flow = """
    pipeline {{
      agent any
      stages {{
        {stage}
      }}
      post {{
        {postBuild}
      }}
    }}
  """.format(
      stage='\n'.join(stages),
      postBuild='\n'.join(postBuild)
    ) if stages.__len__() > 0 or postBuild.__len__() > 0 else ''


  cron_flow = cron_template.format(cron=cron) if cron is not None else ''

  template = pipeline_template.format(script=script_flow, cron=cron_flow)

  try:
    server.create_job(f"Playground/test/{re.sub(r'[^a-zA-Z0-9]', '.', name)}", template)
    print(f"{colored('[Success]', 'cyan')} pipeline created: https://jenkins.devtools.saagie.tech/job/Playground/job/test/job/{name}")
  except jenkins.JenkinsException as e:
    print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
    logger.error(e)

def open_mr(card_id, gitlab_user_id, slack_user_id):
  build_number = None

  # Format project name
  project_name = 'Bots/ProductBot/MR_Open_Review'

  # Set build parameters
  parametres_build = {
    'confirm': True,
    'productNumber': card_id,
    'gitlabUserId': gitlab_user_id,
    'username': slack_user_id,
  }

  # Get build number
  try:
    build_number = server.build_job(project_name, parameters=parametres_build)
    print(f"{colored('[Success]', 'cyan')} build number: {build_number}")
  except jenkins.JenkinsException as e:
    print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
    logger.error(e)

def delete_env(server, env_name, slack_user_id = ''):
  build_number = None

  # Format project name
  project_name = f'Ondemand/GKE/Drop'

  parametres_build = {
    'confirm': True,
    'prefix_name': env_name,
    'slackId': slack_user_id,
  }
  
  # Get build number
  try:
    build_number = server.build_job(project_name, parameters=parametres_build)
    print(f"{colored('[Success]', 'cyan')} build number: {build_number}")
  except jenkins.JenkinsException as e:
    print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
    logger.error(e)
  
def start_env(server, branch_name, env_name, show_progression = False, slack_user_id = ''):
  build_number = None

  # Format project name
  project_name = f'Ondemand/GKE/Start/{quote_plus(branch_name)}'

  # Set build parameters
  parametres_build = {
    'confirm': True,
    'prefix_name': env_name,
    'slackId': slack_user_id,
  }

  # Get build number
  try:
    build_number = server.build_job(project_name, parameters=parametres_build)
    print(f"{colored('[Success]', 'cyan')} build number: {build_number}")
  except jenkins.JenkinsException as e:
    print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
    logger.error(e)

  if show_progression:
    get_build_progresion(server, project_name, build_number);

def start_build(server, branch_name, show_progression = False):
  build_number = None

  # Format project name
  project_name = f'Product/Build/{quote_plus(branch_name)}'

  # Get build number
  try:
    build_number = server.build_job(project_name)
    print(f"{colored('[Success]', 'cyan')} build number: {build_number}")
  except jenkins.JenkinsException as e:
    print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
    logger.error(e)

  if show_progression:
    get_build_progresion(server, project_name, build_number);

def askValidation(server, validation_type, prefix_name, show_progression = False, slack_user_id = ''):
  build_number = None

  # Format project name
  project_name = f'Bots/ProductBot/Update_Story_Validation_Status'

  parametres_build = {
    'confirm': True,
    'cardId': prefix_name,
    'validationType': validation_type,
    'validationState': 'todo',
    'username': slack_user_id,
  }
  
  # Get build number
  try:
    build_number = server.build_job(project_name, parameters=parametres_build)
    print(f"{colored('[Success]', 'cyan')} build number: {build_number}")
  except jenkins.JenkinsException as e:
    print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
    logger.error(e)

  if show_progression:
    get_build_progresion(server, project_name, build_number);

def deploy(server, branch_name, prefix_name, show_progression = False, slack_user_id = '', test_types = [], installation_id = 'saagie', kubernetes_version = ''):
  build_number = None

  # Format project name
  project_name = f'Ondemand/GKE/Create/{quote_plus(branch_name)}'

  parametres_build = {
    'confirm': True,
    'create_env': True,
    'install_product': True,
    'prefix_name': prefix_name,
    'slackId': slack_user_id,
    'test_types': ','.join(test_types),
    'installationId': installation_id,
    'kubernetes_version': kubernetes_version
  }

  # Get build number
  try:
    build_number = server.build_job(project_name, parameters=parametres_build)
    print(f"{colored('[Success]', 'cyan')} build number: {build_number}")
  except jenkins.JenkinsException as e:
    print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
    logger.error(e)

  if show_progression:
    get_build_progresion(server, project_name, build_number);

if __name__ == "__main__":

  parser = argparse.ArgumentParser(
    prog='Saagie Jenkins',
    description='Use jenkins from command line',)

  # Arguments
  parser.add_argument('-v', '--version', action='version', version='%(prog)s 2.3.1')
  parser.add_argument('-c', '--cron', type=str, help='Set cron')
  parser.add_argument('-mr', '--open-mr', type=int, help='Open MR specified by card id')
  parser.add_argument('-ask', '--ask-validation', type=str, nargs='+', choices=['tests', 'pm', 'ux', 'secu'], help='Ask validation (tests|pm|ux|secu)')
  parser.add_argument('-tt', '--test-types', type=str, default=[], nargs='+', choices=['UI', 'API', 'APIv2', 'All'], help='Tests to run after deployement (UI|API|APIv2|All)')
  parser.add_argument('-cid', '--card-id', type=str, help='Specify a card ID')
  parser.add_argument('-rm', '--remove', const='current', nargs='?', type=str, help='Environment')
  parser.add_argument('-iid', '--installation-id', default='saagie', const='saagie', nargs='?', type=str, help='Installation Id')
  parser.add_argument('-e', '--env', default='current', const='current', nargs='?', type=str, help='Environment')
  parser.add_argument('-b', '--build', const='current', nargs='?', type=str, help='Build current or specific branch')
  parser.add_argument('-d', '--deploy', const='current', nargs='?', type=str, help='Deploy current or specific branch')
  parser.add_argument('-s', '--start', const='current', nargs='?', type=str, help='Start an env with current or specific branch')
  parser.add_argument('-kv', '--kubernetes-version', default='', nargs='?', type=str, help='Set a custom kubernete version')
  parser.add_argument('-gamr', '--get-assigned-mr', action='store_true', help='Start an env with current or specific branch')

  args = parser.parse_args()

  # Read config file
  config_file_path = f"{pathlib.Path(__file__).parent.resolve()}/.jks-env"
  custom_config = read_config_file(config_file_path)

  # Connect to jenkins
  server = connect_to_jenkins(custom_config['JENKINS'])

  # Clear installation id
  args.installation_id = re.sub('[^A-Za-z0-9]+', '', args.installation_id)
  
  # Get env name
  env = None
  if args.env:
    env = args.env
    if args.env == 'current':
      env = config.list_kube_config_contexts()[1]['context']['cluster'].split('_')[-1] if config.list_kube_config_contexts() else None
  
  if args.open_mr:
    # Get gitlab user id
    gitlabUserId = get_gitlab_user_id(custom_config['GITLAB']['ServerUrl'], custom_config['GITLAB']['ApiKey']);

    print(f"{colored('[MR]', 'cyan')} Open MR for cardId: {colored(args.open_mr, 'green')}")

    if confirm(f"{colored('Are you sure [Y/N]? ', 'light_blue', attrs=['bold'])}"):
      open_mr(args.open_mr, gitlabUserId, custom_config['SLACK']['UserId']);
  elif args.get_assigned_mr:
    print(f"{colored('[Get Assigned MR]', 'cyan')}")

    try:
      gl = gitlab.Gitlab(custom_config['GITLAB']['ServerUrl'], private_token=custom_config['GITLAB']['ApiKey'])

      gl.auth()

      # Get merge requests that i'm a reviewer
      merge_requests = gl.mergerequests.list(reviewer_id=gl.user.id)

      merge_requests_without_thumbs_up = [mr for mr in merge_requests if mr.upvotes < 2]

      for mr in merge_requests_without_thumbs_up:
        print(f"Merge Request: {mr.title}")
        print(f"Link: {mr.web_url}")
        print()
    except gitlab.Exception as e:
      print(f"{colored('[Error]', 'red')} An exception occurred look at /tmp/jks.log");
      logger.error(e)
  elif args.ask_validation:
    print(f"{colored('[Ask Validation]', 'cyan')} {colored(','.join(args.ask_validation), 'green')} feature not available")
    # Check if card_id is empty
    #if args.card_id == None:
    #  parser.error(f"{colored('[Error]', 'red')} You must specify a cardId")
    
    #if env == None:
    #  parser.error(f"{colored('[Error]', 'red')} You must specify a env")

    #
    #print(f"{colored('[Ask Validation]', 'cyan')} {colored(','.join(args.ask_validation), 'green')} for cardId: {colored(args.card_id, 'green')} on env: {colored(env, 'green')}")

    #if confirm(f"{colored('Are you sure [Y/N]? ', 'light_blue', attrs=['bold'])}"):
    #  askValidation(server, args.ask_validation, args.card_id, env,  env=env, slack_user_id=custom_config['SLACK']['UserId'])
  elif args.remove:
    #
    print(f"{colored('[Delete]', 'cyan')}:")
    print(f"• Env: {colored(env, 'green')}")

    if confirm(f"{colored('Are you sure [Y/N]? ', 'light_blue', attrs=['bold'])}"):
      # Remove envs
      delete_env(server, env, slack_user_id=custom_config['SLACK']['UserId'])   
  elif args.cron:
    if croniter.is_valid(args.cron) is False:
      print(f"{colored('[Error]', 'red')} Cron is not valid")
      sys.exit(1)

    type = {}
    if args.start:      
      type['start'] = get_branch_name(args.start)
      print(f"{colored('[Cron Start]', 'cyan')} {colored(type['start'], 'green')}:")
    if args.build:
      type['build'] = get_branch_name(args.build)
      print(f"{colored('[Cron Build]', 'cyan')} {colored(type['build'], 'green')}:")
    if args.deploy:
      type['deploy'] = get_branch_name(args.deploy)
      print(f"{colored('[Cron Deploy]', 'cyan')} {colored(type['deploy'], 'green')}:")
    
    print(f"• Env: {colored(env, 'green')}") 
    print(f"• Installation Id: {colored(args.installation_id, 'green')}")

    # Check if type is empty
    if type.__len__() == 0:
      parser.error(f"{colored('[Error]', 'red')} You must specify a type with cron [s, b, d]")

    # Check if all values are equal
    if check_equal_values(type) == False:
      print(f"{colored('[Error]', 'red')} The branch name must be the same for all types for this moment")
      sys.exit(1)

    if confirm(f"{colored('Are you sure [Y/N]? ', 'light_blue', attrs=['bold'])}"):
      create_pipeline(server, f"cron.{list(type.values())[0]}",  env=env, cron=args.cron, type=type, slack_user_id=custom_config['SLACK']['UserId'])
  elif args.start:
    branch_name = get_branch_name(args.start)
  
    if env is None:
      print(f"{colored('[Error]', 'red')} Environment not found")
      sys.exit(1)

    #
    print(f"{colored('[Start]', 'cyan')}:")
    print(f"• Branch: {colored(branch_name, 'green')}")
    print(f"• Env: {colored(env, 'green')}")

    if confirm(f"{colored('Are you sure [Y/N]? ', 'light_blue', attrs=['bold'])}"):
      # Start envs
      start_env(server, branch_name, env, slack_user_id=custom_config['SLACK']['UserId'])
  elif args.build:
    branch_name = get_branch_name(args.build)

    #
    print(f"{colored('[Build]', 'cyan')}:")
    print(f"• Branch: {colored(branch_name, 'green')}")
    
    if confirm(f"{colored('Are you sure [Y/N]? ', 'light_blue', attrs=['bold'])}"):
      # Start build
      start_build(server, branch_name, False);
  elif args.deploy:
    branch_name = get_branch_name(args.deploy)

    if args.deploy == 'current':
      # Get current branch name
      branch_name = get_git_branch_name()

      # Check branch name
      check_git_branch_name(branch_name);
    
    if env is None:
      print(f"{colored('[Error]', 'red')} Environment not found")
      sys.exit(1)

    if len(args.installation_id) > 12:
      print(f"{colored('[Error]', 'red')} Installation id should be less than 12 characters")
      sys.exit(1)

    print(f"{colored('[Deploy]', 'cyan')}:")
    print(f"• Branch: {colored(branch_name, 'green')}")
    print(f"• Env: {colored(env, 'green')}") 
    print(f"• Installation Id: {colored(args.installation_id, 'green')}")

    # 
    if args.kubernetes_version: 
      print(f"• Kubernetes version: {colored(args.kubernetes_version, 'green')}")
    
    if confirm(f"{colored('Are you sure [Y/N]? ', 'light_blue', attrs=['bold'])}"):
      # Start deploy
      deploy(
        server=server,
        branch_name=branch_name,
        prefix_name=env,
        slack_user_id=custom_config['SLACK']['UserId'],
        test_types=args.test_types,
        installation_id=args.installation_id,
        kubernetes_version=args.kubernetes_version
      );

  sys.exit(1);