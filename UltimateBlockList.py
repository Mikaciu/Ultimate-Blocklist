#!/usr/bin/env python
# Written for Python 3.5
# Written by: Adam Walsh
# Modified by: Mikael Hautin
# Written on 7/6/14
# Maintained @ https://github.com/walshie4/Ultimate-Blocklist

import requests
import urllib
import furl
import shutil
from bs4 import BeautifulSoup
import gzip
import os

token = os.getenv('DROPBOX_ACCESS_TOKEN')
db_client = None

if token:
    from dropbox.client import DropboxClient

    db_client = DropboxClient(token)

BASE = "https://www.iblocklist.com"
formats_to_download = ['p2p', 'cidr']


def get_value_from(url):
    parsed_url = BeautifulSoup(requests.get(BASE + url).text, "html.parser")
    return str(parsed_url.find_all("input")[-1]).split("\"")[-2]


def process(url):
    parsed_url = furl.furl(url)

    for list_type in formats_to_download:
        parsed_url.args['fileformat'] = list_type
        gz_file_name = 'ultBlockList_{}.tmp.gz'.format(list_type)

        try:
            handle = urllib.request.urlopen(parsed_url.url)
        except Exception as e:
            print("URL open failed! Exception following:")
            print(e)
            return
        with open(gz_file_name, 'wb') as out:
            while True:
                data = handle.read(1024)
                if len(data) == 0:
                    break

                out.write(data)
        with gzip.open(gz_file_name, 'rt', encoding='latin-1') as downloaded_list_contents:
            with open("blocklist_{}.txt".format(list_type), "a+") as output_text_file:
                output_text_file.write(downloaded_list_contents.read())
        os.remove(gz_file_name)


if __name__ == "__main__":
    # first, remove the old files
    for file_format in formats_to_download:
        for file_type in ['txt', 'gz']:
            file_to_remove = 'blocklist_{}.{}'.format(file_format, file_type)
            if os.path.isfile(file_to_remove):
                os.remove(file_to_remove)

    print("Getting list page")
    soup = BeautifulSoup(requests.get("https://www.iblocklist.com/lists.php").text, "html.parser")
    links = {}  # dict of name of list -> its url
    for row in soup.find_all("tr")[1:]:  # for each table row
        section = str(list(row.children)[0])
        pieces = section.split("\"")
        links[pieces[4].split("<")[0][1:]] = pieces[3]

    for link in links:  # download and combine files
        print("Downloading {} blocklist.".format(link))
        value = get_value_from(links[link])
        if value == "subscription":
            print("Blocklist is not available for free download D:")
        elif value == "unavailable":
            print("URL is unavailable")
        else:  # download and add this sucker
            process(value)

    # duplicates removal
    for file_format in formats_to_download:
        lines_seen = set()
        file_name = 'blocklist_{}.txt'.format(file_format)
        gz_file_name = 'blocklist_{}.gz'.format(file_format)
        os.rename(file_name, '{}.ori'.format(file_name))
        with open('{}.ori'.format(file_name), 'r') as old_file:
            with open(file_name, 'w') as new_file:
                for old_file_line in old_file:
                    if old_file_line not in lines_seen:  # not a duplicate
                        new_file.write(old_file_line)
                        lines_seen.add(old_file_line)
        os.remove('{}.ori'.format(file_name))

        with open(file_name, 'rb') as f_in:
            with gzip.open(gz_file_name, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    if token:
        for file_format in formats_to_download:
            file_name = 'blocklist_{}.txt'.format(file_format)
            with open(file_name, 'rb') as file:
                response = db_client.put_file(file_name, file, overwrite=True)

            print('Uploaded {} to Dropbox!'.format(file_name))
