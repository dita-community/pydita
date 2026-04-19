# pydita

Python utilities for DITA processing: map resolution, key space construction, DITAVAL filtering.

Version 0.1.0. Default branch is `develop`.

The `pyproject.toml` in the project root defines this as an installable package (`pydita`).

## Documentation

- [DITA key space construction algorithm](KEYSPACE_CONSTRUCTION_ALGORITHM.md)
- [DITA key space construction guide](KEYSPACE_CONSTRUCTION_GUIDE.md)

## Modules

| Module | Description |
|--------|-------------|
| `pydita.config` | DITA OT path discovery from `DITA_OT_DIR` or `~/.build.properties` |
| `pydita.xmlutils` | XML parsing helpers (DTD-aware and no-DTD parsers, element utilities) |
| `pydita.loggingutils` | Error recording and reporting (`SEVERITY`, `ErrorRecord`, `recordError`) |
| `pydita.ditaenv` | Environment helpers: Git directory detection, relative path computation |
| `pydita.visitor` | Visitor pattern base classes (`Visitor`, `Visitable`) |
| `pydita.ditaval` | DITAVAL filter: parse `.ditaval` files, filter elements |
| `pydita.ditavalvisitors` | Visitor that generates an Excel report from a DITAVAL filter |
| `pydita.resolvemap` | Resolve a DITA map tree to a single in-memory document |
| `pydita.ditautils` | DITA-aware utilities: conref resolution, key reference handling |
| `pydita.keyspace` | Key space and key definition data model |
| `pydita.keyspacemgr` | Key space manager: constructs and manages key spaces from a root map |
| `pydita.keyspacevisitors` | Visitors: pull-up/push-down, text report, Excel report for key spaces |
| `pydita.ditacontext` | `DitaContext`: bundles key space, DITAVAL filter, and error state |

## Requirements

- Python 3.10 or newer
- A DITA Open Toolkit installation for DTD-aware parsing (set `DITA_OT_DIR` or `dita.ot.dir` in `~/.build.properties`)

## Installation

Install the package from GitHub using pip or pipenv:

```
pipenv install git+https://github.com/dita-community/pydita.git@main#egg=pydita
```

Or add to your `Pipfile`:

```
pydita = {ref = "main", git = "https://github.com/dita-community/pydita.git"}
```

## Developing

This project uses pipenv to manage dependencies.

### Set up

```
cd ~/workspace/pydita
pipenv install --dev
```

### Running tests

```
pipenv run pytest
```

The test suite requires a DITA Open Toolkit to be discoverable. The `conftest.py` auto-discovers common installation locations (including the Oxygen XML Editor bundled OT on macOS). You can also set `DITA_OT_DIR` explicitly:

```
DITA_OT_DIR=/path/to/dita-ot pipenv run pytest
```

### Installing from local source in another project

```
cd ~/workspace/other-project
pipenv install -e ~/workspace/pydita --dev
```

## Contributing

All commits must be signed. All merges to `develop` and `main` must go through pull requests.

Development is done on scratch branches named:

```
scratch/{mergeTarget}/{StoryNumber|NoStory}-{description}
```
