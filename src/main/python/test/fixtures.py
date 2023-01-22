"""pytest fixtures for unit tests
"""

import os
import sys
import pytest

@pytest.fixture
def resourcesDir() -> str:
    """Gets the resources directory path for test cases.

    Returns:

        str: The resources directory path
    """
    return os.path.join(os.path.dirname(__file__), "resources")

@pytest.fixture
def rootMap1Path(resourcesDir) -> str:
    """The path to root map 1.

    Returns:

        str: path to the root-map-01.ditamap file.
    """
    return os.path.join(resourcesDir, "dita", "root_map_1.ditamap")

