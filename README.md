# TUBULAR
A small CI/CD pipeline manager for normal people who use Git.  
*TODO: docs for people who don't know what that means*

The core concepts of Tubular are
- Human Parsable
- Version Controlled
- Plain Text

Everything from the system configuration to the pipeline definitions are mere text files (YAML, to be precise)
and all of it is expected to be contained in (one or more) git repos. Even if the application goes down or you eventually
move on from Tubular, everything is easy to understand and transfer to another system.

Tubular also strives to be simple and concise in its workspace directory structure possible, with the intention that a real human ~~may~~ **will**
need to inspect the workspace and output of a pipeline from time to time.

## Features
- **Multi-node**: Linux and Windows are both supported
- **Version Control**: Everything is version controlled, and we mean everything.
- **Web Management UI**: View and run pipelines in your browser.
- **Auto Triggers**: Automatically run pipelines on a schedule or when somebody commits
- **Live Config Reloading**: Just commit config changes to have it reflected in your system

## Quick-Start

### 1. Install Nodes
*TODO: probably have docker containers for this eventually*

At most 1 control node, any number of task nodes.  
Can have a control node on the same machine as a task node.  

Create a node config file (typically called `tubular.yaml`):
```yaml
# Set this to the repo you create in the next step
config-repo: https://theUrlOfMyRepo.git

# Set the controller workspace path, only needed if this agent is the controller
controller:
  workspace: tubular-workspace/ctrl

# Same thing, but for task nodes
node:
  workspace-root: tubular-workspace/node
```

### 2. Create a Config and a Pipeline repo
The config repo will contain your configuration files for all nodes,
and you will put your pipeline definitions in the pipeline repo.

In your config repo, at a minimum you need `nodes.yaml` and `pipelines.yaml`

#### nodes.yaml
```yaml
nodes:
  myserver:
    # if 'host' is not specified, the above key is used as the hostname
    port: 8000
    # generic list of tags for this node
    # pipelines can white/blacklist specific tags
    tags:
      - windows
      - gpu
  myotherserver:
    host: actualhostname
    port: 8008
    tags:
      - linux
      - whatever
```

#### pipelines.yaml
```yaml
pipelines:
  # Set this to the url of your pipeline repo
  url: "git@github.com:alagyn/tubular-tests"
  default-branch: main
```

#### constants.yaml
This defines a map of constant variables you can reference in your pipelines
```yaml
repo-url: git@github.com:/alagyn/tubular-tests.git
myKey: myVal
```

#### triggers.yaml
This defines the auto triggers for various pipelines
```yaml
triggers:
  - name: My Commit Trigger
    type: commit

    # type specific args
    repo: "@{repo-url}"
    branch: main
    include: 
      # these are any glob that works in a recursive python glob
      - myScript.sh
      - myFolder/*

    # list of pipelines to execute
    # these are scheduled concurrently
    pipelines:
      - target: myPipeline
        args:
          branch: main

  - name: My schedule trigger
    type: schedule
#    # type specific args
#    # min
#    # period: 3 min
    period: 1 hour
#    # no when for these
#
#    # daily
#    #period: 1 day
#    #when: 9:30am
#
#    # Weekly
#    # period: 1 week
#    # when: Friday 9pm
#
    pipelines:
      - target: myFolder/myOtherPipeline
```

### 3. Define a pipeline

myPipeline.yaml:
```yaml
meta:
  display: My pipeline
  keep-runs: 10

args:
  # sets default values
  repo: "@{repo-url}"
  branch: main

stages:
  # stages are completed sequentially
  - display: Build my thing
    # tasks are completed concurrently, if possible
    tasks:
      - myTask
      - idleTask

  - display: Run nested task
    tasks:
      - myFolder/myTask2.yaml
```

myTask.yaml:
```yaml
meta:
  display: My task

node:
  # lists of tags
  requires:
    - linux
  avoids:
    - mac

steps:
  # steps are completed sequentially
  - type: clone
    url: "@{repo}"
    branch: "@{branch}"

  - display: Exec shell
    type: script
    lang: shell
    script: |
      # this is my shell script
      echo "testing testing 1 2 3"
      rm -f output.txt

  - display: exec myScript
    type: exec
    target: "tubular-tests/myScript.sh"

  # copy build to artifact dir
  - type: archive
    target: "output.txt"

  - type: archive
    target: "myFolder"
```
