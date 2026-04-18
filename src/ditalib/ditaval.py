"""Implements support for the DITA DITAVAL features.

Enables reading DITAVAL files and using them for filtering
DITA elements.
"""

import re

from typing import Union
from io import IOBase
from lxml import etree
from lxml.etree import Element, ElementTree

from ditalib.loggingutils import ErrorRecord, recordError
from ditalib import xmlutils
from ditalib.visitor import Visitor, Visitable

class DitavalCondition(Visitable):
    """Manages the details for a single condition.

    Holds the configuration details from the DITAVAL
    files or the equivalent filtering configuration.

    """

    def __init__(self, conditionName: str, debug:bool=False):
        """Constructs an initial Condition for the specified condition name.

        Args:

            conditionName (str): The condition name, i.e., "product" or "deliveryTarget".
                Corresponds to the name of a conditional attribute or @props named group.
        """
        self._conditionName = conditionName
        # Dictionary of value tokens to include/exclude (True/False) values
        # Special value "#default" captures the default include/exclude value.
        valueDict: dict[str, bool] = {'#default' : True}
        self._valueDict = valueDict
        self._debug = debug

    def __str__(self) -> str:
        result: str = f'Condition[{self._conditionName}]: {self._valueDict}'
        return result

    def isIncluded(self, value: str) -> bool:
        """Detrmine if the value is included (True) or excluded (False) for this condition.

        Args:

            value (str): The condition value to check, i.e, "pdf", "product-01"

        Returns:

            bool: True (include) if the condition evaluates to True for the value.
        """
        result: bool = self._valueDict.get(value)
        if result is None:
            result = self.getDefault()
        return result

    def isExcluded(self, value: str) -> bool:
        """Detrmine if the value is included (True) or excluded (False) for this condition.

        Args:

            value (str): The condition value to check, i.e, "pdf", "product-01"

        Returns:

            bool: True (include) if the condition evaluates to True for the value.
        """
        return not self.isIncluded(value)

    def getName(self) -> str:
        return self._conditionName

    def addValue(self, valueName: str, include: bool) -> None:
        """Add a new value for the condition.

        If the value is already defined, the old value is replaced
        by the new value. This reflects the priority implication
        for DITAVAL files, where later DITAVAL files can override
        newer DITAVAL files.

        Per the DITA 2.0 specification, it's an error to have the
        same att/action or att/action/value tuple defined twice
        in the same DITAVAL file. It's up to the DITAVAL XML
        processor to check that.

        Args:
            valueName (str): _description_
            include (bool): _description_
        """
        self._valueDict[valueName] = include

    def getValues(self) -> dict:
        """Gets the dictionary of values to action boolean

        Returns:
            dict[str, bool]: Dictionary of value names to boolean (include/exclude)
        """
        return self._valueDict.copy()

    def setDefaultAction(self, include:bool) -> bool:
        """Sets the default for the condition.

        Args:

            include (bool): Indicates whether the default is include (True) or exclude (False).

        Returns:

            bool: The new default value
        """
        self._valueDict['#default'] = include
        return self.getDefault()

    def getDefault(self) -> bool:
        """Gets the default include/excldue value for the condition.

        Returns:

            bool: The default include/exclude
        """
        return self._valueDict['#default']

    def getActionStr(action: bool) -> str:
        """Gets the string representation of the action, one of "include" or "exclude"

        Args:

            action (bool): True or False

        Returns:

            str: "include" or "exclude"
        """
        if action:
            return "include"
        else:
            return "exclude"

    def report(self) -> str:
        """Generate a simple string report of the condition.

        Returns:

            str: Multi-line string report of the condition.
        """
        lines: list[str] = [f'Condition "{self.getName()}"']
        lines.append(f'  Default action: {DitavalCondition.getActionStr(self.getDefault())}')
        for value in self._valueDict.keys():
            lines.append(f'  + {"%10s" % value}: {DitavalCondition.getActionStr(self._valueDict[value])}')
        return "\n".join(lines)


class DitavalFilter(Visitable):
    """Filters DITA elements using zero or more DITAVAL files.
    """

    # Set of known condition names.
    # Note: This does not include @props as that is a separate
    #       case and is not, itself, a condition.
    builtInConditions: list[str] = [
        "audience",
        "deliveryTarget",
        "otherprops",
        "platform",
        "product",
        "rev"
    ]

    def __init__(self,
        ditavalFiles:list=[],
        errors:dict={},
        debug:bool=False
        ):
        """Create a new DitavalFilter from zero or more DITAVAL files.

        Args:

            ditavalFiles (list[Union[str, IOBase]]): The DITAVAL files to use for filtering.
                Defaults to [].

            errors (dict[str, ErrorRecord], optional): Error container. Defaults to {}.

            debug (bool, optional): Controls debug logging. Defaults to False.
        """
        self._errors = errors
        self._debug:bool=debug
        self._defaultAction = None
        # Condition names that are known to this filter. Start
        # with built-in condition names and add as needed based
        # on what's in the DITAVAL or from some other source.
        self._condition_names: list[str] = self.builtInConditions.copy()
        # Condition objects by condition name
        self._conditions: dict[str, DitavalCondition] = {}

        self._ditavalFiles = [];
        for file in ditavalFiles:
            if isinstance(file, IOBase):
                self._ditavalFiles.append(file)
            elif isinstance(file, str):
                # Attempt to open the file
                try:
                    f: IOBase = open(file, 'r')
                    self._ditavalFiles.append(f)
                except Exception as err:
                    recordError(errors, file, err, operation="DitavalFilter: Open DITAVAL file")
            else:
                msg = f'DitavalFilter(): Unexpected item: "{file}"'
                if debug:
                    print(f'[DEBUG] {msg}')
                recordError(errors, file, Exception(msg), operation="DitavalFilter: Process ditavalFiles parameter", severity="WARN")

        # Now parse the DITAVAL files
        self._ditavalDocs: list[ElementTree] = []
        for file in self._ditavalFiles:
            try:
                doc: ElementTree = etree.parse(file, xmlutils.getNoDTDParser())
                self._ditavalDocs.append(doc)
            except Exception as err:
                if debug:
                    print(f'[DEBUG] DitavalFilter(): Exception parsing {file.name}:')
                    print(err)
                recordError(errors, file, err, operation="DitavalFilter: Parse DITAVAL file")

        if debug:
            print(f'[DEBUG] DitavalFilter(): Parsed DITAVAL docs:')
            for doc in self._ditavalDocs:
                print(etree.tostring(doc, pretty_print=True, encoding="unicode"))
        # Set up the filter by importing the DITAVAL docs:
        _importDitavalFiles(self)

    def getDitavals(self) -> list:
        """Get the DITAVAL files this filter is configured with.

        Returns:

            list[IOBase]: List, possibly empty, of DITAVAL files as file objects.
        """

        return self._ditavalFiles

    def getConditions(self) -> list:
        """Gets the DitavalCondition objects for this filter

        Returns:

            list[DitavalCondition]: The DitavalCondition objects
        """
        return list(self._conditions.values()).copy()

    def getCondition(self, conditionName: str) -> DitavalCondition:
        """Get the specified condition, if it is available in the filter.

        Args:
            conditionName (str): The name of the condition to get.

        Returns:
            DitavalCondition: The DitavalCondition, if present, or if condition is not present.
        """
        condition: DitavalCondition = self._conditions.get(conditionName)
        if condition is None:
            condition = self.addCondition(conditionName)
        return condition

    def isIncluded(self, elem: Element) -> bool:
        """Determines if the specified element is included by this filter.

        Args:

            elem (Element): The element to evaluate.

        Returns:

            bool: True if the element is not excluded by the filter.
        """
        conditions: dict = self._getConditionsFor(elem)
        result: bool = self.getDefaultAction()

        # Within a condition, values are ORed.
        # Separate conditions are ANDed.
        # Thus, for audience="foo bar", if either foo or bar is included
        # audience resolves to True. If another condition product has
        # only an excluded value, it resolves to False so the final
        # result is True AND False, so False (element is exluded)
        # For each condition, evaluate each value against the DITAVAL spec:

        andItems: list[bool] = []
        for condition_name in conditions.keys():

            orItems: list[bool] = []
            condition: DitavalCondition = self._conditions.get(condition_name)
            if condition is None:
                andItems.append(self.getDefaultAction())
                continue
            # We have a good condition, check all the values
            # specified on the element.
            for value in conditions[condition_name]:
                orItems.append(condition.isIncluded(value))

            # any() returns True if any of the items in the list
            # evaluate to True:
            orValue: bool = any(orItems)
            andItems.append(orValue)

        # all() does the logical AND of the items, returning True IFF all
        # the items in the list are True.
        result: bool = all(andItems)
        return result

    def isExcluded(self, elem: Element) -> bool:
        """Determines if the specified element is excluded by this filter.

        Args:

            elem (Element): The element to evaluate.

        Returns:

            bool: True if the element is excluded by the filter.
        """
        return not self.isIncluded(elem)


    def getConditionNames(self) -> list:
        """Gets the list of condidtion names this filter knows about.

        Returns:

            list[str]: List of condition names. Elements are evaluated against
                       these conditions.
        """
        return self._condition_names

    def _getConditionsFor(self, elem: Element) -> dict:
        pass
        """Get the condition specified on the element as conditional attributes.

        Arguments:

            elem (Element): The element to get the conditions from.

        Returns:

            dict[str, list[str]]: Dictionary of condition names to specified values

        """
        result: dict =  {}

        propsValue: str = elem.get("props")
        if propsValue is not None and propsValue.strip() != "":
            result = parse_props_value(propsValue)

        for condition in self.getConditionNames():
            attValue = elem.get(condition)
            if attValue is not None and attValue != "":
                result[condition] = attValue.split()


        return result

    def addCondition(self, conditionName: str) -> DitavalCondition:
        """Add a condition to the filter for the specified condition name.

        If a Condition with the name already exists, returns it.

        Args:

            conditionName (str): The condition name, i.e., "product"

        Returns:

            Condition: The Condition with the name condition_name.
        """
        if self._conditions.get(conditionName) is None:
            self._conditions[conditionName] = DitavalCondition(conditionName, debug=self.getDebug())
            # Inherit the filter-level default action.
            self._conditions[conditionName].setDefaultAction(self.getDefaultAction())
        return self._conditions.get(conditionName)

    def getDebug(self) -> bool:
        return self._debug

    def getErrors(self) -> dict:
        return self._errors

    def getDefaultAction(self) -> bool:
        """Gets the default action value for the filter.

        Returns:

            bool: The default include value (True or False)
        """
        if self._defaultAction is not None:
            return self._defaultAction
        # The built-in default is Include
        return True

    def setDefaultAction(self, include:bool) -> bool:
        """Sets the default for the filter (<prop> with just @action).

        Per the DITA spec, only the first default action should be
        effective.

        Args:

            include (bool): Indicates whether the default is include (True) or exclude (False).

        Returns:

            bool: The new default value
        """

        if self._defaultAction is not None:
            self._defaultAction = include
        return self.getDefaultAction()

    def report(self) -> str:
        """Produces a simple text report of the filter

        Returns:

            str: A multi-line string with the report
        """
        lines: list[str] = [f'DitavalFilter Report for filter {self}']
        lines.append(f'')
        lines.append(f'Known condition names: {self._condition_names}')
        lines.append(f'')
        lines.append(f'Filter-level default action is "{"exclude" if not self.getDefaultAction() else "include"}"')
        lines.append(f'')
        lines.append(f'DITAVAL files:')
        for file in self._ditavalFiles:
            lines.append(f' + {file.name}')
        lines.append(f'')
        lines.append(f'Have {len(self._conditions.keys())} defined conditions: {self._conditions.keys()}')
        for cond in self._conditions.values():
            lines.append('')
            lines.append(cond.report())
        return "\n".join(lines)

def parse_props_value(propsValue: str, debug:bool=False) -> dict:
    """Parse the value of a @props attribute into a dictionary of
    conditions and values.

    Args:

        propsValue (str): Value of a @props attribute. Must use the
                          generalization syntax: "cond(value1 value2)"

    Returns:

        dict[str, list[str]]: Dictionary of condition values by condition name
    """

    # Use a raw string (r'') for regular expressions so we don't have to do
    # double escapes.
    pattern: re.Pattern = re.compile(r'(\w+)\(([^)]+)\)')

    if debug:
        print(f'[DEBUG] parse_props_value(): pattern="{pattern.pattern}"')

    result: dict = {}

    if pattern.match(propsValue):
        for mo in re.finditer(pattern, propsValue):
            condition: str = mo.group(1)
            values: list[str] = []
            if result.get(condition):
                values.extend(result.get(condition))
            values.extend(mo.group(2).split())
            result[condition] = values
    return result

def filterElement(elem, filter: DitavalFilter, debug:bool=False) -> Element:
    """Apply a filter to an element and its descendants. Updates in place.

    Apply this function to the root element of a document to filter the
    entire document.

    Args:
        elem (Element|ElementTree): The element or document to be filtered.
        filter (DitavalFilter): The filter to apply

    Return:
        The filtered result. This provides the ability to return None when the
        input element itself is filtered out. Otherwise the element is updated
        in place and the input element or document is returned with any filtering applied to it.
    """

    # If we were given an ElementTree, get the root element

    if elem.__class__.__name__.startswith("_ElementTree"):
        if debug:
            print(f'[DEBUG] filterElement(): elem is an ElementTree, getting the root element')
        elem = elem.getroot()


    # First, see if any ancestors are filtered out

    for ancestor in elem.iterancestors():
        if filter.isExcluded(ancestor):
            if debug:
                print(f'[DEBUG] filterElement(): Input element {elem.tag} is filtered out by an ancestor')
            # Input element is filtered out, so we're done


    if filter.isExcluded(elem):
        if debug:
            print(f'[DEBUG] filterElement(): Input element {elem.tag} is filtered out')
        # Input element is filtered out, so we're done
        return None

    # Input element is not filtered out, so check its descendants:
    attribues: list[str] = [f'@{name}' for name in filter.getConditionNames()]
    attSelector: str = " | ".join(attribues)
    xpath: str = f'//*[{attSelector}]'
    conditionalElements: list[Element] = elem.xpath(xpath)

    for cand in conditionalElements:
        # Probably causes an exception to remove an element whose ancestor
        # has been removed, so just catch those and go on.
        try:
            if (filter.isExcluded(cand)):
                if debug:
                    print(f'[DEBUG] filterElement(): Element {cand.tag} is excluded')
                xmlutils.removeElement(cand)
        except Exception as e:
            if debug:
                print(f'[DEBUG] filterElement(): Exception removing element: {e}')
    return elem

def _importDitavalFiles(filter: DitavalFilter) -> None:
    """Process the filter's DITAVAL files to capture the condition details."""

    if filter.getDebug():
        print(f'[DEBUG] _importDitavalFiles(): Starting...')
    for doc in filter._ditavalDocs:
        if filter.getDebug():
            print(f'[DEBUG] _importDitavalFiles(): Processing DITAVAL doc "{doc.getroot().base}"...')
        props: Element = doc.getroot().findall("prop")
        if props is None:
            if filter.getDebug():
                print(f'[DEBUG] _importDitavalFiles():   No <prop> elemements in doc.')
            continue

        if filter.getDebug():
            print(f'[DEBUG] _importDitavalFiles():   Have {len(props)} <prop> elements')
        for prop in props:
            # The @action attribute is required by the DITAVAL spec
            # If it's not present have to bail
            action: str = prop.get("action")
            if action is None or action.strip() == "":
                if filter.getDebug():
                    print(f'[DEBUG] _importDitavalFiles():   <prop> element has no @action attribute: {etree.tostring(prop, encoding="unicode", pretty_print="True")}')
                continue
            att: str = prop.get("att")
            value: str = prop.get("val")

            include_action: bool = action.strip() in ("include", "flag")

            if att is not None:
                cond: DitavalCondition = filter.addCondition(att.strip())
                if value is not None:
                    cond.addValue(value, include_action)
                else:
                    cond.setDefaultAction(include_action)
            else:
                filter.setDefaultAction(include_action)
    if filter.getDebug():
        print(f'[DEBUG] _importDitavalFiles(): DITAVAL files imported:')
        print(filter.report())
