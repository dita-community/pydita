#!/usr/bin/env python
"""Configure the local ditalib environment

* Set the location of the DITA Open Toolkit you want to use.
* ???
"""

import os
import sys
from io import IOBase

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
libDir = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.append(libDir)

from lxml import etree
from lxml.etree import XMLParser
from lxml.etree import ElementTree

from ditalib import config

print('### sys.path:')
print(sys.path)

def reportErrorAndExit(msg: str):
    print(f'[ERROR] {msg}')
    print(f'[ERROR] Check your DITA Open Toolkit installation to make sure it\'s good.')
    sys.exit(1)

print("""
[INFO] Checking the configuration details for full use of the ditalib modules.
[INFO]
[INFO] In order to do grammar-aware parsing of DITA documents, ditalib needs an
[INFO] entity resolution catalog, which is most easily found in a DITA Open Toolkit.
[INFO] This code checks that your configured Open Toolkit has a parsable catalog file.
[INFO]
""")

otDirEnvVariable = "DITA_OT_DIR"
otDir: str = os.environ.get(otDirEnvVariable)
homeDir: str = os.environ.get("HOME")
buildPropertiesFile: str = ".build.properties"
buildPropertiesPath: str = os.path.join(homeDir, buildPropertiesFile)
otDirProperty: str = "dita.ot.dir"
saveConfig: bool = False

if otDir is not None:
    print(f'[INFO] Found environment variable {otDirEnvVariable}')

if otDir is None:
    props: dict[str, str] = {}
    if os.path.exists(buildPropertiesPath):
        f: IOBase = open(buildPropertiesPath,'r')
        for line in f.readlines():
            if line.startswith('#'):
                continue
            (name, value) = line.split('=')
            props[name] = value
        f.close()
        otDir = props.get(otDirProperty)
        if otDir is not None:
            print(f'[INFO] Found property "{otDirProperty}" in configuration file "{buildPropertiesPath}"')        
    
if otDir is None:
    inputDir = input("Enter the path to the Open Toolkit you want to use (you can use '~'): ")
    if inputDir is None or inputDir == "":
        print(f'[INFO] No directory entered, quiting.')
        sys.exit(0)
    otDir = os.path.expanduser(inputDir)
    saveConfig = True

# This should always succeed at this point
if otDir is not None:
    print(f'[INFO] DITA Open Toolkit directory is set to "{otDir}"')

if not os.path.exists(otDir):
    reportErrorAndExit(f'Open toolkit directory "{otDir}" not found.')
if os.path.exists(otDir):
    print(f'[INFO]   Directory "{otDir}" exists, checking Open Toolkit to make sure it\'s usable...')
    catalogXmlFile: str = "catalog-dita.xml"
    catalogXmlFilePath: str = os.path.join(otDir, catalogXmlFile)
    expectedFirstLine: str = '<?xml version="1.0" encoding="UTF-8"?>'
    try:
        f: IOBase = open(catalogXmlFilePath, 'r')
    except Exception as err:
        reportErrorAndExit(f'Got {err.__class__.__name__} exception "{err}" opening file "{catalogXmlFilePath}')
    line: str = f.readline()
    if line is None:
        reportErrorAndExit(f'Did not find expected file {catalogXmlFile}.')

    if line is not None and line.strip() != expectedFirstLine:
        reportErrorAndExit(f'Found expected file {catalogXmlFile} but it did not have expected first line "{expectedFirstLine}".')
    f.close()
    print(f'[INFO] Found expected {catalogXmlFile} file.')
    try:
        parsed: ElementTree = etree.parse(catalogXmlFilePath, XMLParser(load_dtd=False, attribute_defaults=False))
    except Exception as err:
        reportErrorAndExit(f'Got {err.__class__.__name__} exception "{err}" parsing entity catalog file {catalogXmlFile}')
    if parsed is None:
        reportErrorAndExit(f'Found {catalogXmlFile} but failed to parse it.')

    print(f'[INFO] Successfully parsed {catalogXmlFile}, should be good to go with this Open Toolkit.')

if saveConfig:
    print(f'[INFO] Saving configuration settings to ~/.build.properties')
    lines: list[str] = ['# Python ditalib settings\n', f'{otDirProperty}={otDir}\n']
    if os.path.exists(buildPropertiesPath):
        print(f'[INFO] Adding {otDirProperty} entry to "{buildPropertiesPath}"...')
        try:
            f = open(buildPropertiesPath, 'a')
            f.writelines(lines)
            f.close()
            print(f'[INFO] Configuration file updated.')
        except Exception as err:
            reportErrorAndExit(f'Got {err.__class__.__name__} exception "{err}" opening file {buildPropertiesPath} for write.')
    else:
        print(f'[INFO] Creating configuration file "{buildPropertiesPath}"...')
        try:
            f = open(buildPropertiesPath, 'w')
            f.writelines(lines)
            f.close()
            print(f'[INFO] Configuration file created.')
        except Exception as err:
            reportErrorAndExit(f'Got {err.__class__.__name__} exception "{err}" opening file {buildPropertiesPath} for write.')
    