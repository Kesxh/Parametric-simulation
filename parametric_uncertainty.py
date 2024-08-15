"""
==================================
Parametric uncertainty simulations
==================================

Module description
------------------
Parametric simulation tool for uncertainty analyses; requires parametric_utils.py

This script operates on the current model. The script generates a list of unique
simulations based on combinations of one variable taken from each of the lists of
independent model changes. If you want the current model state to be included as a
baseline include it in the lists at index[0].

Large numbers of simulations can be generated. Plan each analysis; consider a series of
considered analyses rather one big one with every possible variable e.g. geometry or
shades or systems etc. Decide which output metric(s) will be used to define 'best'.

The lists of independent model changes are defined by the user; these are of
two types: numeric or by-reference. Examples are given in the script. Take care not to
define independent model changes that have no value e.g. changing glazing % and shade
size independently or changing asp files & ap systems.

The script can be used for compliance actual/proposed etc models.

The script outputs a csv file containing the scenario run #, model changes and multiple
output metrics; this is saved after each iteration so that the results are safe should
a simulation error occur. The csv can be viewed & processed in Excel e.g. using sort.
The csv can be edited e.g. deleting the control row or output metric columns that are
not wanted then parallel coordinate charted using parallel_chart.py,
TM_54_uncertainty_chart.py and TM_54_range_of_outcomes_chart.py.

Notes
-----
Metric units only

Setup a model with templates, constructions, air exchanges, gains, ApSys or ApHVAC
systems, local shades, parametric or freestanding PV panels etc. Set inner volumes
representation (this affects returned floor area; UK Part L = OFF). Create new items
(constructions, gains, air exchanges, asp / ap systems etc.) in the VE to reference
from the parametric change lists. If you are changing shades name them appropriately
in Model-iT so that they will work with the function (north, south, east, west
(lower case matters)).

Set apache simulation options; unless overwritten by the script (asp file) these are
used by all the sims so set HVAC, Suncast, RadianceIES & Macroflo options and make sure
your setpoints for multiple parameter options are set so that clashes do not occur. For
UK Compliance sim options are set within UK Compliance view not in Apache.

We advise using a 6 min simulation step to avoid thermal instability issues. Try running
some check simulations before running parametric simulations; ensure that the model works
before committing to mass simulations. For UK Compliance the TER will be visible in
compliance view following sims.

In the main loop section:
- Define the output metrics required
- Define the parametric input lists ; comment-out input lines to be excluded
- Set the simulation route
- Set if you want room & system sizing runs
- Set the model to edit (normally the real model)
- Remember to set the options on the Apachesim dialog!

Decide if you do not want to delete each aps/asp file after each iteration; comment-out.
If you do not delete each aps/asp file before you repeat a parametric simulation on the
same project you must manually delete the previous parametric aps/asp (Vista folder)
files.

The script will archive the model before making any changes.

"""

import os
import iesve
import importlib
import utils_parametric as utils_parametric
from datetime import datetime
from pathlib import Path

# Reload pu to pick up any edits in the current session
importlib.reload(utils_parametric)

# Main loop
if __name__ == "__main__":

    # Get the current project
    project = iesve.VEProject.get_current_project()

    # Archive the project before we run parametric changes to the model
    print('Archiving project ...')
    project_folder = project.path
    #time_stamp = datetime.now().strftime("%d%m%Y_%H%M%S")
    #path = Path(project_folder, 'Backups', f'{project.name}_{time_stamp}.cab')
    #project.archive_project(str(path), False)
    print('Project archived to project backups folder')

    ### Define the output metrics
    # For df column names use snake_case. Spaces are not permitted, example coded list
    # Summary entries:
    # 'Gas_MWh',
    # 'Elec_MWh',
    # 'Gas_kWh/m2',
    # 'Elec_kWh/m2'
    # 'Boilers_MWh',
    # 'Chillers_MWh',
    # 'Boilers_kWh/m2',
    # 'Chillers_kWh/m2'
    # 'CE_kgCO2/m2',
    # 'UK_BER_kgCO2/m2',
    # 'EUI_kWh/m2'
    # 'Ta_max_degC',
    # 'Boiler_max_kW',
    # 'Chiller_max_kW'

    # Energy end use breakdown entries:
    #'Interior_lighting_kWh/m2',
    #'Exterior_lighting_kWh/m2',
    #'Space_heating_(gas)_kWh/m2',
    #'Space_heating_(elec)_kWh/m2',
    #'Space_cooling_kWh/m2',
    #'Pumps_kWh/m2',
    #'Fans_interior_kWh/m2',
    #'DHW_heating_kWh/m2',
    #'Receptacle_equipment_kWh/m2',
    #'Elevators_escalators_kWh/m2',
    #'Data_center_equipment_kWh/m2',
    #'Cooking_(gas)_kWh/m2',
    #'Cooking_(elec)_kWh/m2',
    #'Refrigeration_kWh/m2',
    #'Wind_PV_kWh/m2'

    outputs = [
                'Gas_MWh',
                'Elec_MWh',
                'Gas_kWh/m2',
                'Elec_kWh/m2',
                'Boilers_MWh',
                'Chillers_MWh',
                'Boilers_kWh/m2',
                'Chillers_kWh/m2',
                'CE_kgCO2/m2',
                'UK_BER_kgCO2/m2',
                'EUI_kWh/m2',
                'Ta_max_degC',
                'Boiler_max_kW',
                'Chiller_max_kW',

                'Interior_lighting_kWh/m2',
                'Exterior_lighting_kWh/m2',
                'Space_heating_(gas)_kWh/m2',
                'Space_heating_(elec)_kWh/m2',
                'Space_cooling_kWh/m2',
                'Pumps_kWh/m2',
                'Fans_interior_kWh/m2',
                'DHW_heating_kWh/m2',
                'Receptacle_equipment_kWh/m2',
                'Elevators_escalators_kWh/m2',
                'Data_center_equipment_kWh/m2',
                'Cooking_(gas)_kWh/m2',
                'Cooking_(elec)_kWh/m2',
                'Refrigeration_kWh/m2',
                'Wind_PV_kWh/m2'
                ]

    ### Define the parametric inputs in a dict
    # Example coded dict entries [list 1 ...n]; comment-out inputs not required
    inputs = {}

    # ... numeric inputs
    inputs['building_orientation'] = [90.0, 135.0, 180.0]
    #inputs['room_heating_setpoint'] = [19.0, 21.0, 22.0]
    #inputs['room_cooling_setpoint'] = [25.0, 26.0, 28.0]
    #inputs['apsys_scop'] = [0.7, 0.8, 0.9]
    #inputs['apsys_sseer'] = [2.0, 2.5, 3.0]
    #inputs['sys_free_cooling'] = [4.0, 5.0]
    #inputs['ncm_terminal_sfp'] = [0.1, 0.5]            # NCM only
    #inputs['ncm_localexhaust_sfp'] = [0.1, 0.5]        # NCM only
    #inputs['ncm_light_pho_parasit'] = [0.01, 0.05]     # NCM only
    #inputs['ncm_light_occ_parasit'] = [0.01, 0.05]     # NCM only
    #inputs['window_openable_area'] = [25.0, 30.0, 35.0]
    #inputs['ext_wall_glazing'] = [20, 30, 40]
    #inputs['wall_const_u_value'] = [0.1, 0.2, 0.3]
    #inputs['window_const_u_value'] = [1.0, 1.2, 1.5]
    #inputs['roof_const_u_value'] = [0.1, 0.2, 0.3]
    #inputs['floor_const_u_value'] = [0.1, 0.2, 0.3]
    #inputs['outer_pane_transmittance'] = [0.2, 0.3, 0.4]
    #inputs['outer_pane_reflectance'] = [0.6, 0.8]
    #inputs['local_shade_overhang'] = [-0.1, 0.1, 0.1, 0.1, 0.1]    # NB. cumulative
    #inputs['local_shade_depth'] = [-0.1, 0.1, 0.1]       # NB. cumulative
    #inputs['pv_area'] = [10.0, 50.0, 100.0]

    # ... string id by integer index (maps to id, name or filename)
    #inputs['weather_file'] = ['LondonDSY2020H.fwt', 'LondonDSY2050H.fwt', 'LondonDSY2080H.fwt']    
    #inputs['ap_system'] = ['SYST0001', 'SYST0002', 'SYST0003']
    #inputs['infiltration_rate'] = ['Infiltration 0.5', 'Infiltration 0.75']
    #inputs['gen_lighting_gain'] = ['General Lighting 5','General Lighting 10']
    #inputs['computer_gain'] = ['Computers 3','Computers 5']
    #inputs['wall_construction'] = ['STD_WAL2','STD_WAL3']
    #inputs['window_construction'] = ['STD_EXT1','STD_EXT2']
    #inputs['roof_construction'] = ['STD_ROO1', 'STD_ROO2']
    #inputs['floor_construction'] = ['STD_FLO2', 'STD_FLO3']
    #inputs['asp_file'] = ['CAV.asp', 'VAV.asp', 'UFAD.asp']

    ### Define the simulation choice
    # 0 is run_simulation() i.e. Apache
    # 1 is run_compliance_simulation () i.e. UK Part L
    route = 0

    ### Define loads sims (asp_file must be defined)
    # True for ON, False for off. Set to False for UK Compliance
    loads_on = False

    ### Set the model to edit
    #   The Real model is index 0 in the project.models list
    #   The Real, Actual & Proposed models are the same model; actual/proposed room model
    #   data is updated following edits in accordance with relevant compliance rules
    model_index = 0

    # Create dataframe of scenarios
    scenarios_df = utils_parametric.scenarios(inputs)
    # ... optionally export the scenarios
    scenarios_output_name = project_folder + 'Scenarios.xlsx'
    scenarios_df.to_excel(scenarios_output_name)

    # Run parametric simulations
    simulations_output_name = project_folder + 'Para_sim_table.csv'
    utils_parametric.simulations( project,
                                    model_index,
                                    route,
                                    loads_on,
                                    scenarios_df,
                                    simulations_output_name,
                                    outputs)