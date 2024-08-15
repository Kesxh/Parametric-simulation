"""
==================================
Parametric sensitivity simulations
==================================

Module description
------------------
Parametric simulation tool for sensitivity analyses; requires parametric_utils.py

This script operates on the current model. Each independent model change list is a
single variable sensitivity analysis; a simulation is run for each input in each
independent model change list. The script can be run for one or many lists each
execution of the script; thus an individual analysis or a mass individual analyses; the
script resets the model to the index[0] parameter after each independent model change
list so that all independent model change lists start from the same model state (the
exception is shade geometry which cannot be reset).

Plan each sensitivity analysis; pick the model change list variables with good reason and
carefully set the range and number of inputs (10 ordinates is considered sensible for a
regression analysis; however for the statsmodel lib used in chart_sensitivity.py 20 are
required).

The independent model change lists are defined by the user; these are of two types:
numeric or by-reference; only numeric changes can have meaningful regression applied.
Examples are given in the script; notice that you can use functions in-line to generate
the numeric lists (start, stop, step).

The script loops through each list of independent model changes and for each list
generates a csv output file. If you want the current model state to be included as a
baseline include it in the lists at index[0].

The script can be used for compliance actual/proposed etc models.

The output csv files contain the scenario run #, model changes and multiple output
metrics; this is saved after each iteration so that the results are safe should
a simulation error occur.

The csv can be viewed & processed in Excel e.g. using sort. The csv can be edited e.g.
deleting rows or output metric columns that are not wanted then charted using
chart_sensitivity.py. As multiple output metrics can be defined the sensitivity
simulations can be used to study multiple sensitivities e.g. CO2. heating, cooling,
max Ta etc.

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
import numpy as np
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

    # Define the independent model change lists in a dict
    # Example coded dict entries [list 1 ...n]; comment-out inputs not required
    inputs = {}

    # ... numeric inputs
    inputs['building_orientation'] = [90.0, 135.0, 180.0, 270.0]
    #inputs['room_heating_setpoint'] = np.arange(16.0, 22.0, 0.25).tolist()
    #inputs['room_cooling_setpoint'] = np.arange(23.0, 29.0, 0.25).tolist()
    #inputs['apsys_scop'] = np.arange(0.70, 0.95, 0.0125).tolist()
    #inputs['apsys_sseer'] = np.arange(2.0, 5.0, 0.15).tolist()
    #inputs['sys_free_cooling'] = np.arange(4.0, 6.0, 0.1).tolist()
    #inputs['ncm_terminal_sfp'] = np.arange(0.1, 0.5, 0.02).tolist()          # NCM only
    #inputs['ncm_localexhaust_sfp'] = np.arange(0.1, 0.5, 0.02).tolist()      # NCM only
    #inputs['ncm_light_pho_parasit'] = np.arange(0.01, 0.05, 0.002).tolist()  # NCM only
    #inputs['ncm_light_occ_parasit'] = np.arange(0.01, 0.05, 0.002).tolist()  # NCM only
    #inputs['window_openable_area'] = np.arange(10.0, 30.0, 1.0).tolist()
    #inputs['ext_wall_glazing'] = np.arange(20.0, 40.0, 1.0).tolist()
    inputs['wall_const_u_value'] = np.arange(0.1, 0.3, 0.1).tolist()
    #inputs['window_const_u_value'] = np.arange(1.0, 1.8, 0.02).tolist()
    #inputs['roof_const_u_value'] = np.arange(0.1, 0.3, 0.01).tolist()
    #inputs['floor_const_u_value'] = np.arange(0.1, 0.3, 0.01).tolist()
    #inputs['outer_pane_transmittance'] = np.arange(0.2, 0.4, 0.01).tolist()
    #inputs['outer_pane_reflectance'] = np.arange(0.6, 0.8, 0.01).tolist()
    #inputs['local_shade_overhang'] = [-0.05, -0.05, -0.05, 0.05, 0.05, 0.05, 0.05, 0.05,
    # 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05] # NB. cumulative
    #inputs['local_shade_depth'] = = [-0.05, -0.05, -0.05, 0.05, 0.05, 0.05, 0.05, 0.05,
    # 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05] # NB. cumulative
    #inputs['pv_area'] = np.arange(0.0, 100.0, 5.0).tolist()

    # gains - new 103053
    # air exchanges inc infil - new 31587

    # ... string id by integer index (maps to id, name or filename)
    #inputs['weather_file'] = ['LondonDSY2020H.fwt', 'LondonDSY2050H.fwt', 'LondonDSY2080H.fwt'] 
    #inputs['ap_system'] = ['SYST0001', 'SYST0002', 'SYST0003']
    #inputs['infiltration_rate'] = ['Infiltration 0.5', 'Infiltration 0.75']
    #inputs['gen_lighting_gain'] = ['General Lighting 5','General Lighting 10']
    #inputs['computer_gain'] = ['Computers 3','Computers 5']
    #inputs['wall_construction'] = ['STD_WAL2','STD_WAL3']
    # inputs['window_construction'] = ['STD_EXT1','STD_EXT2']
    #inputs['roof_construction'] = ['STD_ROO1', 'STD_ROO2']
    #inputs['floor_construction'] = ['STD_FLO2', 'STD_FLO3']
    #inputs['asp_file'] = ['CAV.asp', 'VAV.asp', 'UFAD.asp']

    # weather - new 106742

    # Define the simulation choice
    # 0 is run_simulation() i.e. Apache
    # 1 is run_compliance_simulation () i.e. UK Part L
    route = 0

    # Define loads sims (asp_file must be defined)
    # True for ON, False for off. Set to False for UK Compliance
    loads_on = False

    # Set the model to edit
    #   The Real model is index 0 in the project.models list
    #   The Real, Actual & Proposed models are the same model; actual/proposed room model
    #   data is updated following edits in accordance with relevant compliance rules
    model_index = 0
    print(inputs)
    # Loop thru each model change list and process each sensitivity analysis
    # save each analysis to a seprate csv file named after the input list
    for item in inputs:

        # Make dict of item
        single = {item: inputs[item]}

        # Create dataframe of scenarios
        scenarios_df = utils_parametric.scenarios(single)

        # Run parametric simulations
        simulations_output_name = project_folder + str(item) + '.csv'
        utils_parametric.simulations(project,
                                     model_index,
                                     route,
                                     loads_on,
                                     scenarios_df,
                                     simulations_output_name,
                                     outputs)

        # Reset model back to index[0] state ready for the next model change list
        utils_parametric.reset_changes(project, model_index, scenarios_df)
