#!/usr/bin/python

# Note: for setting up email with sendmail, see: http://linuxconfig.org/configuring-gmail-as-sendmail-email-relay

import argparse
import subprocess
import json
import logging
import smtplib
import sys
import ctypes  # An included library with Python install.

from datetime import datetime
from os import path
from subprocess import check_output


def main():
    with open('config.json', 'r') as json_file:
        data = json.load(json_file)

    with open('config.json.bak', 'w') as json_file:
        json.dump(data, json_file, indent=4)



if __name__ == '__main__':
    main()
