"""
==================================
Parametric Simulation - utilities
==================================

Module description
------------------
Functions for generating a list of unique parametric simulations, modifying the model,
simulating the model and returning simulation results.Required by parametric_***.py

"""

import os
import time
import iesve
import pandas as pd
from typing import List
from pathlib import Path
from itertools import product
import utils_model_mod

from importlib import reload
reload(utils_model_mod)



def scenarios(inputs):
    """ 
    Generates a Pandas dataframe of model revision combinations.
    The first combination is a control with no model changes.
    The combinations include one item from every list & are unique.

    Args:
        inputs (dict) : {key : list (float or string)}

    Returns:
        df (pandas df) : rows of unique combinations of model revisions
    """
    
    # Ensure all inputs are lists (even if only one value is provided)
    for key in inputs:
        if not isinstance(inputs[key], list):
            inputs[key] = [inputs[key]]  # Convert single values to a list

    # Use product to generate all combinations of input values
    scenarios = list(product(*inputs.values()))

    # Create a dataframe of the scenarios with column names using the dict keys
    df = pd.DataFrame(scenarios, columns=inputs.keys())

    # Name the index column
    df.index.name = 'run'

    # Add a note to the user
    print('Number of scenarios generated: ', len(df))
    if len(df) > 100:
        print('NOTE: number of scenarios > 100; this may take some time')

    return df


def reset_changes(project, model_index, df):
    """ Resets model changes for a single variable change list to list index[0]

    Args:
        project (iesve object) : object
        model_index (int) : index for real, proposed model etc
        df (pandas df) : model changes for a single variable

    """

    project = iesve.VEProject.get_current_project()
    model = project.models[model_index]

    # Reset mode change to index[0]
    print('\n Resetting model back to index[0] state')

    utils_model_mod.apply_model_modifications(project, model, df.columns, df.loc[df.index[0]])

def simulations(project, model_index, route, loads_on, df: pd.DataFrame, simulations_output_name, new_columns: List[str]):
    """ Modifies the specified model for each scenario
        Thus each successive scenario overwrites the last
        Optionally runs sizing and thermal simulations for each scenario
        Deletes output files after the results have been extracted

    Args:
        project (iesve object) : object
        model_index (int) : index for real, proposed model etc
        route (int) : sim (0) or compliance sim flag (1)
        loads_on (bool) : loads sims on / off (1/0)
        df (pandas df) : list of scenarios & assignments
        simulations_output_name (str) : output csv file pathname
        new_columns (list (str)) : aps variable names

    Returns:
        df2 (pandas df) : dataframe of scenarios with results added
    """

    project = iesve.VEProject.get_current_project()
    model = project.models[model_index]
    project_folder = project.path
    sim = iesve.ApacheSim()

    # As you should not modify something you are iterating over we will make a copy of df
    # We add labelled columns to the dataframe for the required simulation results
    df2 = df.copy()
    for column in new_columns:
        df2[column] = 0.0

    # Iterate over the the scenarios in the df
    # iterrows is slow but the VE simulations are the speed limiting factor here
    # and iterrows facilitates using row index and column names for easy access

    for index, row in df.iterrows():

        # Apply scenario (row) changes
        print(f'\nApplying scenario {index} modifications to model ...')

        utils_model_mod.apply_model_modifications(project, model, df.columns, row)

        path_list = []
        # ... create aps, asp & shd filenames
        if route == 0:
            # user names output files
            aps_name = f'Para_run_{index}.aps'
            # ... and set up path names
            aps_path = Path(project_folder, 'Vista', aps_name)
            asp_path = Path(project_folder, 'Vista',   f'Para_run_{index}.asp')
            shd_path = Path(project_folder, 'SunCast', f'{project.name}.shd')
            gsk_path = Path(project_folder, 'SunCast', f'{project.name}.gsk')

            path_list += [aps_path, asp_path, shd_path, gsk_path]
        elif route == 1:
            # uk compliance 2013 default names
            aps_name = f'a_(Part L2 2013)_{project.name}.aps'
            aps_n_name = f'n_(Part L2 2013)_{project.name}.aps'
            # ... and set up path names
            aps_path = Path(project_folder, 'Vista', aps_name)
            aps_n_path = Path(project_folder, 'Vista', aps_n_name)
            path_list += [aps_path, aps_n_path]
        else:
            print('Route flag set incorrectly')
            return

        # ... set simulation options - results file
        sim.set_options(results_filename=aps_name)

        # Simulate scenario (row)
        print('Running scenario ' + str(index) + ' ...')

        if loads_on:
            # ... Set the HVAC network; catch the control run
            if row['asp_file'] != 0:
                sim.set_hvac_network(row['asp_file'])
            # ... Room / zone loads simulation
            sim.run_room_zone_loads()
            # ... Run HVAC system loads & sizing simulation
            sim.run_loads_sizing()
            time.sleep(10)          # 103555 get/set load file names; so use a delay

        # ... Run thermal simulation
        if route == 0:
            # suncast & radiance presims require batch mode
            thermal_result = sim.run_simulation(queue_to_tasks=True)
        elif route == 1:
            # uk compliance has independent sim settings & mode
            thermal_result = sim.run_compliance_simulation()
        else:
            print('Route flag set incorrectly')
            return

        # ... wait for aps to be saved to vista folder or break after 15 mins
        time_counter = 0
        time_out = 900
        while not os.path.exists(aps_path):
            time.sleep(1)
            time_counter += 1
            if time_counter > time_out:
                break

        print('Thermal simulation run success: {}'.format(thermal_result))
        time.sleep(2)

        # Get results if simulation has not failed
        if thermal_result == True:
            output = utils_model_mod.get_results(project, aps_name, new_columns)

            # Write results to df2 result columns
            for column in new_columns:
                df2.loc[index, column] = output[column]

            # Export results
            # Includes an index in the export to match with the aps filename suffix
            df2.to_csv(simulations_output_name, encoding='utf-8', index=True)

            # Allow time for resources to be freed
            # For UK Compliance allow BRUKL additional process to complete
            if route == 0:
                time.sleep(2)
            elif route == 1:
                time.sleep(10)

            # Delete aps & asp file to avoid filling up the hard drive
            # Comment this out if you want to keep the files; but you must manually
            # delete them before running the script again on the same project
            for path in path_list:
                try:
                    os.remove(path)
                except:
                    pass
