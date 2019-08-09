import traceback
import math

from .ManagementCost import ManagementCost
from .FoundationCost import FoundationCost
from .SubstationCost import SubstationCost
from .TransmissionCost import TransmissionCost
from .RoadsCost import RoadsCost
from .CollectionCost import Cable, Array, ArraySystem
from .ErectionCost import ErectionCost
from .DevelopmentCost import DevelopmentCost


class Manager:
    """
    The Manager class distributes input and output dictionaries among
    the various modules. It maintains the hierarchical dictionary
    structure.
    """

    def __init__(self, input_dict, output_dict, log):
        """
        This initializer sets up the instance variables of:

        self.cost_modules: A list of cost module instances. Each of the
            instances must implement the method input_output.

        self.input_dict: A placeholder for the inputs dictionary

        self.output_dict: A placeholder for the output dictionary
        """
        self.input_dict = input_dict
        self.output_dict = output_dict
        self.log = log

    def execute_landbosse(self, project_name):
        try:
            # Create weather window that will be used for all tasks (window for entire project; selected to restrict to seasons and hours specified)
            weather_data_user_input = self.input_dict['weather_window']
            season_construct = self.input_dict['season_construct']
            time_construct = self.input_dict['time_construct']
            daily_operational_hours = self.input_dict['hour_day'][time_construct]

            # Filtered window. Restrict to the seasons and hours specified.
            filtered_weather_window = weather_data_user_input.loc[(weather_data_user_input['Season'].isin(season_construct)) & (weather_data_user_input['Time window'] == time_construct)]
            filtered_weather_window = filtered_weather_window[0:(math.ceil(self.input_dict['construct_duration'] * 30 * daily_operational_hours))]

            # Rename weather data to specify types
            self.input_dict['weather_window'] = filtered_weather_window
            self.input_dict['weather_data_user_input'] = weather_data_user_input

            self.log.debug('Begin foundation cost calculation')
            foundation_cost = FoundationCost(input_dict=self.input_dict, output_dict=self.output_dict, project_name=project_name)
            foundation_cost.run_module()
            self.log.debug('End foundation cost calculation')

            self.log.debug('Begin roads cost calculation')
            roads_cost = RoadsCost(input_dict=self.input_dict, output_dict=self.output_dict, project_name=project_name)
            roads_cost.run_module()
            self.log.debug('End roads cost calculation')

            self.log.debug('Begin substation cost calculation')
            substation_cost = SubstationCost(input_dict=self.input_dict, output_dict=self.output_dict, project_name=project_name)
            substation_cost.run_module()
            self.log.debug('End substation cost calculation')

            self.log.debug('Begin transmission distribution cost calculation')
            transdist_cost = TransmissionCost(input_dict=self.input_dict, output_dict=self.output_dict, project_name=project_name)
            transdist_cost.run_module()
            self.log.debug('End transmission distribution cost calculation')

            self.log.debug('Begin collection cost calculation')
            collection_cost = ArraySystem(input_dict=self.input_dict, output_dict=self.output_dict, project_name=project_name)
            collection_cost.run_module()
            self.log.debug('End collection cost calculation')

            self.log.debug('Begin development cost calculation')
            development_cost = DevelopmentCost(input_dict=self.input_dict, output_dict=self.output_dict,
                                          project_name=project_name)
            development_cost.run_module()
            self.log.debug('End development cost calculation')


            self.log.debug('Begin erection cost calculation')
            erection_cost_output_dict = dict()
            erection_cost = ErectionCost(
                input_dict=self.input_dict,
                output_dict=self.output_dict,
                project_name=project_name,
                log=self.log
            )
            erection_cost.run_module()
            self.output_dict['erection_cost'] = erection_cost_output_dict
            self.log.debug('End erection cost calculation')

            total_costs = self.output_dict['total_collection_cost']
            total_costs = total_costs.append(self.output_dict['total_road_cost'], sort=False)
            total_costs = total_costs.append(self.output_dict['total_transdist_cost'], sort=False)
            total_costs = total_costs.append(self.output_dict['total_substation_cost'], sort=False)
            total_costs = total_costs.append(self.output_dict['total_foundation_cost'], sort=False)
            total_costs = total_costs.append(self.output_dict['total_erection_cost'], sort=False)
            total_costs = total_costs.append(self.output_dict['total_development_cost'],sort=False)

            self.input_dict['project_value_usd'] = total_costs.sum(numeric_only=True)[0]
            self.input_dict['foundation_cost_usd'] = self.output_dict['total_foundation_cost'].sum(numeric_only=True)[0]
            self.log.debug('Begin management cost calculation')
            management_cost = ManagementCost(input_dict=self.input_dict, output_dict=self.output_dict, project_name=project_name)
            management_cost.run_module()
            self.log.debug('End management cost calculation')

            return 0
        except Exception:
            traceback.print_exc()
            return 1  # module did not run successfully