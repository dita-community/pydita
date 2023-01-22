"""Manages and provides access to configuration information needed to do DITA processing.
"""

import os, sys
from io import IOBase

homeDir: str = os.environ.get("HOME")
buildPropertiesFile: str = ".build.properties"
buildPropertiesPath: str = os.path.join(homeDir, buildPropertiesFile)
otDirProperty: str = "dita.ot.dir"
otDirEnvVariable: str = "DITA_OT_DIR"

def readPropertiesFile(filePath: str) -> dict[str, str]:
    """Reads the specified Java properties file (name=value) into a
    dictionary.

    Args:

        filePath (str): Path to the properties file to load.

    Returns:

        dict[str, str]: Dictionary where keys are the property names and values are the property values.
    """
    props: dict[str, str] = {}
    if os.path.exists(filePath):
        f: IOBase = open(filePath,'r')
        for line in f.readlines():
            if line.startswith('#'):
                continue
            (name, value) = line.split('=')
            props[name] = value.strip()
        f.close()
    else:
        raise FileNotFoundError(filePath)
    return props

def getDitaOtPath() -> str:
    """Gets the configured DITA OT path if it can find it.

    Returns:

        str: The absolute path to the configured DITA OT or None if
             the configuration is not found.
    """

    otPath: str = os.environ.get(otDirEnvVariable)
    if otPath is None:
        properties: dict[str, str] = readPropertiesFile(buildPropertiesPath)
        otPath: str = properties.get(otDirProperty)
    
    return otPath
    
