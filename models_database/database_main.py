import os.path
import time
import dateutil.parser
import re
import itertools as it

import pkg_resources
import mysql.connector
import json
import yaml


class ExperimentDatabase:
    """An object to wrap MySQLdb and handle all connections to mySQL server

    Example
    -------

    >>> import models_database as mdb
    >>> db = mdb.ExperimentDatabase()
    >>> models = db.select_all('SELECT * FROM models LIMIT 10')
    >>> db.disconnect()
    """

    def __init__(self):
        """Connects to SQL database upon initialization."""
        with open(pkg_resources.resource_filename(__name__, '../config.yaml'),
                  'r') as f:

            self._configs = yaml.safe_load(f)['db_configs']

        self.connect()

    @property
    def database_name(self):
        return self._configs['database']
        

    @classmethod
    def drop_database(cls):
        with open(pkg_resources.resource_filename(__name__, '../config.yaml'),
                  'r') as f:

            mysql_configs = yaml.safe_load(f)['db_configs']

        database = mysql_configs['database']
        del mysql_configs['database']
        db = mysql.connector.connect(**mysql_configs)

        print(f'Removing database {database}')
        db.cursor().execute(
            f'DROP DATABASE IF EXISTS {database}')

    @classmethod
    def create_database(cls):
        with open(pkg_resources.resource_filename(__name__, '../config.yaml'),
                  'r') as f:

            mysql_configs = yaml.safe_load(f)['db_configs']

        database = mysql_configs['database']
        del mysql_configs['database']
        db = mysql.connector.connect(**mysql_configs)

        print(f'Creating database {database}')
        db.cursor().execute(
            f'CREATE DATABASE IF NOT EXISTS {database}')


    def connect(self):
        """Connect to the SQL database."""
        self._database = mysql.connector.connect(**self._configs)

    def disconnect(self):
        """Close the connection to SQL database server."""
        self._database.close()

    def select(self, sql, args=[], verbose=False):
        """ Queries SQL database return single result

        Parameters
        ----------
        sql : str
            Raw SQL to pass to the database.
        args : list, optional
            List of variables to sub into SQL statement in accordiance see
            MySQLdb. Defaults to an empty list.
        verbose : bool, optional
            If set to True print the SQL query. Defaults to False

        Returns
        -------
        result : dict
            First record to match SQL query as a dictionary, with the field
            name being the key.
        """

        cursor = self._database.cursor(dictionary=True, buffered=True)

        cursor.execute(sql, args)
        if verbose:
            print(sql)

        result = cursor.fetchone()
        if result is None:
            return None

        return result


    def select_all(self, sql, args=[], verbose=False):
        """ Queries SQL database and return all the results

        Parameters
        ----------
        sql : str
            Raw SQL to pass to the database.
        args : list, optional
            List of variables to sub into SQL statement in accordiance see
            MySQLdb. Defaults to an empty list.
        verbose : bool, optional
            If set to True print the SQL query. Defaults to False

        Returns
        -------
        result : dict
            All records to match SQL query as a dictionary, with the field name
            being the key.
        """

        cursor = self._database.cursor(dictionary=True, buffered=True)
        cursor.execute(sql, args)
        if verbose:
            print(sql)

        result = cursor.fetchall()
        return result

    def query(self, sql, args=[], verbose=False, ignore_duplicates=True):
        """ Run an arbitrary SQL query i.e. INSERT or DELETE commands. SQL
        statement is passsed directory MySQLdb.

        Parameters
        ----------
        sql : str
            Raw SQL statement to query the database with.
        args : list, optional
            List of variables to sub into SQL statement in accordiance see
            MySQLdb. Defaults to an empty list.
        verbose : bool, optional
            If set to True print the SQL query. Defaults to False
        ignore_duplicates : bool, optional
            If set to True Duplicate entry errors are prevented from being
            raised, instead of raising an error the method returns False.
            Defaults to True.

        Returns
        -------
        bool : True if the SQL statement executes, False otherwise
        """

        cursor = self._database.cursor(dictionary=True, buffered=True)
        try:
            cursor.execute(sql, args)
        except Exception as e:
            if not ignore_duplicates or 'Duplicate entry' not in e.__str__():
                raise e
            return False
        else:
            if verbose:
                print(sql)
            self._database.commit()
        return True

    def table_columns(self, table_name):
        res = self.select(f'SELECT * FROM {table_name} LIMIT 1')
        return [k for k in res.keys()] 


def report_path():
    with open(pkg_resources.resource_filename(__name__, '../config.yaml'),
              'r') as f:
        return yaml.safe_load(f)['report_path']


def create_db():
    """ creates a new database to store models information in """

    db = ExperimentDatabase()
    db.create_database()

    db.query("""
        CREATE TABLE models(
            model_id INT NOT NULL AUTO_INCREMENT,
            base_id INT,
            task_id INT,
            project_id INT,
            path TEXT,
            time INT, PRIMARY KEY (model_id)
            )""")

    db.query("""
        CREATE TABLE model_attributes(
            attribute_id INT NOT NULL AUTO_INCREMENT,
            model_id INT,
            attribute TEXT,
            value TEXT, PRIMARY KEY (attribute_id)
            )""")

    db.query("""
        CREATE TABLE tasks(
            task_id INT AUTO_INCREMENT,
            task_name TEXT, PRIMARY KEY(task_id)
            )""")

    db.query("""
        CREATE TABLE projects(
            project_id INTEGER AUTO_INCREMENT,
            project_name text, PRIMARY KEY(project_id)
            )""")

    db.query("""
        CREATE TABLE project_attributes(
            attribute_id INTEGER AUTO_INCREMENT,
            project_id int,
            attribute text,
            value text, PRIMARY KEY(attribute_id)
            )""")

    db.disconnect()


def reset_db():
    """ Deletes all records an resets the database schema """

    db = ExperimentDatabase()
    tables = db.select_all(
        f'SELECT table_name FROM information_schema.tables WHERE table_schema = "{db.database_name}"')
    
    if len(tables) > 0:
        print(f'Resetting non-empty Models Database: {db.database_name}')
        confirm = input('continue? [y/N]: ').strip().lower()
        if confirm != 'y':
            return
        print('Dropping tables')

        queries = list(map('DROP TABLE {}'.format, [next(iter(x.values())) for x in tables]))
        list(map(db.query, queries))
    db.disconnect()

    create_db()


