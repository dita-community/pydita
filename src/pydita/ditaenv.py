"""Provides accessor functions for getting environment details.

- git directory
- operating system
- Jenkins/local

For the git directory, getGitDir() determines the OS-specific default. You can override this
by setting the environment variable "GITDIR" to whatever directory you want.

"""

import os


def isMac() -> bool:
    """Returns true if the current environment is macOS.

    Returns:

        bool: True if running on macOS
    """
    return os.uname().sysname == "Darwin"

def isJenkins() -> bool:
    """Returns true if the current environment is Jenkins (or any Linux).

    Returns:

        bool: True if running on Linux
    """
    return os.uname().sysname == "Linux"

def getGitDir() -> str:
    """Gets the git directory for the current environment.

    Defaults to $HOME/git on macOS and $WORKSPACE on Linux (Jenkins).
    Can be overridden by setting the GITDIR environment variable.

    Returns:

        str: The git directory path, or None if it cannot be determined.
    """
    if os.environ.get("GITDIR") is not None:
        return os.environ.get("GITDIR")
    if isJenkins():
        return os.environ.get("WORKSPACE")
    if isMac():
        return os.path.join(os.environ.get("HOME"), 'git')
    return None

def getGitRelativePath(path: str) -> str:
    """Returns the path relative to the git directory for the specified path.

    Args:

        path (str): Absolute path to relativize

    Returns:

        str: The path relative to getGitDir(), or the original path if the
             git directory cannot be determined.
    """
    gitDir = getGitDir()
    if gitDir is None:
        return path
    return os.path.relpath(path, gitDir)
