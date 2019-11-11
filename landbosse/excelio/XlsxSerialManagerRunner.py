from collections import OrderedDict
import os

import pandas as pd

from ..model import Manager
from .XlsxFileOperations import XlsxFileOperations
from .XlsxReader import XlsxReader
from .XlsxManagerRunner import XlsxManagerRunner
from .XlsxDataframeCache import XlsxDataframeCache


class XlsxSerialManagerRunner(XlsxManagerRunner):
    """
    This subclass implementation of XlsxManagerRunner runs all projects
    in a serial loop.
    """

    def run_from_project_list_xlsx(self, projects_xlsx):
        """
        This function runs all the scenarios in the projects_xlsx file. It creates
        the OrderedDict that holds the results of all the runs. See the return
        section below for more details on what the OrderedDict contains.

        This is a concrete implementation of the super class method.

        Parameters
        ----------
        projects_xlsx : str
            A path name (preferably created with os.path.join()) specific to the
            operating system that is the main input .xlsx file that controls
            running of all the projects. Crucially, this file contains names of
            other. It is recommended that all input file be kept in the same
            input directory. Each line of projects_xlsx becomes a project_series.

        Returns
        -------
        OrderedDict, list, list, list
            First element of tuple is an ordered dict that is the result of
            all the runs. Each key is the name of a project and each value
            is the output dictionary of that project. The second element
            is the list of rows for the csv. The third element is the list
            of costs for the spreadsheets. The fourth element is the same as
            module_type_operation_lists, but every row has all the inputs
            on each row.
        """
        # Load the project list
        # projects = pd.read_excel(projects_xlsx, 'Sheet1')
        project_list, parametric_list = self.read_project_and_parametric_list_from_xlsx()
        print('>>> Project and parametric lists loaded')

        # For file operations
        file_ops = XlsxFileOperations()

        # Get the output dictionary ready
        runs_dict = OrderedDict()

        # Instantiate and XlsxReader
        xlsx_reader = XlsxReader()

        xlsx_reader.create_parametric_value_list(parametric_list, steps=3)

        # Loop over every project
        for _, project_series in project_list.iterrows():
            project_id = project_series['Project ID']
            project_data_basename = project_series['Project data file']

            # Input path for the Xlsx
            project_data_xlsx = os.path.join(file_ops.landbosse_input_dir(), 'project_data', f'{project_data_basename}.xlsx')

            # Log each project
            print(f'<><><><><><><><><><><><><><><><><><> {project_id} <><><><><><><><><><><><><><><><><><>')
            print('>>> project_id: {}'.format(project_id))
            print('>>> Project data: {}'.format(project_data_xlsx))

            # Read the project data sheets.
            project_data_sheets = XlsxDataframeCache.read_all_sheets_from_xlsx(project_data_basename)

            # Create the master input dictionary.
            master_input_dict = xlsx_reader.create_master_input_dictionary(project_data_sheets, project_series)

            # Now run the manager and accumulate its result into the runs_dict
            output_dict = dict()
            mc = Manager(input_dict=master_input_dict, output_dict=output_dict)
            mc.execute_landbosse(project_name=project_id)
            output_dict['project_series'] = project_series
            runs_dict[project_id] = output_dict

        final_result = dict()
        final_result['details_list'] = self.extract_details_lists(runs_dict)
        final_result['module_type_operation_list'] = self.extract_module_type_operation_lists(runs_dict)

        # Return the runs for all the scenarios.
        # return runs_dict, details_list, module_type_operation_list, module_type_operation_list_with_inputs
        return final_result
