import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import sys
import os

import h5py
import numpy as np
import pandas as pd
import itertools as it
import glob
import argparse
from pathlib import Path

import models_database as mdb

def fetch_trial_info(model_id):
    model = mdb.get_model(model_id)
    model_attrs = mdb.get_model_attributes(model_id).drop('model_id')
    #TODO: fix legacy database entries
    if 'regularizer_coef' in model_attrs.index.unique():
        model_attrs['weights_regularizer_coef'] = model_attrs['regularizer_coef']
        model_attrs['activity_regularizer_coef'] = model_attrs['regularizer_coef']

    full_model = pd.concat((pd.Series(model), model_attrs))
    return full_model

def fetch_model_results(task_id, task_name):
    print(f'[{task_name}]')
    trial_ids = mdb.fetch_models(task_name=task_name)
    return pd.Series(trial_ids).apply(fetch_trial_info)

def row_to_html(row):
    base_id = row['base_id']
    if base_id == 0:
        row['base_id'] = '_None'
    else:
        row['base_id'] = mdb.get_model(base_id)['task_name']
    model_id_class = f'basemodel{row["model_id"]:.0f}'
    class_name = f'basemodel{base_id:.0f}'
    row_html = list(row.drop('model_id').drop('path').apply(
        lambda x, className: f'<td class="{className}">{str(x)}</td>',
        className=class_name)) 
    model_id_html = [f'<td class="{model_id_class}">{row["model_id"]:.0f}</td>']
    
    folder = Path(row['path']).parents[0].absolute().resolve()
    path_html = [f'<td class="{class_name}"><a href="https://heys-server-01.bioen.utah.edu/pdfs/index?path=/{folder}" target="_blank">{row["path"]}</a></td>']
    return ['<tr>'] + model_id_html + row_html + path_html + ['</tr>']

def main(argv):
    trial_type = 'tDNMS'
    #filepath = f'/data1/jack/models_info_mysql.html'
    filepath = mdb.report_path()
    print(filepath)

    db = mdb.ExperimentDatabase()
    tasks = pd.DataFrame(db.select_all('SELECT * FROM tasks'))
    db.disconnect()

    all_data = pd.concat(
        tasks.apply(lambda x: fetch_model_results(**x), axis=1).values
        ).set_index('task_name', drop=True)
    all_data = all_data.where(all_data['epoc'].notna()).dropna(how='all')
    all_data['mse'] = all_data['mse'].apply(lambda x: f'{x:.5f}')

    styles = {'html': {'font-family': 'Arial, Helvetica, sans-serif'},
              '.headerRow td': {'background-color': '#aaa',
                                'font-weight': 'bold', 'font-size': '12px'},
              'table': {'background-color': '#aaa'},
              'td': {'padding': '2px 15px', 'font-size': '12px',
                     'white-space': 'nowrap'},
              'td.noUse': {'background-color': '#000', 'color': '#fff'},
              'a:link': {'color': 'inherit', 'text-decoration': 'none'},
              'a:visited': {'color': 'inherit'},
              'caption': {'font-size': 'large', 'background-color': '#ddd',
                          'text-align': 'left', 'padding-top': '5px',
                          'padding-bottom': '5px'}}


    base_tasks = pd.DataFrame(
        list(zip(all_data['base_id'].unique(), it.count())),
        columns=('base_id', 'count'))
    base_tasks['background-color'] = (base_tasks['count'] % 20).apply(
        matplotlib.colormaps['tab20']).apply(matplotlib.colors.rgb2hex)
    base_tasks['color'] = ['#fff' if x == 0 else '#000' for x in
                     base_tasks['count'] % 2 == 1]
    base_tasks['keys'] = base_tasks['base_id'].apply(lambda x: f'.basemodel{x:.0f}')
    styles.update(
        base_tasks[['keys', 'background-color', 'color']].set_index(
            'keys').T.to_dict())
    ss = [str(k) + ' {' + '; '.join(
        [f'{kk}: {vv}' for kk, vv in v.items()]) + '}' for k, v in
         styles.items()]

    style = [
        '<style>'] + ss + \
        ['</style>'
    ]

    cols = ['model_id', 'base_id',  'time',
            'activation', 'learning_rate', 'noise_level',
            'input_noise', 'gamma', 'mse', 'epoc', 'weights_regularizer_coef',
            'activity_regularizer_coef','path']

    all_data = all_data.reindex(cols, axis=1)
    data_rows = list(it.chain.from_iterable(
        all_data.apply(row_to_html, axis=1)))

    header_row = ['<tr class="headerRow"><td>' +
                 '</td><td>'.join(all_data.columns.values) +
                 '</td></tr>']

    tables = all_data.groupby('task_name').apply(
        lambda x, header_row=header_row:
            ['<table>', f'<caption>{x.name}</caption>'] + header_row +
            list(it.chain.from_iterable(x.sort_values(['base_id', 'epoc']).apply(row_to_html, axis=1))) +
            ['</table>', '<br/><br/>'])

    page = [
        '<html>',
        '<head>'] + style + ['</head>'] + \
        ['<body>'] + list(it.chain.from_iterable(tables.values)) + \
        ['</table>',
        '</body>',
        '</html>'
    ]
    with open(filepath, 'w') as f:
        f.writelines(page)


if __name__ == '__main__':
    main(sys.argv[1:])
