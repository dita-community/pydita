"""Test configuration module.
"""

import os
import sys

from .fixtures import resourcesDir, rootMap1Path

from ditalib import config

def test_readPropertiesFile(resourcesDir):
    configPath: str = os.path.join(resourcesDir, "config", "test.properties")
    assert os.path.exists(configPath), f'Expected to find test resource "{configPath}"'
    props: dict[str, str] = config.readPropertiesFile(configPath)
    assert props is not None, f'Exected to get a props dictionary.'
    name: str = "prop1"
    value: str = props[name]
    expected: str = "value1"
    assert value == expected, f'Expected value "{expected}" for property "{name}", got "{value}"'
    name: str = "prop2"
    value: str = props[name]
    expected: str = "value2"
    assert value == expected, f'Expected value "{expected}" for property "{name}", got "{value}"'
    # prop3.name=This is a value with spaces
    name: str = "prop3.name"
    value: str = props[name]
    expected: str = "This is a value with spaces"
    assert value == expected, f'Expected value "{expected}" for property "{name}", got "{value}"'
    # prop4-more-name="Value in quotes"
    name: str = "prop4-more-name"
    value: str = props[name]
    expected: str = '"Value in quotes"'
    assert value == expected, f'Expected value "{expected}" for property "{name}", got "{value}"'

def test_getDitaOtPath(resourcesDir):
    os.environ[config.otDirEnvVariable] = os.path.join(resourcesDir, "dita-ot")
    path: str = config.getDitaOtPath()
    assert path is not None, f'Expected to get a value for the OT path'
    assert os.path.exists(path), f'Expected path "{path}" to exist'
    