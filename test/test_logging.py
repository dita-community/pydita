"""Test configuration module.
"""

import os
import sys

from .fixtures import resourcesDir, rootMap1Path

import ditalib.logging
from ditalib.logging import Errors, ErrorRecord

def test_readPropertiesFile(resourcesDir):
    assert ditalib.logging.WARN == "warning", f'Expected ditalib.logging.WARN to be "warning", got "{ditalib.logging.WARN}"'
    assert ditalib.logging.ERROR == "error", f'Expected ditalib.logging.ERROR to be "error", got "{ditalib.logging.ERROR}"'
    errors: Errors = Errors()
    assert len(errors.keys()) == 0, f'Expected to have an empty dictionary, got {len(errors.key())}.'
    key: str = "key1"
    errors.logError(key, "Error message 1", severity=ditalib.logging.WARN)
    assert len(errors.keys()) == 1, f'Expected to have 1 key, got {len(errors.key())}.'
    errors.logError(key, "Error message 2")
    assert len(errors.keys()) == 1, f'Expected to have 1 key, got {len(errors.key())}.'
    errorsForKey: list[ErrorRecord] = errors.get(key)
    assert errorsForKey is not None, f'Expected to get a list of errors for key "{key}"'
    assert len(errorsForKey) == 2, f'Expected to have 2 errors in the list, have {len(errorsForKey)}.'
    error: ErrorRecord = errorsForKey[0]
    assert error.getKey() == key, f'Expected key to be "{key}", got "{error.getKey()}"'
    assert error.getSeverity() == ditalib.logging.WARN, f'Expected severity of WARN, got {error.getSeverity()}'
    #err: Exception = error.getException()
    #assert err is not None, f'Expected to have an Exception object.'
    #assert str(err) == "Error message 1", f'Expected exception message "Error message 1", got "{str(err)}"'