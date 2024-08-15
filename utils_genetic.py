"""
===================================================
Genetic optimization - utilities
===================================================

Module description
------------------
Class to provide Pygmo access and class functions for modifying the model, simulating
the model and returning simulation results. Required by ga_so.py

"""

import os
import time
import iesve
import numpy as np
import pandas as pd
from pathlib import Path
import utils_model_mod

# Reload utils
import importlib
importlib.reload(utils_model_mod)

class ga_function:

    def __init__(self, target, outputs, boundaries, mapped_ids, route, loads_on, model_index, output_file_name):
        """ Initialise class variables

        Args:
            target (list[str]) : variable strings
            outputs (list[str]) : variable strings
            boundaries (dict) : input name : list of two floats or ints (lower/upper bounds)
                                numeric inputs or string inputs mapped by index
            mapped_ids (dict) : input name : list of string inputs
                                used for mapping index to string inputs
            route (int) : 0/1 flag for type of simulation
            loads_on (bool) : loads sims on / off (True/False)
            model_index (int) : index of ve model to be modified
        """

        # Create vars to pass meta data into the class simulation(x) function without
        # changing the Pygmo design pattern
        self.target = target
        self.outputs = outputs
        self.boundaries = boundaries
        self.mapped_ids = mapped_ids
        self.route = route
        self.loads_on = loads_on
        self.model_index = model_index

        # Set dimension of Pygmo problem (number of inputs)
        self.dim = len(boundaries)

        # Set up a pandas df for a results dump
        project = iesve.VEProject.get_current_project()
        project_folder = project.path
        self.df_path = os.path.join(project_folder, output_file_name)
        # get input names and convert to list
        self.cols_list = list(boundaries.keys())
        # add output names
        self.cols_list += self.outputs
        self.df_dump = pd.DataFrame(columns=self.cols_list)

    def fitness(self, x):
        """ Pygmo mandatory fitness test
            Calls the function to modify the model, simulate and return the target
            aps variable

        Args:
            x (numpy array) : chromosones (inputs that are changed in the model by the
                              Pygmo evolve function)
        """

        return self.simulation(x)


    def get_nobj(self):
        """ Returns number of objectives
            Required for > 1 objective problems

        """
        return len(self.target)

    def get_bounds(self):
        """ Pygmo mandatory bounds for the generation of chromosones
            Uses the self.boundaries dict

        Returns:
            tuple[list,list]: lower and upper bounds
        """

        lower = []
        upper = []
        for key in self.boundaries:
            lower.append(self.boundaries[key][0])
            upper.append(self.boundaries[key][1])
        bounds = (lower, upper)
        return bounds

    def simulation(self, x):
        """ Modifies the specified model for chromosone set x and runs a simulation
            Each successive chromosone change will overwrite the last change
            Optionally runs sizing and thermal simulations set by the class variables
            Deletes output files after the results have been extracted

        Args:
            x (numpy array) : array of chromosone values len=dim from Pygmo

        Returns:
            result (float) :
        """

        project = iesve.VEProject.get_current_project()
        model = project.models[self.model_index]
        project_folder = project.path
        sim = iesve.ApacheSim()

        # Create a dict with the boundary keys and the current values in the np array x
        # that has been passed in by Pygmo evolve (the order in the ordered  dict will
        # match that of the values in the np array  x)
        data = {}
        count = 0
        for key in self.boundaries.keys():
            data[key] = x[count]
            count += 1

        # For string based inputs replace index with the mapped id
        # As Pygmo uses floats use round to get an integer index
        for key in self.mapped_ids.keys():
            data[key] = self.mapped_ids[key][round(data[key])]

        # Apply model changes
        print('Applying chromosone set model changes ... ')

        utils_model_mod.apply_model_modifications(project, model, data, data)

        path_list = []
        # ... create aps, asp & shd filenames
        if self.route == 0:
            # user names output files
            aps_name = f'Para_run.aps'
            # ... and set up path names
            aps_path = Path(project_folder, 'Vista', aps_name)
            asp_path = Path(project_folder, 'Vista',   f'Para_run.asp')
            shd_path = Path(project_folder, 'SunCast', f'{project.name}.shd')
            gsk_path = Path(project_folder, 'SunCast', f'{project.name}.gsk')

            path_list += [aps_path, asp_path, shd_path, gsk_path]
        elif self.route == 1:
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
        sim.set_options(results_filename = aps_name)

        # ... set simulation options - HVAC file
        if 'asp_file' in data:
            utils_model_mod.set_sim_options(data['asp_file'])

        # Simulate scenario (row)
        print('Simulating chromosone set ...')

        if self.loads_on:
            # ... Set the HVAC network
            sim.set_hvac_network(data['asp_file'])
            # ... Room / zone loads simulation
            sim.run_room_zone_loads()
            # ... Run HVAC system loads & sizing simulation
            sim.run_loads_sizing()
            time.sleep(10)          # 103555 get/set load file names; so use a delay

        # ... Run thermal simulation
        if self.route == 0:
            # suncast & radiance presims require batch mode
            thermal_result = sim.run_simulation(queue_to_tasks=True)
        elif self.route == 1:
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
        print(f'Thermal simulation run success: {thermal_result}')
        time.sleep(2)

        # Get results if simulation has not failed
        if thermal_result == True:
            output = utils_model_mod.get_results(project, aps_name, self.outputs)
            print('Simulation result ', output)

            # Allow time for resources to be freed
            # For UK Compliance allow BRUKL additional process to complete
            if self.route == 0:
                time.sleep(5)
            elif self.route == 1:
                time.sleep(10)

            # Dump results in to the initialized df and save / overwrite to csv file
            new_row = list(data.values()) + list(output.values())
            # create new df
            new_df = pd.DataFrame([new_row], columns = self.cols_list)
            # add new df to existing
            self.df_dump = pd.concat([self.df_dump, new_df], ignore_index=True)
            # Name the index column to work with ga_chart.py
            self.df_dump.index.name = 'run'
            # save to csv
            self.df_dump.to_csv(self.df_path, index=True)

            # Delete aps & asp file to avoid filling up the hard drive
            # Comment this out if you want to keep the files; but you must manually
            # delete them before running the script again on the same project
            for path in path_list:
                try:
                    os.remove(path)
                except:
                    pass


            output_list = [] # For single-objective only one value will be returned.
            for key in output:
                if key in self.target:
                    output_list.append(float(output[key]))
            print(output_list)

            return output_list