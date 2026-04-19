"""Visitors that operate on key spaces.
"""

import os
import sys
from copy import copy, deepcopy
from typing import Any, Union

from lxml import etree
from lxml.etree import Element
from lxml.etree import ElementTree

from pydita import xmlutils
from pydita import ditaenv

from pydita import ditautils
from pydita.visitor import Visitor
from pydita.visitor import Visitable

from pydita.keyspace import KeyDefinition
from pydita.keyspace import KeySpace

from anytree import RenderTree

import xlsxwriter

class KeyspaceVisitor(Visitor):
    """Base class for keyspace visitors.
    """

    def __init__(self, debug:bool=False):
        self.debug = debug

    def visit(self, obj: object) -> None:
        """Visit an object.

        Dispatches the appropriate type-specific visitor method.

        Args:

            obj (object): object to be visited
        """
        if isinstance(obj, KeySpace):
            self.visitKeySpace(obj)
        elif isinstance(obj, KeyDefinition):
            self.visitKeyDefinition(obj)
        else:
            super().visit(obj)


    def visitKeySpace(self, keySpace: KeySpace) -> None:
        """Visit a KeySpace object.

        Args:

            keySpace (KeySpace): The key space being visited.

        """
        raise NotImplementedError("You must implement visitKeySpace()")

    def visitKeyDefinition(self, keyDef: KeyDefinition) -> None:
        """Visit a KeyDefinition object.

        Args:

            keyDef (KeyDefinition): The key definition being visited.

        """
        raise NotImplementedError("You must implement visitKeyDefinition()")

class PullUpVisitor(KeyspaceVisitor):
    """Applies pull-up processing to a key space by walking the key space tree.
    """

    def __init__(self, debug:bool=False):
        super().__init__(debug=debug)
        self.collectedKeyDefsStack = []
        self.collectedKeyDefsStack.append([])

    def visitKeyDefinition(self, keyDef: KeyDefinition):
        pass

    def visitKeySpace(self, keySpace: KeySpace) -> None:
        # Pull the space-qualified names of child spaces
        # up into this space.
        collectedKeyDefs = []
        if len(keySpace.children) > 0:
            self.collectedKeyDefsStack.append([])
            # Process the child key spaces
            for child in keySpace.children:
                child.accept(self)
            # Get the keydefs collected from desendants
            collectedKeyDefs = self.collectedKeyDefsStack.pop()
        # Now apply any collected keydefs:
        for keydef in collectedKeyDefs:
            keySpace.addKeyDefinition(keydef)
        collectedKeyDefs = self.collectedKeyDefsStack[-1]
        # Now collect the key space's keydefs,
        # adding its key scopes to the key names
        for keyDef in keySpace.getKeyDefinitions():
            for scopeName in keySpace.getScopeNames():
                # Don't collect keys for the annonymous scope
                if scopeName == "#annonymous":
                    continue
                newKey = scopeName + "." + keyDef.getKeyName()
                newKeydef = copy(keyDef)
                newKeydef.setKeyName(newKey)
                collectedKeyDefs.append(newKeydef)
        # Special case for root key space: Add keydefs qualified
        # with the root's own scope name.
        if keySpace.parent is None:
            for keydef in collectedKeyDefs:
                keySpace.addKeyDefinition(keydef)


class PushDownVisitor(KeyspaceVisitor):
    """Applies push down processing to a key space by walking the key space tree.
    """

    def __init__(self, debug:bool=False):
        super().__init__(debug=debug)

    def visitKeySpace(self, keySpace: KeySpace) -> None:
        # For each child key space, add this key space's
        # keys, then visit each child.
        for child in keySpace.getChildSpaces():
            child.addKeyDefinitions(keySpace.getKeyDefinitions())
        for child in keySpace.getChildSpaces():
            self.visit(child)

    def visitKeyDefinition(self, keyDef: KeyDefinition):
        pass

class KeyspaceReportingVisitor(KeyspaceVisitor):
    """Generates a report from a key space
    """

    def __init__(self, debug:bool=False):
        super().__init__(debug=debug)
        self.lines = []

    def visitKeySpace(self, keySpace: KeySpace) -> None:
        # Show to the key definitions in this space
        # then visit any child key spaces
        self.lines.append(f'-------------------------------------------------')
        self.lines.append(f'Key space: {", ".join(keySpace.getScopeNames())}')
        self.lines.append(f'')
        self.lines.append(f'  Space defining element:')
        keyScope = keySpace.getSpaceDefiner().get("keyscope")
        keyScopeAttr = ""
        if keyScope is not None:
            keyScopeAttr = f' keyscope="{keyScope}"'
        self.lines.append(f'      <{keySpace.getSpaceDefiner().tag}{keyScopeAttr}>')
        self.lines.append(f'')
        self.lines.append(f'Key definitions:')
        for keyDef in sorted(keySpace.getKeyDefinitions(), key=lambda keydef: keydef.getKeyName()):
            self.visit(keyDef)
        children = keySpace.getChildSpaces()
        if len(children) > 0:
            self.lines.append(f'')
            self.lines.append(f'Child key spaces:')
            for child in children:
                self.visit(child)
        self.lines.append(f'-------------------------------------------------')

    def visitKeyDefinition(self, keyDef: KeyDefinition) -> None:
        """Report a single key definition

        Args:

            keyDef (KeyDefinition): Key definition to be reported.
        """
        self.lines.append(f'+ [{keyDef.getKeyName()}] Has {len(keyDef.getKeyDefiners())} key-defining elements.')
        pos = 0
        for topicref in keyDef.getKeyDefiners():
            pos += 1
            self.visitTopicref(topicref, pos)

    def visitTopicref(self, topicref: Element, pos: int) -> None:
        """Report the relevant details for a key-defining topicref

        Args:

            topicref (Element): Topicref element (class="- map/topicref ... ")
        """
        keysValue = topicref.get("keys")
        if keysValue is None:
            return
        self.lines.append(f'  {"%2s" % pos}. {topicref.tag}:')
        self.lines.append(f'      keys: {", ".join(keysValue.split())}')
        for attName in ["href", "keyref", "format", "scope", "product", "deliveryTarget", "processing-role", "otherprops"]:
            value = topicref.get(attName)
            if value is not None:
                self.lines.append(f'      {attName}: {value}')
        if topicref.get("href") is None and topicref.get("keyref") is None:
            linkText = xmlutils.getKeydefLinkTextString(topicref)
            self.lines.append(f'      Link text: "{linkText}"')




    def reportKeySpace(self, keySpace: KeySpace) -> str:
        """Generates a report for a key space

        Args:

            keySpace (KeySpace): The root key space to be reported.

        Returns:

            str: The report as a multiline string.
        """
        self.lines.append(f'')
        self.lines.append(f'Key space tree:')
        self.lines.append(f'')
        self.lines.append(RenderTree(keySpace).by_attr("label"))
        self.lines.append(f'')
        self.lines.append(f'Key definitions report:')
        self.lines.append(f'')
        self.visit(keySpace)
        return "\n".join(self.lines)

class ExcelGeneratingKeyspaceVisitor(KeyspaceVisitor):
    """Generates an Excel spreadsheet from a key space
    """

    def __init__(self, outDir: str, debug:bool=False):
        """Excel-generating visitor

        Args:

            outDir (str): Directory to write the Excel sheet to.

            debug (bool, optional): Controls debug logging. Defaults to False.
        """
        super().__init__(debug=debug)

        self.outDir = outDir
        # Will be set by the root keyspace visitor.
        self.excelPath = None
        # Maintains the current row to write to
        self.row = 0
        # Used to group key definitions by tokens within the key names
        #
        self.lastToken = None
        # The current level to set on rows:
        self.currentLevel = 0
        self.keySpaceLevel = 0
        self.keyDefLevel = 1

    def visitKeySpace(self, keySpace: KeySpace) -> None:
        if self.debug:
            print(f'[DEBUG] visitKeySpace(): Starting, keyscopes: {keySpace.getScopeNames()}')
        # For reasons I do not understand, the keySpace variable is not root after
        # processing all the child spaces, but setting this variable for the root
        # map works to correctly detect that we are in the call of this method
        # for the root map so we can finalize the spreadsheet and close it.
        rootSpace: KeySpace = None
        if keySpace.is_root:
            # If this is the root key space, set up the worksheet using the base URI
            # of the root map, which will be the definer for the key space.
            name = os.path.basename(keySpace.getSpaceDefiner().base).split(".")[0]
            print(f'[INFO] Preparing output directory "{self.outDir}"')
            os.makedirs(self.outDir,exist_ok=True)
            self.excelPath: str = os.path.join(self.outDir, f'{name}_keyspace.xlsx')
            print(f'[INFO] Construcing Excel report for root map "{keySpace.getSpaceDefiner().base}"...')
            rootSpace = keySpace
            # Construct the Excel directly using xlsxwriter so we have
            # full control over the details.
            self.workbook = xlsxwriter.Workbook(self.excelPath)
            self.worksheet = self.workbook.add_worksheet("Root Key Space")
            self.row = self._create_sheet_header_rows(keySpace, self.row)
        else:
            # Do whatever subspaces need to do
            pass

        self.worksheet.set_row(self.row, None, None, {"level": self.currentLevel})
        scopeNames: str = str(keySpace.getScopeNames())
        self.worksheet.write(self.row, 0, scopeNames)
        self.row += 1

        if self.debug:
            print(f'[DEBUG] visitKeySpace():   Visiting key definitions...')
        self.currentLevel += 1
        keyDefs: list = keySpace.getKeyDefinitions(sortKeys=True)
        for keyDef in keyDefs:
            keyName = keyDef.getKeyName()
            # Group the keydefs by token (scope qualified) or letter group
            # Get all but the last dot-delimited token.
            # If there are no "dots" (not scope qualified)
            # then groupingToken will be an empty string
            # This makes the full scope qualifier the grouping token.
            groupingToken: str = ".".join(keyName.split(".")[0:-1])
            if groupingToken == "":
                groupingToken = keyName[0].lower()
            print(f'[DEBUG] groupingToken={groupingToken}, lastToken="{self.lastToken}')
            if groupingToken != self.lastToken:
                print(f'[DEBUG] groupingToken={groupingToken}')
                self.keyDefLevel = self.keySpaceLevel + 1
            else:
                # Must be part of a group.
                self.keyDefLevel = self.keySpaceLevel + 2
            self.lastToken = groupingToken
            self.visitKeyDefinition(keyDef)
        self.currentLevel -= 1

        if self.debug:
            print(f'[DEBUG] visitKeySpace():   Visiting child spaces...')
        for keySpace in keySpace.getChildSpaces():
            self.visit(keySpace)

        if self.debug:
            print(f'[DEBUG] visitKeySpace(): At end, keyscopes: {str(keySpace.getScopeNames())}')
            print(f'[DEBUG] visitKeySpace(): At end, keySpace.is_root: {keySpace.is_root}')

        if rootSpace is not None:
            # Autofit the columns:
            self.worksheet.autofit()
            print(f'[INFO] Writing Excel to "{self.excelPath}"')
            self.workbook.close()
            print(f'[INFO] Done.')

    def visitKeyDefinition(self, keyDef: KeyDefinition) -> None:
        keyName = keyDef.getKeyName()
        definer = keyDef.getKeyDefiner()
        type: str = "Variable (String)" if keyDef.isStringKey() else None
        resource: str = None
        if type is None:
            scope: str = definer.get("scope")
            href: str = definer.get("href")
            format: str = definer.get("format")
            if scope is not None and scope == "external":
                type = "External"
            elif format is None or format == "dita":
                type = "Topic"
            else:
                # Must be an image key
                type = "Image"

        resource = keyDef.resolveToResource()

        self.worksheet.set_row(self.row, None, None, {"level": self.keyDefLevel})
        col: int = 1
        self.worksheet.write(self.row, col, keyName)
        col += 1
        self.worksheet.write(self.row, col, type)
        col += 1
        # Get the resource
        resource = keyDef.resolveToResource()
        resourceDetails = self._renderResource(keyDef, resource)
        self.worksheet.write(self.row, col, resourceDetails)
        col += 1
        path = None if not etree.iselement(resource) else resource.base
        relPath: str = "No resource file" if path is None else ditaenv.getGitRelativePath(path)
        self.worksheet.write(self.row, col, relPath)
        col += 1
        self.worksheet.write(self.row, col, len(keyDef.getKeyDefiners()))
        col += 1
        definersStrs: list = []
        for definer in keyDef.getKeyDefiners():
            definersStr = etree.tostring(definer, encoding="unicode").strip()
            if len(definersStr) > 20:
                definerStr = definersStr[0:20]
            definersStrs.append(definersStr)

        self.worksheet.write(self.row, col, ", ".join(definersStrs))
        col += 1
        self.row += 1

    def _renderResource(self, keyDef: KeyDefinition, resource: Element) -> str:
        """Render a keydefs resource to an appropriate string.

        Args:

            resource (Element): The resource element

        Returns:
            str: String for the resource
        """

        result: str = ""

        if resource is None:
            result = "{Resource not resolved}"
        elif etree.iselement(resource):
            if resource.get("keys"):
                # Must be a key definition
                result = etree.tostring(resource, pretty_print=True, encoding="unicode").strip()
            else:
                elem = resource
                tag = resource.tag
                label = ""
                # Get the appropriate element to report
                if tag in ["concept", "task", "reference", "topic"]:
                    title = resource.find("title")
                    elem = deepcopy(title)
                    label = f'{tag}: '

                keySpace: KeySpace = keyDef.getKeySpace()
                ditautils.resolveStringKeyrefs(elem, keySpace, keyDef.getKeyDefiner())
                result = f'{label}{xmlutils.getElementText(elem)}'
        else:
            result = f'Unrecognized resource: {resource}'

        return result

    def _create_sheet_header_rows(self, keySpace: KeySpace, row:int) -> int:
        """Creates the initial title and informational rows for
        the work sheet.

        Returns:

            int: The number of the next row to add to.
        """
        # Make outline visible and put expand/collapse controls at top of outline.
        self.worksheet.outline_settings(True, False, True, False)
        self.worksheet.set_zoom(125)

        # Just making the formats class members--no reason to be more sophisticated.
        self.boldBottomBorder = self.workbook.add_format({'bold': True})
        self.boldBottomBorder.set_bottom()
        self.boldBig = self.workbook.add_format({'bold': True, 'font_size': 14})
        self.bold = self.workbook.add_format({'bold': True})
        self.notBold = self.workbook.add_format({'bold': False})

        path = keySpace.getSpaceDefiner().base
        name = os.path.basename(path)
        relpath = ditaenv.getGitRelativePath(path)

        # Give the sheet title a single merged cell:
        self.worksheet.merge_range(row, 0, row, 3, f'Key Space Report for {name}', self.boldBig)

        row += 2
        # Write out the root map details

        self.worksheet.write(row, 0, "Root Map:")
        self.worksheet.merge_range(row, 1, row, 4, relpath)
        row += 1

        # Make a blank row before the header row
        row += 1
        # Write the Header row:
        col: int = 0
        self.worksheet.write(row, col, "Key Scopes", self.boldBottomBorder)
        col += 1
        self.worksheet.write(row, col, "Key Name", self.boldBottomBorder)
        col += 1
        self.worksheet.write(row, col, "Resource Type", self.boldBottomBorder)
        col += 1
        self.worksheet.write(row, col, "Resource", self.boldBottomBorder)
        col += 1
        self.worksheet.write(row, col, "Resource File", self.boldBottomBorder)
        col += 1
        self.worksheet.write(row, col, "Definition Count", self.boldBottomBorder)
        col += 1
        self.worksheet.write(row, col, "Definers", self.boldBottomBorder)
        col += 1
        self.worksheet.freeze_panes(row+1, 0)
        row += 1
        return row
