#!/usr/bin/python

# Note: for setting up email with sendmail, see: http://linuxconfig.org/configuring-gmail-as-sendmail-email-relay

from __future__ import print_function
import argparse
import subprocess
import json
import logging
import smtplib
import sys
import os
import httplib2
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
import ctypes  # An included library with Python install.
import go_to_goes

from datetime import datetime
from os import path
from subprocess import check_output



try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
CLIENT_SECRET_FILE = 'client_secrets.json'
APPLICATION_NAME = 'Drive API Python Quickstart'

EMAIL_TEMPLATE1 = """
<p>Good news! There's a Global Entry appointment available on <b>%s</b> (looking for appointments prior to %s).</p>
<p>If this sounds good, please sign in to https://goes-app.cbp.dhs.gov/main/goes to reschedule.</p>
<p>If you reschedule, please remember to update CURRENT_INTERVIEW_DATE in your config.json file.</p>
"""

EMAIL_TEMPLATE2 = """
<p>No sooner Global Entry appointments available. The soonest is on <b>%s</b> (your current appointment is on %s).</p>
<p>You can sign in to https://goes-app.cbp.dhs.gov/main/goes to reschedule.</p>
<p>If you reschedule, please remember to update CURRENT_INTERVIEW_DATE in your config.json file.</p>
"""


def notify_send_email(settings, current_apt, avail_apt, use_gmail=False):
    sender = settings.get('email_from')
    recipient = settings.get('email_to', sender)  # If recipient isn't provided, send to self.
    password = settings.get('gmail_password')
    last_appt = settings.get('last_available_interview_date_str')

    if not password and use_gmail:
        print('Trying to send from gmail, but password was not provided.')
        return

    try:
        if use_gmail:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender, password)
        else:
            server = smtplib.SMTP('localhost', 25)

        if avail_apt < current_apt:
            subject = "Alert: New Global Entry Appointment Available on " + avail_apt.strftime('%m/%d/%y')
            message = EMAIL_TEMPLATE1 % (avail_apt.strftime('%B %d, %Y at %I:%M%p'), current_apt.strftime('%B %d, %Y at %I:%M%p'))
        else:
            subject = "No New Global Entry Appointment Available. Soonest available on " + avail_apt.strftime('%m/%d/%y')
            message = EMAIL_TEMPLATE2 % (avail_apt.strftime('%B %d, %Y at %I:%M%p'), current_apt.strftime('%B %d, %Y at %I:%M%p'))

        headers = "\r\n".join(["from: %s" % sender,
                               "subject: %s" % subject,
                               "to: %s" % recipient,
                               "mime-version: 1.0",
                               "content-type: text/html"])

        # message = EMAIL_TEMPLATE % (avail_apt.strftime('%B %d, %Y'), current_apt.strftime('%B %d, %Y'))
        content = headers + "\r\n\r\n" + message

        if avail_apt < current_apt:
            server.sendmail(sender, recipient[0:2], content)
            if settings.get('send_mobile'):
                server.sendmail(sender, recipient[1:], "\r\nNew appt on " + avail_apt.strftime('%m/%d/%y at %I:%M%p') + "! Quick!")
        # else:
        #     server.sendmail(sender, recipient[0], content)
        #     server.sendmail(sender, recipient[1:], "\r\nNo sooner appointment. Saddies :(  Soonest appt is on " +
        #                     avail_apt.strftime('%m/%d/%y at %I:%M%p') + ".")

        # elif avail_apt != last_appt:
            # server.sendmail(sender, recipient[0], content)
            # with open('config.json', 'w') as outfile:
            #     json.dump({"last_available_interview_date_str": avail_apt.strftime('%m/%d/%y')}, outfile)



        server.quit()
    except Exception:
        logging.exception('Failed to send success e-mail.')


def notify_osx(msg):
    subprocess.getstatusoutput("osascript -e 'display notification \"%s\" with title \"Global Entry Notifier\"'" % msg)



def main(settings):

    try:
        # Run the phantom JS script - output will be formatted like 'July 20, 2015'
        # script_output = check_output(['phantomjs', '%s/ge-cancellation-checker.phantom.js' % pwd]).strip()
        script_output = check_output(['phantomjs', '--ssl-protocol=any', '%s/ge-cancellation-checker.phantom.js' % pwd]).strip()
        script_output = script_output.decode('utf-8')

        if script_output == 'None':
            logging.info('No appointments available.')
            return

        new_apt = datetime.strptime(script_output, '%B %d, %Y %I:%M %p')


    except ValueError:
        logging.critical("Couldn't convert output: {} from phantomJS script into a valid date. ".format(script_output))
        return
    except OSError:
        logging.critical("Something went wrong when trying to run ge-cancellation-checker.phantom.js. Is phantomjs is installed?")
        return

    current_apt = datetime.strptime(settings['interview_date_cutoff_str'], '%m/%d/%y %I:%M %p')

    if new_apt > current_apt:
        return
        logging.info('No new appointments. Next available on %s (current is on %s)' % (new_apt, current_apt))
        if not settings.get('no_email'):
            notify_send_email(settings, current_apt, new_apt, use_gmail=settings.get('use_gmail'))
            # ctypes.windll.user32.MessageBoxW(0, "No new appointments. Next available on " + new_apt.strftime("%m/%d/%y"),
            #                                  "No New Appointment Available", 'MB_SYSTEMMODAL')
    else:
        msg = 'Found new appointment on %s (current is on %s).' % (new_apt, current_apt)
        logging.info(msg + (' Sending email.' if not settings.get('no_email') else ' Not sending email.'))
        # ctypes.windll.user32.MessageBoxW(0, "Sooner Appointment Available on " + new_apt.strftime("%m/%d/%y"),
        #                                  "New Appointment Available!", 'MB_OK' | 'MB_SYSTEMMODAL')
        if settings.get('notify_osx'):
            notify_osx(msg)
        if not settings.get('no_email'):
            notify_send_email(settings, current_apt, new_apt, use_gmail=settings.get('use_gmail'))
            # go_to_goes.login_to_goes()



def _check_settings(config):
    required_settings = (
        'interview_date_cutoff_str',
        'init_url',
        'enrollment_location_id',
        'username',
        'password'
    )

    for setting in required_settings:
        if not config.get(setting):
            raise ValueError('Missing setting %s in config.json file.' % setting)

    if config.get('no_email') == False and not config.get('email_from'): # email_to is not required; will default to email_from if not set
        raise ValueError('email_to and email_from required for sending email. (Run with --no-email or no_email=True to disable email.)')

    if config.get('use_gmail') and not config.get('gmail_password'):
        raise ValueError('gmail_password not found in config but is required when running with use_gmail option')

if __name__ == '__main__':

    # Configure Basic Logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        stream=sys.stdout,
    )

    pwd = path.dirname(sys.argv[0])

    # Parse Arguments
    parser = argparse.ArgumentParser(description="Command line script to check for Global Entry appointment time slots.")
    parser.add_argument('--no-email', action='store_true', dest='no_email', default=False, help='Don\'t send an e-mail when the script runs.')
    parser.add_argument('--use-gmail', action='store_true', dest='use_gmail', default=False, help='Use the gmail SMTP server instead of sendmail.')
    parser.add_argument('--notify-osx', action='store_true', dest='notify_osx', default=False, help='If better date is found, notify on the osx desktop.')
    parser.add_argument('--config', dest='configfile', default='%s/config.json' % pwd, help='Config file to use (default is config.json)')
    arguments = vars(parser.parse_args())

    # Load Settings
    try:
        with open(arguments['configfile']) as json_file:
            settings = json.load(json_file)

            # merge args into settings IF they're True
            for key, val in arguments.items():
                if not arguments.get(key): continue
                settings[key] = val

            _check_settings(settings)
    except Exception as e:
        logging.error('Error loading settings from config.json file: %s' % e)
        sys.exit()

    # Configure File Logging
    if settings.get('logfile'):
        handler = logging.FileHandler('%s/%s' % (pwd, settings.get('logfile')))
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        handler.setLevel(logging.DEBUG)
        logging.getLogger('').addHandler(handler)

    logging.debug('Running GE cron with arguments: %s' % arguments)

    main(settings)
