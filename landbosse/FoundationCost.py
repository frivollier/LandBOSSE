"""
FoundationCost.py
Created by Annika Eberle and Owen Roberts on Apr. 3, 2018

Calculates the costs of constructing foundations for land-based wind projects
(items in brackets are not yet implemented)

Get number of turbines
Get duration of construction
Get daily hours of operation*  # todo: add to process diagram
Get season of construction*  # todo: add to process diagram
[Get region]
Get rotor diameter
Get hub height
Get turbine rating
Get buoyant foundation design flag
[Get seismic zone]
Get tower technology type
Get hourly weather data
[Get specific seasonal delays]
[Get long-term, site-specific climate data]

Get price data
    Get labor rates
    Get material prices for steel and concrete

[Use region to determine weather data,

Calculate the foundation loads using the rotor diameter, hub height, and turbine rating

Determine the foundation size based on the foundation loads, buoyant foundation design flag, and type of tower technology

Estimate the amount of material needed for foundation construction based on foundation size and number of turbines

Estimate the amount of time required to construct foundation based on foundation size, hours of operation,
duration of construction, and number of turbines

Estimate the additional amount of time for weather delays (currently only assessing wind delays) based on
hourly weather data, construction time, hours of operation, and season of construction

Estimate the amount of labor required for foundation construction based on foundation size, construction time, and weather delay
    Calculate number of workers by crew type
    Calculate man hours by crew type

Estimate the amount of equipment needed for foundation construction based on foundation size, construction time, and weather delay
    Calculate number of equipment by equip type
    Calculate equipment hours by equip type

Calculate the total foundation cost based on amount of equipment, amount of labor, amount of material, and price data

"""
import math
import pandas as pd
import numpy as np
import WeatherDelay as WD

# constants
kg_per_tonne = 1000
cubicm_per_cubicft = 0.0283168
steel_density = 9490  # kg / m^3
cubicyd_per_cubicm = 1.30795
ton_per_tonne = 0.907185


def calculate_foundation_loads(component_data):
    """

    :param component_data: data on components (weight, height, area, etc.)
    :param rotor_diam:
    :param hub_height:
    :param turbine_rating:
    :return:
    """

    # set exposure constants
    a = 9.5
    z_g = 274.32

    # get section height
    z = component_data['Section height m']

    # get cross-sectional area
    A_f = component_data['Surface area sq m']

    # get lever arm
    L = component_data['Lever arm m']

    # Equations from Shrestha, S. 2015. DESIGN AND ANALYSIS OF FOUNDATION FOR ONSHORE TALL WIND TURBINES. All Theses. Paper 2291.
    # https: // tigerprints.clemson.edu / cgi / viewcontent.cgi?referer = https: // www.google.com / & httpsredir = 1 & article = 3296 & context = all_theses

    # calculate wind pressure
    K_z = 2.01 * (z / z_g) ** (2 / a)  # exposure factor
    K_d = 0.95  # wind directionality factor
    K_zt = 1  # topographic factor
    V = 70  # critical velocity in m/s
    wind_pressure = 0.613 * K_z * K_zt * K_d * V ** 2

    # calculate wind loads of each component
    G = 0.85  # gust factor
    C_f = 0.8  # coefficient of force
    F = wind_pressure * G * C_f * A_f

    # calculate moment from each component at base of tower
    M = F * L

    # get total lateral load (N) and moment (N * m)
    F_lat = F.sum()
    M_tot = M.sum()

    # calculate dead load in N
    g = 9.8  # m / s ^ 2
    F_dead = component_data['Weight tonne'].sum() * g * kg_per_tonne

    foundation_loads = {'F_dead': F_dead,
                        'F_lat': F_lat,
                        'M_tot': M_tot}

    return foundation_loads


def determine_foundation_size(foundation_loads):
    """
    Calculates the radius of a round, raft foundation
    Assumes foundation made of concrete with 1 m thickness

    :param foundation_loads: dictionary of foundation loads (forces in N; moments in N*m)
    :param buoyant_design: flag for buoyant design - currently unused
    :param type_of_tower: flag for type of tower - currently unused
    :return:
    """

    # get foundation loads and convert N to kN
    F_dead = foundation_loads['F_dead']
    F_lat = foundation_loads['F_lat']
    M_tot = foundation_loads['M_tot']

    foundation_cubic_meters = 1.012 * (0.0000034 * M_tot * (M_tot / (71 * F_lat)) * (M_tot / (20 * F_dead)) + 168) / cubicyd_per_cubicm

    return foundation_cubic_meters


def estimate_material_needs(foundation_volume, num_turbines):
    """
    Estimate amount of material based on foundation size and number of turbines

    :param foundation_volume: volume of foundation material in m^3
    :param num_turbines: number of turbines
    :return: table of material needs
    """

    steel_mass = foundation_volume * 0.012 * steel_density / kg_per_tonne * ton_per_tonne * num_turbines
    concrete_volume = foundation_volume * 0.99 * cubicyd_per_cubicm * num_turbines

    material_needs = pd.DataFrame([['Steel - rebar', steel_mass, 'ton (short)'],
                                   ['Concrete 5000 psi', concrete_volume, 'cubic yards']],
                                  columns=['Material type ID', 'Quantity of material', 'Units'])
    return material_needs


def estimate_construction_time(throughput_operations, material_needs, duration_construction):
    """

    :param material_needs:
    :param duration_construction:
    :return:
    """

    foundation_construction_time = duration_construction * 1/3
    operation_data = pd.merge(throughput_operations, material_needs, on=['Material type ID'])
    operation_data['Number of days'] = operation_data['Quantity of material'] / operation_data['Daily output']
    operation_data['Number of crews'] = np.ceil((operation_data['Number of days'] / 30) / foundation_construction_time)
    operation_data['Cost USD without weather delays'] = operation_data['Quantity of material'] * operation_data['Rate USD per unit']

    # if more than one crew needed to complete within construction duration then assume that all construction happens
    # within that window and use that timeframe for weather delays; if not, use the number of days calculated
    operation_data['time_construct_bool'] = operation_data['Number of days'] > foundation_construction_time * 30
    boolean_dictionary = {True: foundation_construction_time * 30, False: np.NAN}
    operation_data['time_construct_bool'] = operation_data['time_construct_bool'].map(boolean_dictionary)
    operation_data['Time construct days'] = operation_data[['time_construct_bool', 'Number of days']].min(axis=1)

    return operation_data


def calculate_weather_delay(weather_data, season_dict, season_construct, time_construct,
                            duration_construction, start_delay, critical_wind_speed):
    """

    :param weather_data:
    :param season_dict:
    :param season_construct:
    :param time_construct:
    :param duration_construction:
    :param start_delay:
    :param critical_wind_speed:
    :return:
    """

    weather_window = WD.create_weather_window(weather_data=weather_data,
                                              season_id=season_dict,
                                              season_construct=season_construct,
                                              time_construct=time_construct)

    # compute weather delay
    wind_delay = WD.calculate_wind_delay(weather_window=weather_window,
                                         start_delay=start_delay,
                                         mission_time=duration_construction,
                                         critical_wind_speed=critical_wind_speed)
    wind_delay = pd.DataFrame(wind_delay)

    # if greater than 4 hour delay, then shut down for full day (10 hours)
    wind_delay[(wind_delay > 4)] = 10
    wind_delay_time = float(wind_delay.sum())

    return wind_delay_time


def calculate_costs(input_data, num_turbines, construction_time, season_id, season_construct, time_construct):
    """

    :param labor:
    :param equip:
    :param material:
    :param price_data:
    :return:
    """

    foundation_loads = calculate_foundation_loads(component_data=input_data['components'])
    foundation_volume = determine_foundation_size(foundation_loads=foundation_loads)
    material_vol = estimate_material_needs(foundation_volume=foundation_volume, num_turbines=num_turbines)
    material_data = pd.merge(material_vol, input_data['material_price'], on=['Material type ID'])
    material_data['Cost USD'] = material_data['Quantity of material'] * pd.to_numeric(material_data['Material price USD per unit'])

    operation_data = estimate_construction_time(throughput_operations=input_data['rsmeans'],
                                                material_needs=material_vol,
                                                duration_construction=construction_time)

    wind_delay = calculate_weather_delay(weather_data=input_data['weather'],
                                         season_dict=season_id,
                                         season_construct=season_construct,
                                         time_construct=time_construct,
                                         duration_construction=max(operation_data['Time construct days']),
                                         start_delay=0,
                                         critical_wind_speed=13)

    wind_multiplier = 1 + wind_delay / max(operation_data['Time construct days'])

    labor_equip_data = pd.merge(material_vol, input_data['rsmeans'], on=['Material type ID'])
    labor_equip_data['Cost USD'] = labor_equip_data['Quantity of material'] * labor_equip_data['Rate USD per unit'] * wind_multiplier

    print('C')
    foundation_cost = labor_equip_data[['Operation ID', 'Type of cost', 'Cost USD']]

    material_costs = pd.DataFrame(columns=['Operation ID', 'Type of cost', 'Cost USD'])
    material_costs['Operation ID'] = material_data['Material type ID']
    material_costs['Type of cost'] = 'Materials'
    material_costs['Cost USD'] = material_data['Cost USD']

    foundation_cost = foundation_cost.append(material_costs)

    total_foundation_cost = foundation_cost.groupby(by=['Type of cost']).sum().reset_index()
    total_foundation_cost['Phase of construction'] = 'Foundations'

    return total_foundation_cost

