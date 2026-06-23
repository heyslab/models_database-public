import sys
import argparse
from pathlib import Path

import models_database as mdb

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('old_base', type=str, help='old path part to replace')
    parser.add_argument('new_base', type=str, help='old path part to swap in')
    args = parser.parse_args()

    models = mdb.fetch_models('time')
    old_part = args.old_base
    new_part = args.new_base
    
    for model_id in models:
        model = mdb.get_model(model_id)
        path = Path(model['path'])
        if old_part in path.parts:
            new_path = Path(str(path).replace(old_part, new_part).replace('//', '/')).absolute()
            print(f'update path:\n{path} -> {new_path}\n')
            mdb.update_path(model_id, str(new_path))


if __name__ == '__main__':
    main(sys.argv[1:])
