#!/usr/bin/env python
"""
OpenDocument Security

Copyright 2020-2023 Nicolas BEGUIER
Licensed under the Apache License, Version 2.0
Written by Nicolas BEGUIER (nicolas_beguier@hotmail.com)
"""

# Standard library imports
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import logging
from os.path import exists
import sys
import zipfile

# Third party library imports
import xml.etree.ElementTree as ET

# Debug
# from pdb import set_trace as st

VERSION = '1.3.1'

logging.basicConfig(format='%(message)s')
LOGGER = logging.getLogger('opendocument-security')

def get_content_zip_path(content_path):
    """
    Returns the content path inside zip archive
    """
    content_path = content_path.replace('/./', '/')
    if content_path.startswith('/'):
        content_path = content_path[1:]
    if content_path == '':
        return 'content.xml'
    return '{}/content.xml'.format(content_path)

def display_macro_od(od_zipfile):
    """
    This function returns the list of existing macro
    """
    display_banner = False
    for filepath in od_zipfile.namelist():
        if 'Basic/' in filepath:
            if not display_banner:
                LOGGER.critical('> This OpenDocument contains macro !')
                display_banner = True
            LOGGER.critical('  > %s', filepath)
        if 'Scripts/' in filepath:
            if not display_banner:
                LOGGER.critical('> This OpenDocument contains macro !')
                display_banner = True
            LOGGER.critical('  > %s', filepath)
    return display_banner

def display_macro_flat(od_file):
    """
    This function returns the list of existing macro
    """
    display_banner = False
    with open(od_file, 'r') as content:
        raw_content = content.read()
        try:
            root = ET.fromstring(raw_content)
        except ET.ParseError:
            LOGGER.critical('This file seems corrupted')
            return False
        ooo_prefix = get_tag(raw_content, 'xmlns:ooo')
        list_library_embedded = list()
        find_rec(root, '{'+ooo_prefix+'}'+'library-embedded', list_library_embedded)
        if list_library_embedded:
            if not display_banner:
                LOGGER.critical('> This Flat OpenDocument contains macro !')
                display_banner = True
            LOGGER.critical('  > %s', list_library_embedded)
    return display_banner

def find_rec(node, element, result):
    """
    This function is parsing the xml node to update the
    result by a list of found elements
    """
    for item in node:
        for match_item in item.findall(element):
            result.append(match_item)
        find_rec(item, element, result)
    return result

def get_event_listeners(content, script_prefix, indent):
    """
    This function returns every script:event-listeners in the document
    """
    result = list()
    find_rec(content, '{'+script_prefix+'}'+'event-listener', result)
    for script in result:
        LOGGER.critical('%s> Found event listener: %s', indent, script.attrib)

def get_ole_objects(content, draw_prefix):
    """
    This function returns the nested ole objects in the document
    """
    result = list()
    return find_rec(content, '{'+draw_prefix+'}'+'object', result)

def get_tag(content, tag):
    """
    This function returns the tag value
    """
    if isinstance(content, bytes):
        content = content.decode('utf-8', 'ignore')
    for i in content.split(' '):
        if i.startswith(tag+'='):
            return i.split('"')[-2]
    return None


def display_event_listener_flat(od_file, indent=''):
    """
    This function is parsing the file and displaying macro in event-listener
    """
    LOGGER.warning('%s> Entering in %s', indent, od_file)
    with open(od_file, 'r') as content:
        raw_content = content.read()
        try:
            root = ET.fromstring(raw_content)
        except ET.ParseError:
            LOGGER.critical('This file seems corrupted')
            return False
        office_prefix = get_tag(raw_content, 'xmlns:office')
        script_prefix = get_tag(raw_content, 'xmlns:script')
        if not office_prefix:
            LOGGER.warning('%s> Exiting %s', indent, od_file)
            return False
        if script_prefix:
            get_event_listeners(root, script_prefix, indent+'  ')
    LOGGER.warning('%s> Exiting %s', indent, od_file)
    return True


def display_event_listener_od(od_zipfile, content_path, indent=''):
    """
    This function is parsing the file and displaying macro in event-listener
    """
    content_zip_path = get_content_zip_path(content_path)
    LOGGER.warning('%s> Entering in %s', indent, content_zip_path)
    with od_zipfile.open(content_zip_path) as content:
        raw_content = content.read()
        try:
            root = ET.fromstring(raw_content)
        except ET.ParseError:
            LOGGER.critical('This file seems corrupted')
            return False
        office_prefix = get_tag(raw_content, 'xmlns:office')
        script_prefix = get_tag(raw_content, 'xmlns:script')
        draw_prefix = get_tag(raw_content, 'xmlns:draw')
        xlink_prefix = get_tag(raw_content, 'xmlns:xlink')
        if not office_prefix:
            LOGGER.warning('%s> Exiting %s', indent, content_zip_path)
            return False
        if script_prefix:
            get_event_listeners(root, script_prefix, indent+'  ')
        if draw_prefix and xlink_prefix:
            for ole_object in get_ole_objects(root, draw_prefix):
                draw_href = ole_object.attrib['{'+xlink_prefix+'}'+'href']
                display_event_listener_od(
                    od_zipfile,
                    '{}/{}'.format(content_path, draw_href),
                    indent=indent+'  ')
    LOGGER.warning('%s> Exiting %s', indent, content_zip_path)
    return True

def main(od_path):
    """
    Main function
    """
    if not exists(od_path):
        LOGGER.critical('%s is not a file...', od_path)
        sys.exit(1)

    is_flat_opendocument = False
    try:
        od_zip_file = zipfile.ZipFile(od_path, 'r')
    except IOError:
        LOGGER.critical('This file seems corrupted')
        sys.exit(1)
    except zipfile.LargeZipFile as err:
        LOGGER.critical(err)
        sys.exit(1)
    except zipfile.BadZipfile:
        is_flat_opendocument = True
    if is_flat_opendocument:
        LOGGER.warning('> Parsing Flat OpenDocument %s', od_path)
        is_macro = display_macro_flat(od_path)
        if is_macro:
            display_event_listener_flat(od_path)
        LOGGER.warning('> Closing Flat OpenDocument %s', od_path)
    else:
        LOGGER.warning('> Parsing OpenDocument %s', od_path)
        is_macro = display_macro_od(od_zip_file)
        if is_macro:
            display_event_listener_od(od_zip_file, '')
        LOGGER.warning('> Closing OpenDocument %s', od_path)
        od_zip_file.close()


if __name__ == '__main__':
    PARSER = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter
    )
    PARSER = ArgumentParser()

    PARSER.add_argument('--version', action='version', version=VERSION)
    PARSER.add_argument(
        'od_path',
        action='store',
        help='An opendocument path')

    ARGS = PARSER.parse_args()

    main(ARGS.od_path)
