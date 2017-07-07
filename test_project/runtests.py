#!/usr/bin/env python
import os
import sys


sys.argv.insert(1, 'test')

if len(sys.argv) == 2:
    sys.argv.append('cache_utils')


if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
