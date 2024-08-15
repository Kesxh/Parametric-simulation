import os
import iesve
import importlib
import numpy as np
import pandas as pd
import mod_utils_para as utils_parametric
from itertools import product
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

def run_simulation():
    importlib.reload(utils_parametric)
    project = iesve.VEProject.get_current_project()

    print('Archiving project ...')
    project_folder = project.path
    print('Project archived to project backups folder')

    outputs = [
        'Gas_MWh', 'Elec_MWh', 'Gas_kWh/m2', 'Elec_kWh/m2',
        'Boilers_MWh', 'Chillers_MWh', 'Boilers_kWh/m2', 'Chillers_kWh/m2',
        'CE_kgCO2/m2', 'UK_BER_kgCO2/m2', 'EUI_kWh/m2', 'Ta_max_degC',
        'Boiler_max_kW', 'Chiller_max_kW', 'Interior_lighting_kWh/m2',
        'Exterior_lighting_kWh/m2', 'Space_heating_(gas)_kWh/m2',
        'Space_heating_(elec)_kWh/m2', 'Space_cooling_kWh/m2',
        'Pumps_kWh/m2', 'Fans_interior_kWh/m2', 'DHW_heating_kWh/m2',
        'Receptacle_equipment_kWh/m2', 'Elevators_escalators_kWh/m2',
        'Data_center_equipment_kWh/m2', 'Cooking_(gas)_kWh/m2',
        'Cooking_(elec)_kWh/m2', 'Refrigeration_kWh/m2', 'Wind_PV_kWh/m2'
    ]

    try:
        wall_u_start = float(wall_u_s_entry.get())
        window_u_start = float(window_u_s_entry.get())
        roof_u_start = float(roof_u_s_entry.get())
        floor_u_start = float(floor_u_s_entry.get())

        wall_u_end = float(wall_u_e_entry.get())
        window_u_end = float(window_u_e_entry.get())
        roof_u_end = float(roof_u_e_entry.get())
        floor_u_end = float(floor_u_e_entry.get())

        wall_u_jump = float(wall_u_j_entry.get())
        window_u_jump = float(window_u_j_entry.get())
        roof_u_jump = float(roof_u_j_entry.get())
        floor_u_jump = float(floor_u_j_entry.get())

        wall_u_values = np.arange(wall_u_start, wall_u_end + wall_u_jump, wall_u_jump).tolist()
        window_u_values = np.arange(window_u_start, window_u_end + window_u_jump, window_u_jump).tolist()
        roof_u_values = np.arange(roof_u_start, roof_u_end + roof_u_jump, roof_u_jump).tolist()
        floor_u_values = np.arange(floor_u_start, floor_u_end + floor_u_jump, floor_u_jump).tolist()

    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers.")
        return

    inputs = {
        'wall_const_u_value': wall_u_values,
        'window_const_u_value': window_u_values,
        'roof_const_u_value': roof_u_values,
        'floor_const_u_value': floor_u_values
    }

    route = 0
    loads_on = False
    model_index = 0

    combinations = list(product(*inputs.values()))
    print(f"Running {len(combinations)} simulations...")

    all_results = []  # To store all results in a single DataFrame

    for i, (wall_u, window_u, roof_u, floor_u) in enumerate(combinations):
        
        print(f"Running simulation {i+1}/{len(combinations)} with values - Wall: {wall_u}, Window: {window_u}, Roof: {roof_u}, Floor: {floor_u}")
        simulations_output_name = f"{project_folder}/simulation_{i+1}.csv"

        scenario = {
            'wall_const_u_value': wall_u,
            'window_const_u_value': window_u,
            'roof_const_u_value': roof_u,
            'floor_const_u_value': floor_u
        }

        scenarios_df = utils_parametric.scenarios(scenario)

        simulation_results = utils_parametric.simulations(
            project,
            model_index,
            route,
            loads_on,
            scenarios_df,simulations_output_name,
            outputs
        )
        simulation_result={}
        # Add U-values to the results DataFrame
        simulation_result['wall_const_u_value'] = wall_u
        simulation_result['window_const_u_value'] = window_u
        simulation_result['roof_const_u_value'] = roof_u
        simulation_result['floor_const_u_value'] = floor_u

        # Append the results to the list
        all_results.append(simulation_result)

        utils_parametric.reset_changes(project, model_index, scenarios_df)

    # Concatenate all results into a single DataFrame
    final_results = pd.concat(all_results, ignore_index=True)

    # Save to Excel file
    output_file = f"{project_folder}/combined_simulation_results.xlsx"
    final_results.to_excel(output_file, index=False)
    print(f"Results saved to {output_file}")

    messagebox.showinfo("Simulation Complete", "The simulations have completed successfully.")

# Create the main window
root = tk.Tk()
root.title("Parametric Sensitivity Simulation Tool")

# Create and place widgets for input
tk.Label(root, text="BASE VALUE").grid(row=0, column=1, padx=10, pady=5, sticky="e")
tk.Label(root, text="MAXIMUM VALUE").grid(row=0, column=2, padx=10, pady=5, sticky="e")
tk.Label(root, text="JUMP BY").grid(row=0, column=3, padx=10, pady=5, sticky="e")

tk.Label(root, text="Wall U-Values:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
tk.Label(root, text="Window U-Values:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
tk.Label(root, text="Roof U-Values:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
tk.Label(root, text="Floor U-Values:").grid(row=4, column=0, padx=10, pady=5, sticky="e")

wall_u_s_entry = tk.Entry(root, width=5)
wall_u_s_entry.grid(row=1, column=1, padx=10, pady=5)
wall_u_e_entry = tk.Entry(root, width=5)
wall_u_e_entry.grid(row=1, column=2, padx=10, pady=5)
wall_u_j_entry = tk.Entry(root, width=5)
wall_u_j_entry.grid(row=1, column=3, padx=10, pady=5)

window_u_s_entry = tk.Entry(root, width=5)
window_u_s_entry.grid(row=2, column=1, padx=10, pady=5)
window_u_e_entry = tk.Entry(root, width=5)
window_u_e_entry.grid(row=2, column=2, padx=10, pady=5)
window_u_j_entry = tk.Entry(root, width=5)
window_u_j_entry.grid(row=2, column=3, padx=10, pady=5)

roof_u_s_entry = tk.Entry(root, width=5)
roof_u_s_entry.grid(row=3, column=1, padx=10, pady=5)
roof_u_e_entry = tk.Entry(root, width=5)
roof_u_e_entry.grid(row=3, column=2, padx=10, pady=5)
roof_u_j_entry = tk.Entry(root, width=5)
roof_u_j_entry.grid(row=3, column=3, padx=10, pady=5)

floor_u_s_entry = tk.Entry(root, width=5)
floor_u_s_entry.grid(row=4, column=1, padx=10, pady=5)
floor_u_e_entry = tk.Entry(root, width=5)
floor_u_e_entry.grid(row=4, column=2, padx=10, pady=5)
floor_u_j_entry = tk.Entry(root, width=5)
floor_u_j_entry.grid(row=4, column=3, padx=10, pady=5)

# Create a Run button
run_button = tk.Button(root, text="Run Simulation", command=run_simulation)
run_button.grid(row=5, columnspan=1500, pady=30)

# Run the main loop
root.mainloop()
