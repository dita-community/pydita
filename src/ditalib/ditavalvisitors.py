"""Vistors that apply to DitavalFilters
"""
import os
import sys

from ditalib import ditaenv

from ditalib.visitor import Visitor
from ditalib.ditaval import DitavalFilter
from ditalib.ditaval import DitavalCondition
from typing import Any, Union
import xlsxwriter

class DitavalVisitor(Visitor):
    """Base class for visitors that visit DitavalFilters

    """

    def __init__(self, debug:bool=False):
        self.debug = debug

    def visit(self, obj: Union[DitavalFilter, DitavalCondition]):
        if self.debug and False:
            print(f'DitavalVisitor.visit(): obj: {obj.__class__}')
        if isinstance(obj, DitavalFilter):
            self.visit_DitavalFilter(obj)
        else: # Must be a condition. For reasons I can't determine isinstance(obj, DitavalCondition) fails.
            self.visit_DitavalCondition(obj)

    def visit_DitavalFilter(self, ditavalFilter: DitavalFilter) -> Any:
        raise NotImplemented("You must implement visit_DitavalFilter()")

    def visit_DitavalCondition(self, ditavalCondition: DitavalCondition) -> Any:
        raise NotImplemented("You must implement visit_DitavalCondition()")

class ExcelGeneratingDitavalVisitor(DitavalVisitor):
    """Generates an Excel spreadsheet from the DITAVAL filter.
    """

    def __init__(self, excelPath: str, debug:bool=False):
        """Construct a new Excel-generating visitor.

        Args:
            excelPath (str): Path to Excel sheet to generate.

        """
        super().__init__(debug=debug)
        self.execlPath = excelPath
        data: dict[str, dict[str, str]] = {}
        self.data = data

    def visit_DitavalFilter(self, ditavalFilter: DitavalFilter):
        """Loads the conditions in the data dictionary.

        Args:

            ditavalFilter (DitavalFilter): DitavalFilter being visited
        """
        if self.debug:
            print(f'[DEBUG] visit_DitavalFilter(): Starting...')
        for condition in ditavalFilter.getConditions():
            self.visit(condition)
        # Make any directories needed to write Excel file:

        print(f'[INFO] Preparing output directory "{os.path.dirname(self.execlPath)}"')
        os.makedirs(os.path.dirname(self.execlPath),exist_ok=True)
        print(f'[INFO] Writing Excel to "{self.execlPath}"')

        # Using xlsxwriter directly rather than Pandas via a data frame
        # because this is simple enough and we'd need to interact with
        # the writer anyway to do more sophisticated styling and such.

        workbook = xlsxwriter.Workbook(self.execlPath)
        worksheet = workbook.add_worksheet("DITAVALs")
        # Make outline visible and put expand/collapse controls at top of outline.
        worksheet.outline_settings(True, False, True, False)
        worksheet.set_zoom(125)

        boldBottomBorder = workbook.add_format({'bold': True})
        boldBottomBorder.set_bottom()
        boldBig = workbook.add_format({'bold': True, 'font_size': 14})
        bold = workbook.add_format({'bold': True})
        notBold = workbook.add_format({'bold': False})

        row: int = 0

        # Give the sheet title a single merged cell:
        worksheet.merge_range(row, 0, row, 3, "DITAVAL Report", boldBig)

        row += 2
        # Write out the files that contributed to the DITAVAL filter:

        if len(ditavalFilter.getDitavals()) > 0:
            worksheet.write(row, 0, "DITAVAL files:", bold)
            for file in ditavalFilter.getDitavals():
                row += 1
                path = file.name
                name = os.path.basename(path)
                relpath = ditaenv.getGitRelativePath(path)
                worksheet.write(row, 0, name)
                # Merge from column 2 to 4 so the path cell has plenty of room
                worksheet.merge_range(row, 1, row, 3, relpath)
            row += 1

        # Make a blank row before the header row
        row += 1
        # Write the Header row:
        worksheet.write(row, 0, "Condition", boldBottomBorder)
        worksheet.write(row, 1, "Value", boldBottomBorder)
        worksheet.write(row, 2, "Action", boldBottomBorder)
        worksheet.freeze_panes(row+1, 0)

        if self.debug:
            print(f'[DEBUG] visit_DitavalFilter(): self.data.keys(): {self.data.keys()}')

        for conditionName in sorted(self.data.keys()):
            if self.debug:
                print(f'[DEBUG] visit_DitavalFilter():   row={row}')
            values: dict[str, str] = self.data[conditionName]
            if self.debug:
                print(f'[DEBUG] visit_DitavalFilter():   values: {values}')
            row += 1

            # Make the first row of each condition outline level 1
            # The first row shows the default action for the condition
            worksheet.set_row(row, None, None, {"level": 0})
            worksheet.write(row, 0, conditionName, bold)
            worksheet.write(row, 1, "Default action", bold)
            worksheet.write(row, 2, values.get("#default"), bold)
            valueList = sorted(values.keys(), key=str.lower)

            groupValues: bool = True if len(valueList) > 20 else False
            # Used to control grouping of long lists. Groups by either
            # the first dash-delimited token of the value name or
            # if there are no dashes, by the first two letters.
            # That seems to group things reasonably well.
            lastToken = None
            outlineLevel: int = 1

            for value in valueList:
                if value == "#default":
                    continue
                row += 1
                tokens: list[str] = value.split("-")
                if len(tokens) > 1:
                    thisToken = value.split("-")[0]
                else:
                    # Use first two characters as the token--that seems
                    # to fit our condition naming pattern reasonbly well.
                    thisToken = value[0:2]
                if groupValues:
                    if thisToken != lastToken:
                        outlineLevel = 1
                    else:
                        outlineLevel = 2
                    lastToken = thisToken
                worksheet.set_row(row, None, None, {"level": outlineLevel})
                worksheet.write(row, 0, conditionName, notBold)
                worksheet.write(row, 1, value, notBold)
                worksheet.write(row, 2, values.get(value), notBold)

        # Autofit the columns:
        worksheet.autofit()

        # Close the workbook. This causes it to be written to disk.
        workbook.close()


    def visit_DitavalCondition(self, ditavalCondition: DitavalCondition):
        """Creates a dictionary of values to actions and adds it to the
        data entry for the condition name.

        Args:
            ditavalCondition (DitavalCondition): _description_
        """
        condDict: dict[str, str] = {}
        self.data[ditavalCondition.getName()] = condDict
        values: dict[str, bool] = ditavalCondition.getValues()
        for valueName in values.keys():
            condDict[valueName] = DitavalCondition.getActionStr(values[valueName])
