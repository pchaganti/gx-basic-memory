
## How we work 

We usually work like this:
* We talk about ideas
* Most of the time you write the files locally
* I review them in my IDE
* I run tests
* We make changes and iterate
* When things work, I commit changes again and we move on. 

A few things about writing files
* files have to be complete, no "# rest is the same", otherwise we lose file info
* read files before writing, in case I've made changes locally
* write files one at a time in chat responses, long responses can get truncated
* We should break up large files into smaller ones so they are easier for you to update. 

Collaboration
* I want your 100% honest feedback
* We work better together. New ideas and experiments are welcome
* We are ok throwing out an idea if it doesn't work
* Progress not perfection. We iterate slowly and build on what is working.
* We've been moving fast, but now we have to focus on robust testing. 
* You update our project knowledge as we go

## Tools

We are dogfooding our basic-memory tool. You can use it to read from our knowledge graph and write new info.

## Project info

Base dir for `basic-memory` project knowledge: `/Users/phernandez/.basic-memory/projects/default`
- you have access to the directory via the `files_system` tools

Files 
/Users/phernandez/.basic-memory/projects/default/entities/*


db:
/Users/phernandez/.basic-memory/projects/default/data/memory.db

- you have access to the db via the `sqlite` tool

## Code repo 

Repo: /Users/phernandez/dev/basicmachines/basic-memory

```text
(.venv) ➜  basic-memory git:(main) ✗ tree -d
.
├── db
│   └── migrations
├── docs
├── examples
├── projects
│   └── obsidian
├── src
│   └── basic_memory
│       ├── cli
│       ├── mcp
│       ├── repository
│       └── services
└── tests


```