import os.path
import time
import dateutil.parser
import datetime
import re
import itertools as it
import pandas as pd

import json
import yaml

from .database_main import ExperimentDatabase

def insert_model(project, task, filepath, base_id=0, exec_time=None,
                 attrs_file=None, attrs={}):

    project_id = fetch_project_id(project, create=False)
    task_id = fetch_task_id(task, create=False)

    if exec_time is None:
        unix_time = int(time.time())
    else:
        unix_time = int(time.mktime(
            dateutil.parser.parse(exec_time).timetuple()))

    db = ExperimentDatabase()
    db.query("""
        INSERT INTO models
            (`base_id`, `task_id`, `path`, `project_id`, `time`)
        VALUES (%s, %s, %s, %s, %s)
        """, args=[base_id, task_id, filepath, project_id, unix_time])

    model_id = fetch_models(unix_time=unix_time)[-1]
    db.disconnect()

    if attrs_file is not None:
        with open(attrs_file, 'r') as f:
            model_attrs = yaml.load(attrs_file)
    else:
        model_attrs = {}
    model_attrs.update(attrs)

    for attribute, value in model_attrs.items():
        update_model_attr(model_id, attribute, value)

    return model_id


def update_model(model_id, **args):
    db = ExperimentDatabase()
    if model_id in args.keys():
        raise Exception('Model ID cannot be updated')

    for field, value in args.items():
        db.query("""
                UPDATE models
                SET `{}` = %s
                WHERE model_id = %s
                """.format(field),
                     args=[value, model_id], verbose=False)


def update_attr(table, group_name, group_id, attribute, value):
    """
    Parameters
    ----------
    table :
    group_name :
    group_id :
    attribute : str
        Attribute in database to set
    value : str
        Value to set for attribute
    """

    db = ExperimentDatabase()
    attr = db.select("""
        SELECT attribute_id
        FROM {}
        WHERE {} = %s
        AND attribute = %s
        """.format(table, group_name), args=[group_id, attribute],
        verbose=False)

    if attr is not None:
        db.query("""
            UPDATE {}
            SET value = %s
            WHERE attribute_id = %s
            """.format(table),
                 args=[value, attr['attribute_id']], verbose=False)
    else:
        db.query("""
            INSERT INTO {} (`{}`, `attribute`, `value`)
            VALUES (%s, %s, %s)
            """.format(table, group_name),
                 args=[group_id, attribute, value], verbose=False)

    db.disconnect()


def update_model_attr(model_id, attribute, value):
    update_attr('model_attributes', 'model_id', model_id, attribute, value)

def fetch_attr(table, group_name, group_id, attribute, default=None):
    """
    Parameters
    ----------
    table :
    group_name :
    group_id :
    attribute : str
        Attribute to fetch
    default : optional
        What to return if attribute does not exist.
    """
    db = ExperimentDatabase()
    attr = db.select("""
        SELECT value
        FROM {}
        WHERE {} = %s
        AND attribute = %s
        """.format(table, group_name),
        args=[group_id, attribute], verbose=False)
    db.disconnect()

    if attr:
        return attr['value']

    return default



def fetch_task_id(task, create=False):
    db = ExperimentDatabase()

    task_id = db.select_all("""
        SELECT task_id
        FROM tasks
        WHERE task_name = %s
        """, args=[task])

    if create and len(task_id) == 0:
        db.query("""
            INSERT INTO tasks (task_name)
            VALUES (%s)
        """, args=[task])
        db.disconnect()

        task_id = fetch_task_id(task, create=False)
    elif len(task_id) == 1:
        db.disconnect()
        task_id = int(task_id[0]['task_id'])
    else:
        raise KeyError('unable to uniquely identify task {}'.format(
            task))

    return task_id


def fetch_project_id(project_name, create=False):
    db = ExperimentDatabase()

    project_id = db.select_all("""
        SELECT project_id
        FROM projects
        WHERE project_name = %s
        """, args=[project_name])

    if create and len(project_id) == 0:
        db.query("""
            INSERT INTO projects (project_name)
            VALUES (%s)
        """, args=[project_name])
        db.disconnect()

        project_id = fetch_project_id(project_name, create=False)
    elif len(project_id) == 1:
        db.disconnect()
        project_id = int(project_id[0]['project_id'])
    else:
        raise KeyError('unable to uniquely identify project {}'.format(
            project_name))

    return project_id


def _resolve_start_time(start_time):
    try:
        tstruct = time.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass
    else:
        return start_time

    formats = ['%Y-%m-%d-%Hh%Mm%Ss', '%m/%d/%Y']
    for t_format in formats:
        try:
            tstruct = time.strptime(start_time, t_format)
            start_time = time.strftime('%Y-%m-%d %H:%M:%S', tstruct)
        except BaseException:
            pass
        else:
            return start_time

    raise Exception('unable to parse time')



def fetch_models(*args, **kwargs):
    db = ExperimentDatabase()
    trial_fields = db.table_columns('models')

    query_string = """
        SELECT DISTINCT t.*
        FROM {}
        LEFT JOIN model_attributes ta
            USING(model_id)
        LEFT JOIN tasks tn
            USING(task_id)
        LEFT JOIN projects p
            USING(project_id)
        WHERE {} ORDER BY time"""

    conditions = []
    query_args = []
    trial_condition = "({} IS NOT NULL)"
    condition_string = "(attribute='{}')"
    for key in args:
        if key in trial_fields:
            if key == 'project_id':
                key = 'model.%s' % key
            conditions.append(trial_condition.format(key))
        else:
            conditions.append(condition_string.format(key))

    trial_condition = "({}={})"
    condition_string = "(attribute='{}' AND value={})"
    for key, values in kwargs.items():
        if type(values) != list:
            values = [values]

        alternatives = []
        for val in values:
            if key in ['time']:
                val = _resolve_start_time(val)
            elif key == 'unix_time':
                key = 'time'

            try:
                float(val)
            except BaseException:
                val = "'{}'".format(val)

            if key in trial_fields:
                if key == 'model_id' or key == 'project_id' or key == 'task_id':
                    _key = 't.%s' % key
                else:
                    _key = key

                if _key == 'data_folder':
                    if val[1:-1].strip() == '':
                        alternatives.append('data_folder IS NOT NULL')
                    else:
                        alternatives.append('data_folder LIKE %s')
                        query_args.append(os.path.normpath(val[1:-1]) + '%')
                else:
                    alternatives.append(trial_condition.format(_key, val))
            elif key == 'project_name':
                alternatives.append(trial_condition.format(key, val))
            elif key == 'task_name':
                alternatives.append(trial_condition.format(key, val))
            else:
                alternatives.append(condition_string.format(key, val))
        conditions.append("({})".format(" OR ".join(alternatives)))

    query = 'models t'
    for condition in conditions[::-1]:
        query = " (" + query_string.format(query, condition) + ") AS t"
    query = query.rstrip(') AS t').lstrip(' (')

    trials = db.select_all(query, args=query_args)
    return [int(trial['model_id']) for trial in trials]


def get_model(model_id):
    query_string = """
        SELECT m.model_id, t.task_name, p.project_name, m.base_id,
               m.path, m.time
        FROM models m
            LEFT JOIN projects p ON m.project_id = p.project_id
            LEFT JOIN tasks t ON m.task_id = t.task_id
        WHERE m.model_id = %s
        """

    db = ExperimentDatabase()
    result =  db.select(query_string, args=[model_id])
    db.disconnect()

    result['time'] = datetime.datetime.fromtimestamp(
        result['time']).__format__('%Y-%m-%d %H:%M:%S')
    return result


def get_model_attributes(model_id):
    query_string = """
        SELECT attribute, value FROM model_attributes WHERE model_id = %s
    """

    db = ExperimentDatabase()
    attributes = db.select_all(query_string, args=[model_id])

    if not len(attributes):
        return pd.Series({'model_id': model_id})

    df = pd.DataFrame(attributes).set_index('attribute')['value']
    df['model_id'] = model_id
    def formatter(x):
        try:
            return float(x)
        except (ValueError, TypeError):
            pass

        return x

    return df.apply(formatter)

def update_path(trial_id, new_path):
    db = ExperimentDatabase()
    db.query("""
        UPDATE models
        SET path = %s
        WHERE model_id = %s
    """, args=[new_path, trial_id])
