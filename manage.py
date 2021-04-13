#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doc_server.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    if sys.argv[1] == "runserver":
        import configparser
        conf = configparser.ConfigParser()
        conf.read("../config.ini")
        sys.argv = sys.argv[:2]
        sys.argv.append(f"{conf['doc-server']['host']}:{conf['doc-server']['port']}")
    execute_from_command_line(sys.argv)
