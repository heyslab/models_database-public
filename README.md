# models_database-public

`models_database` is a small MySQL-backed Python helper for assigning,
querying, and reporting metadata for trained model runs. It was originally
used as lightweight lab infrastructure: training scripts inserted each saved
model into a database, and downstream analysis scripts used the resulting
model IDs to recover saved-model paths, task labels, project labels, and
run-specific attributes.

This public repository is provided as an archival transparency resource. It is
most useful for understanding analysis code that refers to model IDs through:

```python
import models_database as mdb
```

It is not intended to be a general-purpose experiment-tracking service or a
fully supported database package.

## What It Stores

The database schema tracks four main kinds of information:

```text
models              One row per saved model/run
model_attributes    Key-value metadata attached to model IDs
tasks               Named task labels
projects            Named project labels
project_attributes  Key-value metadata attached to projects
```

The `models` table stores:

```text
model_id    Integer model/run identifier
base_id     Optional parent/base model ID
task_id     Link to a named task
project_id  Link to a named project
path        Saved-model path
time        Unix timestamp for the run
```

The flexible `model_attributes` table stores additional values such as
training epoch, learning rate, input noise, recurrent noise, gamma, model MSE,
regularization coefficients, and other run-specific metadata. Attribute values
are stored as strings in MySQL; `get_model_attributes(...)` converts values
back to floats when possible.

## Repository Contents

```text
models_database/
  __init__.py
  database_main.py      Database connection wrapper and schema helpers
  db_functions.py       Public insert/query/update helper functions

scripts/
  setup_database.py     Initialize/reset the expected MySQL schema
  models_report.py      Generate an HTML report of model metadata
  update_base_dir.py    Bulk-rewrite stored model paths

config.yaml             Example database/report configuration
setup.py                Minimal package installer
```

## Installation

Install from the repository root:

```bash
pip install -e .
```

The package depends on:

```text
pyyaml
python-dateutil
mysql-connector-python
pandas
setuptools<82
```

The report script also uses plotting/data packages such as `matplotlib`,
`numpy`, and `h5py`.

## Configuration

The package reads database settings from `config.yaml`:

```yaml
db_configs:
    host: <database_host_ip>
    user: <sql_username>
    password: <sql_password>
    database: models

report_path: /analysis/models_info.html
```

Replace the placeholder values with settings for your local MySQL server. Do
not commit real credentials to a public repository.

The configured MySQL user needs permission to read and write the selected
database. Schema-creation/reset commands require permission to create or drop
tables and, depending on the setup path used, create the database.

## Database Setup

To initialize the expected schema in a configured MySQL database:

```bash
python scripts/setup_database.py
```

This script wraps the schema helpers in `models_database.database_main`.
Inspect the configured database before running it: when pointed at an existing
non-empty database, the reset helper can drop existing tables after prompting.

If you are using an accompanying manuscript metadata dump, restore that dump
with standard MySQL tooling instead of creating an empty database.

Example:

```bash
mysql -u <sql_username> -p models < manuscript_tables.sql
```

Use the database name that matches `config.yaml`.

## Common API Usage

Import the package:

```python
import models_database as mdb
```

Fetch the main metadata row for a model:

```python
model = mdb.get_model(132)
print(model["path"])
print(model["task_name"])
print(model["project_name"])
```

Fetch model attributes:

```python
attrs = mdb.get_model_attributes(132)
print(attrs["gamma"])
print(attrs["input_noise"])
```

Find model IDs by task, project, base model, or attributes:

```python
model_ids = mdb.fetch_models(task_name="just_short_match")
model_ids = mdb.fetch_models(project_name="tDNMS")
model_ids = mdb.fetch_models(base_id=0)
model_ids = mdb.fetch_models(gamma=0.2, input_noise=0.15)
```

Insert a new model record:

```python
model_id = mdb.insert_model(
    project="tDNMS",
    task="just_short_match",
    filepath="/models/example/model.keras",
    base_id=0,
    attrs={
        "gamma": 0.2,
        "input_noise": 0.15,
        "noise_level": 0.3,
        "epoc": 1000,
        "mse": 0.0012,
    },
)
```

Update a model attribute:

```python
mdb.update_model_attr(model_id, "mse", 0.0011)
```

Update a stored model path:

```python
mdb.update_path(model_id, "/new/model/archive/model.keras")
```

Run a direct SQL query when needed:

```python
db = mdb.ExperimentDatabase()
rows = db.select_all("SELECT * FROM models LIMIT 10")
db.disconnect()
```

## Utility Scripts

### `scripts/models_report.py`

Generates an HTML summary of models grouped by task:

```bash
python scripts/models_report.py
```

The output path comes from `report_path` in `config.yaml`. The report script
was written for the original lab server and includes a path-link template for
that environment; users running it elsewhere may want to adjust the generated
links.

### `scripts/update_base_dir.py`

Bulk-rewrites stored model paths by replacing one path component/string with
another:

```bash
python scripts/update_base_dir.py <old_base> <new_base>
```

This updates database records in place. Inspect the printed path changes before
using it on a database you care about.

### `scripts/setup_database.py`

Creates or resets the schema expected by this package:

```bash
python scripts/setup_database.py
```

This is useful for a fresh local database. For an archival manuscript metadata
database, restoring the provided SQL dump is usually the more direct route.

## Notes for Reuse

- This package is intentionally minimal and mirrors the original analysis
  workflow.
- It does not store trained model files, electrophysiology data, or analysis
  caches. It stores paths and metadata that point to those resources.
- Model attributes are stored as flexible key-value pairs, so available fields
  depend on what the original training scripts inserted.
- Many analyses use model IDs as stable handles; moving model archives may
  require updating the stored `path` values.
- The helper is useful for reproducing the metadata lookup API expected by
  analysis scripts, but it is not a replacement for a full experiment-tracking
  platform.

## AI Assistance Disclosure

This README was generated with AI assistance using the repository source files
and manuscript-analysis context as reference. The source code included in this
repository was not generated by AI.
