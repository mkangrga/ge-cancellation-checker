#!/usr/bin/python

# Note: for setting up email with sendmail, see: http://linuxconfig.org/configuring-gmail-as-sendmail-email-relay

from __future__ import print_function
import json

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

def get_from_gdrive(file_name, local_file_name):

    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

    with open(local_file_name, 'w') as json_file:
        file_list = drive.ListFile({'q': "title='" + file_name + "' and trashed=false"}).GetList()
        gd_file = drive.CreateFile({"id": file_list[0]['id']})
        json.dump(json.loads(gd_file.GetContentString()), json_file, indent=4)


def upload_to_gdrive(file_name, content):
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

    try:
        file_list = drive.ListFile({'q': "title='" + file_name + "' and trashed=false"}).GetList()
        gd_file = file_list[0]
    except:
        gd_file = drive.CreateFile({'title': file_name, 'mimeType': 'text/plain'})
    gd_file.SetContentString(json.dumps(content, indent=4))  # Set content of the file from given string.
    gd_file.Upload()


def main():

    with open("appointment_date.json", 'r') as json_file:
        appointment_date_config = json.load(json_file)

    upload_to_gdrive("appointment_date.txt", appointment_date_config)
    get_from_gdrive("appointment_date.txt", "appointment_date3.json")

    print(appointment_date_config)


if __name__ == '__main__':
    main()
