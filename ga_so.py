"""
=======================================
Genetic optimization - single objective
=======================================

Module description
------------------
Genetic optimization tool for sensitivity analyses; requires ga_so_optimise_utils.py

For an introduction on genetic optimization see:
https://stackoverflow.com/questions/69544221/how-can-i-find-the-optimal-parameters-for-a-function

This script uses Pygmo 2; refer to https://esa.github.io/pygmo2/tutorials/tutorials.html
In this script we define a continuous, single objective, unconstrained problem. Pygmo 2
assumes a minimise function by default. We will use evolve() but not the archipelago()
class as this implements multiple threads (https://esa.github.io/pygmo/quickstart.html).

This script operates on the current model. Very large numbers of simulations can be
generated. Plan each analysis; consider a series of parametric studies to review
sensitivity and to define bounds before embarking on genetic optimization. Genetic
optimization is not a panacea; consider a series of focused genetic optimizations rather
than one big one with every possible variable e.g. geometry or shades or systems etc.
Also consider a coarse genetic optimization first followed a tighter fine genetic
optimization. Decide which output metric(s) will be used to define 'best'.

Also consider what VE sim options you need to use for sensitivity analyses e.g. loads,
Suncast, ApHVAC as these extend simulation times and for narrowing-in on a solution
region simpler faster simulations maybe appropriate initially.

A dict of model change (chromosones) lower & upper bounds is defined by the user; the
bounds are of two types: numeric or by-reference/ID. Examples are given in the script.
Take care not to define independent model changes that have no value e.g. changing
glazing % and shade size independently or changing asp files & ap systems.

The script can be used for compliance actual/proposed models.

The script exports to a csv file after each simulation run; it exports the model
chromosone values and target metric; this ensures that the results are safe should a
simulation error occur or the user chooses to interrupt (stop) the script early. The
Python editor output pane shows progress; you can also copy the csv file and open it at
any time during the sim to look the data to date, but do not open the live file as this
will lock-out access by the script. The csv can be viewed & processed in Excel e.g.
using sort and also charted on a parallel coordinate chart using chart_parallel.py

Notes
-----
Metric units only

Setup a model with templates, constructions, air exchanges, gains, ApSys or ApHVAC
systems, local shades, parametric or freestanding PV panels etc. Set inner volumes
representation (this affects returned floor area; UK Part L = OFF). Create new items
(constructions, gains, air exchanges, asp / ap systems etc.) in the VE to reference
from the ID based model change lower & upper bounds dict. Make sure your setpoints for
multiple parameter options are set so that hunting will not occur. If you are changing
shades name them appropriately in Model-iT so that they will work with the function.

Set simulation options; unless overwritten by the script these are used by all the sims
so set HVAC, Suncast, RadianceIES & Macroflo options. For UK Compliance sim options are
set within UK Compliance view not in Apache.

We advise using a 6 min simulation step to avoid thermal instability issues. Try running
some check simulations before running parametric simulations; ensure that the model works
before committing to mass simulations. For UK Compliance the TER will be visible in
compliance view following each sim.

In the script main_loop:

- Set the target metric that will be minimized (1)
- Set the outputs required
- Set the required inputs and for each the lower / upper bounds (lower must be < upper)
  Note: shade changes are cumulative so use small values & -ve lower bound
- For ID based inputs setup the mapped_ids dict
- Set the simulation route
- Set if you want load sizing sims and makes sure boundaries['asp_file'] is set
- Set the model to edit (normally the real model)
- Set the algorithm parameters e.g. # of generations (gen)
- Set the required population
- Set what you want to plot on the generation chart (this shows after the optimization)

It will be necessary to experiment with # of generations & population (typical quoted
values are 100 & 300). If these parameters are not set large enough an optimal minima
will not be found. Smaller parameter sets should show a minima but it is unlikely to be
optimal; however this still may offer value. As noted above this is a very good reason
to consider a series of parametric analyses, coarse optimization etc.

The script will delete each aps/asp file after each iteration.
The script will archive the model before making any changes.

The GA_output.csv will be overwritten before a new optimization task so move/rename the
file if you wish to keep it.

"""

import os
import iesve
import importlib
import pygmo as pg
import pandas as pd
import utils_genetic as gau
from datetime import datetime
import plotly.express as px
from pathlib import Path

# Reload utils
importlib.reload(gau)

# Main loop
if __name__ == "__main__":

      # Get the current project
    project = iesve.VEProject.get_current_project()

    ### Archive the project
    print('Archiving project ...')
    project_folder = project.path
    time_stamp = datetime.now().strftime("%d%m%Y_%H%M%S")
    path = Path(project_folder, 'Backups', f'{project.name}_{time_stamp}.cab')
    project.archive_project(str(path), False)
    print('Project archived to project backups folder')

    ### Define the optimization problem to minimise - enter 1 objective
    # Example coded list entries:
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
    target = ['CE_kgCO2/m2']

    ### Define the output metrics; this should include the target
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

    ### Define the optimization problem inputs (chromosones) & boundaries in a dict
    # Example coded dict entries [lower, upper]; comment-out inputs not required:
    boundaries = {}

    # ... numeric inputs
    boundaries['building_orientation'] = [90.0, 180.0]
    #boundaries['room_heating_setpoint'] = [19.0, 22.0]
    #boundaries['room_cooling_setpoint'] = [25.0, 28.0]
    #boundaries['apsys_scop'] = [0.7, 0.9]
    #boundaries['apsys_sseer'] = [2.0, 3.0]
    #boundaries['sys_free_cooling'] = [4.0, 5.0]
    #boundaries['ncm_terminal_sfp'] = [0.1, 0.5]            # NCM only
    #boundaries['ncm_localexhaust_sfp'] = [0.1, 0.5]        # NCM only
    #boundaries['ncm_light_pho_parasit'] = [0.01, 0.05]     # NCM only
    #boundaries['ncm_light_occ_parasit'] = [0.01, 0.05]     # NCM only
    #boundaries['window_openable_area'] = [25.0, 30.0]
    #boundaries['ext_wall_glazing'] = [5.0, 50.0]
    #boundaries['wall_const_u_value'] = [0.1, 0.3]
    #boundaries['window_const_u_value'] = [1.0, 1.5]
    #boundaries['roof_const_u_value'] = [0.1, 0.3]
    #boundaries['floor_const_u_value'] = [0.1, 0.3]
    #boundaries['outer_pane_transmittance'] = [0.2, 0.5]
    #boundaries['outer_pane_reflectance'] = [0.6, 0.8]
    #boundaries['local_shade_overhang'] = [-0.1, 0.1]    # NB. cumulative
    #boundaries['local_shade_depth'] = [-0.1, 0.1]       # NB. cumulative
    #boundaries['pv_area'] = [10.0, 50.0]

    # ... string id by integer index (maps to id, name or filename)
    boundaries['weather_file'] = [0, 2]          # ['LondonDSY2020H.fwt', 'LondonDSY2050H.fwt', 'LondonDSY2080H.fwt']  
    #boundaries['ap_system'] = [0, 2]            # ['SYST0001', 'SYST0002', 'SYST0003']
    #boundaries['infiltration_rate'] = [0, 1]    # ['Infiltration 0.5', 'Infiltration 0.75']
    #boundaries['gen_lighting_gain'] = [0, 1]    # ['General Lighting 5','General Lighting 10']
    #boundaries['computer_gain'] = [0, 1]        # ['Computers 3','Computers 5']
    #boundaries['wall_construction'] = [0, 1]    # ['AGWAL213','AGWAL214']
    #boundaries['window_construction'] = [0, 1]  # ['APGEXTW4','APGEXTW']
    #boundaries['roof_construction'] = [0, 1]    # ['APGROOF1', 'APGROOF4']
    #boundaries['floor_construction'] = [0, 1]   # ['APGFLO12', 'AGSOG111']
    #boundaries['asp_file'] = [0, 2]             # ['CAV.asp', 'VAV.asp', 'UFAD.asp']

    ### For string/id based boundaries define the mappings between index and ids
    mapped_ids = {}
    # Example coded list entries; comment-out inputs not required:
    mapped_ids['weather_file'] = ['LondonDSY2020H.fwt', 'LondonDSY2050H.fwt', 'LondonDSY2080H.fwt']     
    #mapped_ids['ap_system'] = ['New System 1', 'New System 2', 'New System 3'],
    #mapped_ids['infiltration_rate'] = ['Infiltration 0.5', 'Infiltration 0.75'],
    #mapped_ids['gen_lighting_gain'] = ['General Lighting 5','General Lighting 10'],
    #mapped_ids['computer_gain'] = ['Computers 3','Computers 5'],
    #mapped_ids['wall_construction'] = ['AGWAL213','AGWAL214'],
    #mapped_ids['window_construction'] = ['APGEXTW4','APGEXTW'] ,
    #mapped_ids['roof_construction'] = ['APGROOF1', 'APGROOF4'],
    #mapped_ids['floor_construction'] = ['APGFLO12', 'AGSOG111'],
    #mapped_ids['asp_file'] = ['CAV.asp', 'VAV.asp', 'UFAD.asp']

    ### Define the simulation route
    #   0 is run_simulation() i.e. Apache
    #   1 is run_compliance_simulation () i.e. UK Part L
    route = 0

    ### Define loads sims (asp_file must be defined)
    # True for ON, False for off. Set to False for UK Compliance
    loads_on = False

    ### Set the model to edit
    #   The Real model is index 0 in the project.models list
    #   The Real, Actual & Proposed models are the same model; actual/proposed room model
    #   data is updated following edits in accordance with relevant compliance rules
    model_index = 0

    ### Set the optimization problem
    prob = pg.problem(gau.ga_function(  target,
                                        outputs,
                                        boundaries,
                                        mapped_ids,
                                        route,
                                        loads_on,
                                        model_index,
                                        'GA_SO_output.csv'))
    #print(prob)

    ### Set the algorithm
    # https://esa.github.io/pygmo2/algorithms.html
    # Single https://esa.github.io/pygmo2/algorithms.html?highlight=pso_gen#pygmo.pso_gen
    algo = pg.algorithm(pg.pso_gen( gen=20,
                                    omega=0.7298,
                                    eta1=2.05,
                                    eta2=2.05,
                                    max_vel=0.5,
                                    variant=5,
                                    neighb_type=2,
                                    neighb_param=4,
                                    memory=False))

    # Set the verbosity (i.e. each 1 gen there will be a log line)
    # https://esa.github.io/pygmo2/algorithm.html?highlight=verbosity#pygmo.algorithm.set_verbosity
    algo.set_verbosity(1)

    ### Set population
    # https://esa.github.io/pygmo2/population.html?highlight=population#pygmo.population
    pop = pg.population(prob, 20)

    ### Perform an evolution
    # https://esa.github.io/pygmo2/tutorials/evolving_a_population.html?highlight=evolve
    pop = algo.evolve(pop)

    ### Print the optimum result
    print(f'Optimum fitness vector for {target} target is {pop.champion_f}')
    print(f'Optimum decision vector for {target} target is {pop.champion_x}')

    """### Optionally plot the optimization generations
    uda = algo.extract(pg.pso_gen)
    log = uda.get_log()
    generation = [entry[0] for entry in log]
    value = [entry[2] for entry in log]
    data = list(zip(generation, value))
    df = pd.DataFrame(data, columns = ['Generation','CE_kgCO2/m2'])
    log_path = project_folder + 'GA_SO_log.csv'
    df.to_csv(log_path)
    fig = px.scatter(df, x='Generation', y=target[0], log_x=True, log_y=False,
    trendline='ols')
    fig.update_traces(marker_size=20)
    fig.show()"""