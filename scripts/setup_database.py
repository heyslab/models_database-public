import sys

import models_database as mdb


def main(args):
    try:
        mdb.reset_db()
    except:
        mdb.create_db()

    db = mdb.ExperimentDatabase()


if __name__ == '__main__':
    main(sys.argv[1:])
