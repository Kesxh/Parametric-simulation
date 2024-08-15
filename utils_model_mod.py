"""
==================================
Model Modification - utilities
==================================

Module description
------------------
Functions for modifying the model and returning simulation results.

"""
import os
import iesve
import numpy as np
from os import listdir
from os.path import isfile, join


def revise_bldg_orientation(project, value):
    """ Sets model angle from north
        Positive is anticlockwise from north

    Args:
        project (iesve object) : object
        value (float) : angle 0-360 or 0--360
    """
    # Check input within -360 to +360 range
    # If out of range adjust as per aplocate tool
    if value > 360.0:
        value = value-360.0
    if value < -360.0:
        value = value+360.0    

    # Set angle
    geom = iesve.VEGeometry
    geom.set_building_orientation(value)


def revise_weather_file(project, value):
    """ Sets weather file
        Checks if weather file

    Args:
        project (iesve object) : object
        value (str) : file name
    """
    # Check file exists in shared data 

    # Get IESVE install location
    app_folder = iesve.get_application_folder()
    # Split path up - returns a list
    parts = app_folder.split('\\')
    # We want to drop the last two elements so take a slice
    parts = parts[:-3]
    # Re-join the parts and add the shared weather folder path
    weather_folder = ('\\').join(parts) + '\Shared Content\Weather'

    # Get the files in the weather folder
    existing_files = [f for f in listdir(weather_folder) if isfile(join(weather_folder, f))]
    # Check the weather file is in the folder
    if value in existing_files:
        # create the API object for ApLocate data
        loc = iesve.VELocate()
        loc.open_wea_data()
        # Set ApLocate data using a dictionary
        loc.set({'weather_file': value})
        # Save and close
        loc.save_and_close()
    else:
        print(value, ' is not in shared content\weather. Not set')


def get_thermal_templates(project):
    """Get list of thermal templates

    Args:
        project (iesve object): project

    Returns:
        list: list of thermal templates
    """
    # Templates are a dict so get values
    templates = project.thermal_templates(True)     # In-use only
    return templates.values()

def revise_ap_systems(project, value):
    """ For active templates using Apsys only:
        Assign ap system = value to hvac, aux and dhw

    Args:
        project (iesve object) : object
        value (str) : gain reference
    """
    # Loop through templates
    for template in get_thermal_templates(project):
        template.set_apache_systems({   'HVAC_system': value,
                                        'aux_vent_system_same' : True,
                                        'aux_vent_system' : value,
                                        'dhw_system' : value,
                                        'dhw_system_same' : True})
        template.apply_changes()

def revise_ap_system_cop(project, value, type):
    """ For active apsystems only:
        Assign ap system SCoP or SSEER = value

    Args:
        project (iesve object) : object
        value (str) : value to set for SCoP or SEER
        type (str) :scop or sseer
    """

    # Loop through active templates and add to list of active system IDs
    active_systems = []
    for template in get_thermal_templates(project):
        apsys_settings = template.get_apache_systems()
        active_systems.append(apsys_settings['HVAC_system'])

        if apsys_settings['aux_vent_system_same'] == False:
            active_systems.append(apsys_settings['dhw_system'])

        if apsys_settings['dhw_system_same'] == False:
            active_systems.append(apsys_settings['aux_vent_system'])

    # Loop through apsystems and change SCoP or SSEER value on active systems only
    ap_systems = project.apache_systems()
    for ap_system in ap_systems:
        if ap_system.id in active_systems:
            if type == 'scop':
                ap_system.set_heating({'SCoP' : value})
            elif type == 'sseer':
                ap_system.set_cooling({'SSEER' : value})

def set_heating_setpoint(project, value):
    """ Sets room heating setpoint on active templates
        Sets either constant setpoint or two value main setpoint

    Args:
        project (iesve object) : object
        value (float) : setpoint
    """
    # Loop through active templates and revise setpoints
    for template in get_thermal_templates(project):
        room_conditions = template.get_room_conditions()

        if room_conditions['heating_setpoint_type']==iesve.setpoint_type.constant:
            template.set_room_conditions({'heating_setpoint' : value})
        elif room_conditions['heating_setpoint_type']==iesve.setpoint_type.two_value:
            template.set_room_conditions(
                {'heating_setpoint_twovalue_main_setpoint': value})
        else:
            print(template.name, ' heating setpoint not single or two value, not set')

        template.apply_changes()

def set_cooling_setpoint(project, value):
    """ Sets room cooling setpoint on active templates
        Sets either constant setpoint or two value main setpoint

    Args:
        project (iesve object) : object
        value (float) : setpoint
    """
    # Loop through active templates and revise setpoints
    for template in get_thermal_templates(project):
        room_conditions = template.get_room_conditions()

        if room_conditions['cooling_setpoint_type'] == iesve.setpoint_type.constant:
            template.set_room_conditions({'cooling_setpoint' : value})
        elif room_conditions['cooling_setpoint_type'] == iesve.setpoint_type.two_value:
            template.set_room_conditions(
                {'cooling_setpoint_twovalue_main_setpoint': value})
        else:
            print(template.name, ' cooling setpoint not single or two value, not set')

        template.apply_changes()

def revise_free_cooling(project, value):
    """ For active templates using Apsys only
        Adds system_air_free_cooling value (ach)

    Args:
        project (iesve object) : object
        value (str) : system_air_free_cooling value (ach)
    """

    # Loop through active templates & set free cooling template (only affects apsys)
    for template in get_thermal_templates(project):
        template.set_apache_systems({'system_air_free_cooling' : value})
        template.apply_changes()

def find_exchange(project, value):
    """ Finds air exchange with name = value
        Returns air exchange object

    Args:
        project (iesve object) : object
        value (str) : air exchange reference

    Returns:
        exchange : air exchange object
    """

    for exchange in project.air_exchanges():
        if exchange.name == value:
            return exchange
    return None


def revise_air_exchange(project, value, type):
    """ For active templates
        Delete air exchange = type
        Add air exchange of same type = value

    Args:
        project (iesve object) : object
        value (str) : air exchange reference
        type (int) : air exchange type_val (0=infil, 1=natvent, 2=auxvent)
    """

    # Loop through templates
    for template in get_thermal_templates(project):
        exchanges = template.get_air_exchanges()
        # Loop through exchanges on template
        for exchange in exchanges:
            # Check if air exchange is type  then delete & add exchange
            if exchange.get()['type_val'] == type:
                template.remove_air_exchange(exchange)
                template.add_air_exchange(find_exchange(project, value))
        template.apply_changes()


def find_gain(project, value):

    """ Finds casual gain with name = value
        Returns casual gain object

    Args:
        project (iesve object) : object
        value (str) : gain reference

    Returns:
        casual_gain : casual gain object
    """

    for casual_gain in project.casual_gains():
        if casual_gain.name == value:
            return casual_gain
    return None


def revise_gain(project, value, type):

    """ For active templates
        Delete gain = type
        Add gain of same type = value

    Args:
        project (iesve object) : object
        value (str) : gain reference
        type (enum) : gain type
    """

    # Loop through templates
    for template in get_thermal_templates(project):
        # Loop through gains on template
        for gain in template.get_casual_gains():
                # Check if gain is type then delete & add gain
                if gain.get()['type_val'] == type:
                    template.remove_gain(gain)
                    template.add_gain(find_gain(project, value))
                    template.apply_changes()

def get_all_rooms(model):
    """Gets a list all the rooms in the given model

    Args:
        model (iesve object): model

    Returns:
        list:  iesve room objects
    """
    return [body for body in model.get_bodies(False) if body.type == iesve.VEBody_type.room]

def get_all_room_data(model):
    """Gets a list of the room data for all the rooms in the given model

    Args:
        model (iesve object): model

    Returns:
        list: room data for rooms
    """
    return [room.get_room_data() for room in get_all_rooms(model)]

def revise_ncm_terminal_sfp(model, value):

    """ Only relevant to UK NCM Apsys
        Sets room > system > vent & extract terminal unit SFP w/(l/s) when ON only
        NCM system selection will set 'mech_supply_in_room' ON

    Args:
        model (iesve object) : object
        value (float) : terminal unit SFP w/(l/s)
    """
    for room_data in get_all_room_data(model):
        room_data.set_apache_systems({'mech_sfp' : value})

def revise_ncm_localexhaust_sfp(model,value):

    """ Only relevant to UK NCM Apsys
        Sets room > system > vent & extract local mech exhaust SFP w/(l/s) when ON only
        User will set 'has_mech_exhaust' ON

    Args:
        model (iesve object) : object
        value (float) : local mech exhaust SFP w/(l/s)
    """
    for room_data in get_all_room_data(model):
        room_data.set_apache_systems({'extract_SFP' : value})

def revise_ncm_light_photoelectric_parasitic(model,value):
    """ Only relevant to UK NCM Apsys
        Sets room > space data > Building regs > controls parasitic power w/m2
        Updates update in VE UI on entering compliance view

    Args:
        model (iesve object) : object
        value (float) : parasitic power w/m2
    """
    for room_data in get_all_room_data(model):
        room_data.set_ncm_lighting({'photoelectric_parasitic_power' : value})

def revise_ncm_light_occupancy_parasitic(model,value):
    """ Only relevant to UK NCM Apsys
        Sets room > space data > Building regs > controls parasitic power w/m2
        Updates update in VE UI on entering compliance view

    Args:
        model (iesve object) : object
        value (float) : parasitic power w/m2
    """
    for room_data in get_all_room_data(model):
        room_data.set_ncm_lighting({'occupancy_parasitic_power' : value})

def set_openable_area(project, value):

    """ Adjusts openable area % on Macroflo opening types
        Only applies to types where % is already non-zero i.e. already open so that
        existing closed windows remain closed

    Args:
        project (iesve object) : object
        value (float) : openable area %
    """

    # If value is specified to change
    # Loop through the opening types and change all non-zero types
    # Update openable_area & equivalent_orifice_area
    for opening in project.get_macro_flo_opening_types():
        if opening.get()['openable_area'] > 0.0:
            opening.set({'openable_area' : value, 'equivalent_orifice_area' : value})

def revise_glazing(model,value):
    """ Adjusts % ext wall glazing on rooms with existing ext wall glazing only

    Args:
        model (iesve object) : object
        value (int) : %
    """
    for room in get_all_rooms(model):
        if room.get_areas()['ext_wall_glazed'] > 0:
            room.select()

    # Replace glazing on selected rooms
    geom = iesve.VEGeometry
    geom.set_percent_wall_glazing(int(value))

def get_cdb_project():
    """Gets CDB project object

    Returns:
        iesve object: construction data base project
    """
    db = iesve.VECdbDatabase.get_current_database()
    cdb_projects = db.get_projects()
    cdb_project_list = cdb_projects[0]
    return cdb_project_list[0]

def change_opaque_construction(model, value, type):
    """ For active bodies:
        Change construction of type = value

    Args:
        model (iesve object) : object
        value (str) : construction id
        type (enum) : surface type
    """
    cdb_project = get_cdb_project()

    # Get construction with ID = value

    new_construction = cdb_project.get_construction(value, iesve.construction_class.opaque)

    try:
        new_construction.is_editable
    except RuntimeError:
        print(f"Error Opaque Construction {value} is not present. Not Updated.")
        return

    for body in get_all_rooms(model):
        # Get all surfaces in the room
        surfaces = body.get_surfaces()
        # Loop through all the room surfaces
        for surface in surfaces:
            # We differentiate between surfaces (wall, roof ...) and windows
            if surface.type == type:
                body.assign_construction(new_construction, surface)

    # To handle inner volumes and differing construction thickness
    model.rebuild_adjacencies()

def change_glazed_construction(model, value):
    """ For active bodies:
        Change construction of all openings of type = value
        Works for ext window, int window or rooflight

    Args:
        model (iesve object) : object
        value (str) : construction id
    """
    cdb_project = get_cdb_project()

    # Get construction with ID = value
    new_construction = cdb_project.get_construction(value, iesve.construction_class.glazed)

    try:
        new_construction.is_editable
    except RuntimeError:
        print(f"Error Glazed Construction {value} is not present. Not Updated.")
        return

    for body in get_all_rooms(model):
        # Get all surfaces in the room
        surfaces = body.get_surfaces()
        # Loop through all the room surfaces
        for surface in surfaces:
            # Catch openings that are not windows ie openings or doors
            for opening in surface.get_openings():
                try:
                    body.assign_construction_to_opening(new_construction, surface,
                    opening.get_id())
                except:
                    continue

    # To handle inner volumes and differing construction thickness
    model.rebuild_adjacencies()

def get_active_constructions(model):
    """Get a list of all the active constructions in the model

    Args:
        model (iesve object): model

    Returns:
        list: active constructions
    """
    active_constr_list = []

    for room in get_all_rooms(model):
        # Get the assigned constructions
        body_constrs = room.get_assigned_constructions()
        # Go through the list of tuples and append id to active construction list
        for body_constr in body_constrs:
            active_constr_list.append(body_constr[0])

    return active_constr_list

def revise_constr_layer(model, value, type, property, position):
    """ For active constructions of type
        Set specified layer (= position) specified property with value
        User must ensure property value is possible

    Args:
        model (iesve object) : object
        value (float) : revised value
        type (enum) : surface type glazed or opaque
        property (str) : material property to revise (dict key)
        position (int) : layer position (0 indexed from outside to inside layer)
    """
    # If value is specified to change
    # Get a list of all the active constructions in the model
    active_constr_list = get_active_constructions(model)

    # Set construction class & is_opaque parameter
    if type == iesve.VESurface_type.ext_glazing:
        c_class = iesve.construction_class.glazed
        is_opaque = False
    else:
        c_class = iesve.construction_class.opaque
        is_opaque = True

    # Get all constructions for type (c_class)
    project = get_cdb_project()

    # Check construction is in active list and revise layer [position] properties
    for constr in project.get_construction_ids(c_class):
        if constr in active_constr_list:
            construction = project.get_construction(constr, c_class)
            layers = construction.get_layers()
            layer = layers[position].get_material(is_opaque)
            layer.set_properties({property : value})

    # To handle inner volumes and differing construction thickness
    model.rebuild_adjacencies()

def revise_glazed_constr_u_value(model, value):
    """ For active constructions of type
        Set opaque insulation layer thickness to achieve u value
        Or set glazing cavity resistance to achieve u value
        User must ensure property value is possible
        enum for u-value set to iso; this can be changed to cibse, iso, ashae, t24

    Args:
        model (iesve object) : object
        value (float) : revised u value w/m2.k
        type (enum) : surface type glazed or opaque
    """
    # If value is specified to change
    # Get a list of all the active constructions in the model
    active_constr_list = get_active_constructions(model)

    # Set construction class & is_opaque parameter
    c_class = iesve.construction_class.glazed
    is_opaque = False

    # Get all constructions for type (c_class)
    project = get_cdb_project()

    # Check construction is in active list and revise layer properties
    for constr in project.get_construction_ids(c_class):
        if constr in active_constr_list:
            construction = project.get_construction(constr, c_class)
            layers = construction.get_layers()

            # Catch for single glazing & make no changes
            if len(layers) < 2:
                continue

            # find cavity layer position from outside layer (zero indexed)
            index = 0
            for layer in layers:
                if layer.get_material(is_opaque) is None:
                    break
                index +=1

            # current cavity layer resistance
            layer_prop = layers[index].get_properties(iesve.uvalue_types.iso)
            resistance = layer_prop['resistance']

            # if u value better than wanted; decrease cavity resistance
            # by 0.01 W/m2K increments until target U value is met
            while construction.get_u_factor(iesve.uvalue_types.iso) <= value:
                resistance -= 0.01
                layers[index].set_properties({'resistance': resistance})

            # if u value worse than wanted; increase cavity resistance
            # by 0.01 W/m2K increments until target U value is met
            while construction.get_u_factor(iesve.uvalue_types.iso) >= value:
                resistance += 0.01
                layers[index].set_properties({'resistance': resistance})

    # To handle inner volumes and differing construction thickness
    model.rebuild_adjacencies()

def revise_opaque_constr_u_value(model, value):
    """ For active constructions of type
        Set opaque insulation layer thickness to achieve u value
        Or set glazing cavity resistance to achieve u value
        User must ensure property value is possible
        enum for u-value set to iso; this can be changed to cibse, iso, ashae, t24

    Args:
        model (iesve object) : object
        value (float) : revised u value w/m2.k
        type (enum) : surface type glazed or opaque
    """
    # If value is specified to change
    # Get a list of all the active constructions in the model
    active_constr_list = get_active_constructions(model)

    # Set construction class & is_opaque parameter
    c_class = iesve.construction_class.opaque
    is_opaque = True

    # Get all constructions for type (c_class)
    project = get_cdb_project()

    # Check construction is in active list and revise layer properties
    for constr in project.get_construction_ids(c_class):
        if constr in active_constr_list:
            construction = project.get_construction(constr, c_class)
            layers = construction.get_layers()

            # find insulation layer position from outside layer
            index = -1
            for idx, layer in enumerate(layers):
                material = layer.get_material(is_opaque)
                if material is not None:
                    props = material.get_properties() # This was incorrect, string give you a string.
                    if props['category'] == iesve.material_categories.insulating:
                        index = idx

            # Catch for no insulation & make no changes
            if index == -1:
                continue

            # current insulation layer thickness
            layer_prop = layers[index].get_properties()
            thickness = layer_prop['thickness']

            # if u value better than wanted; decrease insulation thickness
            # by 10mm increments until U is met
            while construction.get_u_factor(iesve.uvalue_types.iso) <= value:
                thickness -= 0.01
                layers[index].set_properties({'thickness': thickness})

            # if u value worse than wanted; increase insulation thickness
            # by 10mm increments until U is met
            while construction.get_u_factor(iesve.uvalue_types.iso) >= value:
                thickness += 0.01
                layers[index].set_properties({'thickness': thickness})

    # To handle inner volumes and differing construction thickness
    model.rebuild_adjacencies()

def get_bodies_local_shaded(model):
    """Gets a list of locally shaded bodies from model

    Args:
        model (iesve object): model

    Returns:
        list: local shaded bodies
    """
    bodies = [body for body in model.get_bodies(False)
                if body.type == iesve.VEBody_type.local_shade]
    return bodies

def revise_shade_overhang(model, overhang_change):
    """ Adjusts existing horizontal local shade overhang (both ends)
        Checks shade body name to check for an assigned elevation - north, south, east,
        west (lower case matters)
        Surface orientation is compass north, south, east, west +-45 degrees

    Args:
        model (iesve object) : object
        overhang_change (float) : left & right overhang size change (+ is an increase) m

    Notes:
        The change is applied to the current geometry so the changes are cumulative so
        if you want the shade to extend by 0.5, 1.0, 1.5 input 0.5, 0.5, 0.5
        Limitation: surfaces at exactly the test orientation boundaries (set to XYZ.01)
        Limitation: using 0 as an input will make no changes
    """
    for body in get_bodies_local_shaded(model):
        # Get body name
        body_object = body.get_room_data(type = iesve.attribute_type.real_attributes)
        body_data = body_object.get_general()

        # Check NSEW via name and adjust 2 unrestrained ends
        surfaces = body.get_surfaces()
        if 'north' in body_data['name'] or 'south' in body_data['name']:
            for surface in surfaces:
                properties = surface.get_properties()

                if properties['type'] != 'Wall':
                    continue
                orientation = properties['orientation']

                if orientation > 45.01 and orientation <= 135.01:
                    surface.move(overhang_change)

                if orientation > 225.01 and orientation <= 315.01:
                    surface.move(overhang_change)

        if 'east' in body_data['name'] and 'west' in body_data['name']:
            for surface in surfaces:
                properties = surface.get_properties()

                if properties['type'] != 'Wall':
                    continue
                orientation = properties['orientation']

                if orientation > 315.01 and orientation <= 45.01:
                    surface.move(overhang_change)

                if orientation > 135.01 and orientation <= 225.01:
                    surface.move(overhang_change)

def revise_shade_depth(model, depth_change):
    """ Adjusts existing horizontal local shade depth dimension
        Checks shade body name to check for an assigned elevation - north, south, east,
        west (lower case matters)
        Surface orientation is compass north, south, east, west +-45 degrees

    Args:
        model (iesve object) : object
        depth_change (float) : depth size change (+ is an increase) m

    Notes:
        The change is applied to the current geometry so the changes are cumulative so
        if you want the shade to extend by 0.5, 1.0, 1.5 input 0.5, 0.5, 0.5
        Limitation: surfaces at exactly the test orientation boundaries (set to XYZ.01)
        Limitation: using 0 as an input will make no changes
    """
    for body in get_bodies_local_shaded(model):
        # Get body name
        body_object = body.get_room_data(type = iesve.attribute_type.real_attributes)
        body_data = body_object.get_general()

        # Check NSEW via name and adjust 1 unrestrained shade front
        surfaces = body.get_surfaces()
        if 'north' in body_data['name']:
            for surface in surfaces:
                properties = surface.get_properties()
                if (properties['type'] == 'Wall' and
                    properties['orientation'] > 315.01 and
                    properties['orientation'] <= 45.01
                    ):
                    surface.move(depth_change)

        if 'south' in body_data['name']:
            for surface in surfaces:
                properties = surface.get_properties()
                if (properties['type'] == 'Wall'and
                    properties['orientation'] > 135.01 and
                    properties['orientation'] <= 225.01
                    ):
                    surface.move(depth_change)

        if 'east' in body_data['name']:
            for surface in surfaces:
                properties = surface.get_properties()
                if (properties['type'] == 'Wall' and
                    properties['orientation'] > 45.01 and
                    properties['orientation'] <= 135.01
                    ):
                    surface.move(depth_change)

        if 'west' in body_data['name']:
            for surface in surfaces:
                properties = surface.get_properties()
                if (properties['type'] == 'Wall' and
                    properties['orientation'] > 225.01 and
                    properties['orientation'] <= 315.01
                    ):
                    surface.move(depth_change)

def revise_pv_area(value):
    """ Adjusts pv panel area for pv panel index 0

    Args:
        value (float) : panel area m2

    Notes:
        This function only changes an existing parametric or freestanding pv panel; if
        no index 0 panel exists or there is only a HC panel it has no effect
        All existing settings for the index 0 panel are as set by the user
    """

    # If value is specified to change
    renewables = iesve.VERenewables()
    pvs = renewables.get_pv_data()

    # Check if there are no pvs in the model & skip
    if not pvs:
        print('There are no PVs in the model; no changes made')
        return

    # Check if index 0 is a high concentration panel & skip
    if pvs[0]['class'] == 'High concentration panel':
        print('High concentration panel found; no changes made')
        return

    # Set area of index 0 pv panel
    renewables.set_pv_data({'area' : value}, pvs[0]['id'])

def set_sim_options(asp_name):
    """ Sets Apachesim options
        Sim options are not reset; specified vars are just overwritten so user settings
        from this dialog are re-used, so set what you want ON on the dialog

    Args:
        asp_name (str) : asp file name
    """

    sim = iesve.ApacheSim()
    hvac = iesve.HVACNetwork

    # If HVAC is specified to change
    sim.set_options(HVAC_filename=asp_name)

    # Force updates e.g. template setpoints to the asp file by loading it
    # In AphVAC take care - editing parameters can unlink the data with the model
    hvac.load_network(asp_name)

def summary_vars_map():
    """Summary aps variable mapping

    Returns:
        summary_mapping (dict) : mapping name: tuple ([list], type)

    """

    # Define summary variable mapping
    # Use  a dict of dict to handle the different ways variables are processed
    summary_vars_map = {
        'MWh': {
        'Gas_MWh':('Total gas', 'Total nat. gas', 'e'),
        'Elec_MWh':('Total electricity', 'Total electricity', 'e'),
        'Boilers_MWh':('Boilers energy', 'Boilers energy', 'e'),
        'Chillers_MWh':('Chillers energy', 'Chillers energy', 'e')
        },
        'kWh/m2': {
        'Gas_kWh/m2':('Total gas', 'Total nat. gas', 'e'),
        'Elec_kWh/m2':('Total electricity', 'Total electricity', 'e'),
        'Boilers_kWh/m2':('Boilers energy', 'Boilers energy', 'e'),
        'Chillers_kWh/m2':('Chillers energy', 'Chillers energy', 'e'),
        'EUI_kWh/m2':('Total energy (excl. ideal)', 'Total energy','e')
        },
        'kgCO2/m2':{
        'CE_kgCO2/m2':('Total CE', 'Total CE', 'c'),
        'UK_BER_kgCO2/m2':('NCM total CE (ex renewables)','NCM total CE [ex renewables]', 'c')
        },
        'max_C':{
        'Ta_max_degC':('Room air temperature','z')
        },
        'max_kW':{
        'Boiler_max_kW':('Boilers energy', 'Boilers energy', 'e'),
        'Chiller_max_kW':('Chillers energy', 'Chillers energy', 'e')
        }
    }

    return summary_vars_map

def get_end_use_map():
    """Energy end use is mapped to prm energyuse enums

    Returns:
        end_uses_mapping (dict) : mapping

    """

    # Setup vars for enum types
    eu = iesve.EnergyUse
    es = iesve.EnergySource

    # Define energy end use mapping
    end_uses_mapping = {
        'Interior_lighting_kWh/m2':([eu.prm_interior_lighting], es.elec),
        'Exterior_lighting_kWh/m2':([eu.prm_exterior_lighting], es.elec),
        'Space_heating_(gas)_kWh/m2':([eu.prm_space_heating], es.nat_gas),
        'Space_heating_(elec)_kWh/m2':([eu.prm_space_heating], es.elec),
        'Space_cooling_kWh/m2':([eu.prm_space_cooling], es.elec),
        'Pumps_kWh/m2':([eu.prm_pumps, eu.prm_humidification], es.elec),
        'Fans_interior_kWh/m2':([eu.prm_fans_interior_central, eu.prm_fans_interior_local], es.elec),
        'DHW_heating_kWh/m2':([eu.prm_services_water_heating], es.elec),
        'Receptacle_equipment_kWh/m2':([eu.prm_receptacle_equipment], es.elec),
        'Elevators_escalators_kWh/m2':([eu.prm_elevators_escalators], es.elec),
        'Data_center_equipment_kWh/m2':([eu.prm_data_center_equipment], es.elec),
        'Cooking_(gas)_kWh/m2':([eu.prm_cooking], es.nat_gas),
        'Cooking_(elec)_kWh/m2':([eu.prm_cooking], es.elec),
        'Refrigeration_kWh/m2':([eu.prm_refrigeration], es.elec),
        'Wind_PV_kWh/m2':([eu.prm_elec_gen_wind, eu.prm_elec_gen_pv], es.unspecified)
    }

    return end_uses_mapping

def get_results(project, aps_name, results_list):
    """ Gets model level sim results and processes the data for output

    Args:
        project (iesve object) : object
        aps_name (str) : aps file name
        results_list (list of str) : column names

    Returns:
        results (dict of float) : summed results
    """

    # Open scenario aps file
    results = iesve.ResultsReader()
    results.open_aps_data(aps_name)

    # Create a dict to return the results, initialise the dict and values to zero
    output = {}
    for result in results_list:
        output[result] = 0.0

    # Get building conditioned floor area
    floor_area = 0
    model = project.models[0]
    for body in get_all_rooms(model):
        body_areas = body.get_areas()
        # total floor area comprises int & ext floor area but excludes floor holes &
        # floor glazing
        floor_area += body_areas['int_floor_area'] + body_areas['ext_floor_area']

    # Get reporting timestep and determine divisor for sum type results
    rpd = results.results_per_day
    divisor = rpd/24

    # Get mappings
    sv_map = summary_vars_map()
    ee_map = get_end_use_map()

    # Get the results data, apply divisor, convert to usable units and round to 2 dp
    # then assign value to dict
    for result in results_list:
        # Summary entries by type:

        if result in sv_map['MWh']:
            try:
                idx = sv_map['MWh'][result]
                values = results.get_results(idx[0], idx[1], idx[2])
                output[result] = round(np.sum(values)/(1000**2*divisor), 2)
            except:
                output[result] = 0

        elif result in sv_map['kWh/m2']:
            try:
                idx = sv_map['kWh/m2'][result]
                values = results.get_results(idx[0], idx[1], idx[2])
                output[result] = round(np.sum(values) / (1000*floor_area*divisor), 2)
            except:
                output[result] = 0

        elif result in sv_map['kgCO2/m2']:
            try:
                idx = sv_map['kgCO2/m2'][result]
                values = results.get_results(idx[0], idx[1], idx[2])
                output[result] = round(np.sum(values)*(44/12) / (floor_area*divisor), 2)
            except:
                output[result] = 0

        elif result in sv_map['max_C']:
            try:
                idx = sv_map['max_C'][result]
                values = []
                for body in get_all_rooms(model):
                    room_ta = results.get_all_room_results(body.id, idx[0], idx[1])
                    values.append(np.max(room_ta['Air temperature']))
                output[result] = round(np.max(values), 2)
            except:
                output[result] = 0

        elif result in sv_map['max_kW']:
            try:
                idx = sv_map['max_kW'][result]
                values = results.get_results(idx[0], idx[1], idx[2])
                output[result] = round(np.max(values) / 1000, 2)
            except:
                output[result] = 0

        # Energy end use entries:

        elif result in ee_map:
            value = 0

            if result not in ('DHW_heating_kWh/m2'):
                # Unpack mapping
                end_uses = ee_map[result][0]
                energy_source = ee_map[result][1]
                 # Get aps result data for energy end use
                for use in end_uses:
                    values2 = results.get_energy_results(use_id=use, source_id=energy_source)
                    # test for returned invalid data
                    if values2 is not None:
                        value += values2.sum()

            elif result == 'DHW_heating_kWh/m2':
                vars = ['Ap Sys boilers DHW energy', 'ApHVAC boilers DHW energy',
                'ApHVAC generic HPs DHW energy', 'ApHVAC AWHPs DHW energy',
                'ApHVAC WWHPs DHW energy', 'ApHVAC other htg plant DHW energy']
                for var in vars:
                    values2 = results.get_results(var, var, 'e')
                    # test for returned invalid data
                    if values2 is not None:
                        value += values2.sum()

            output[result] = round(value / (1000*floor_area*divisor), 2)
        else:
            print('Error: ', result, ' result not in list')

    # Close results file
    results.close()

    return output

def apply_model_modifications(project, model, mod_categories, row):
    """Applies modifications specified in data frame row to model/project

    Args:
        project (iesve object): project
        model (iesve object): model
        mod_categories (list or dict): modification categories
        row (pandas row or dict): dataframe row/dict to extract values from
    """

    # ... building orientation
    if 'building_orientation' in mod_categories:
        revise_bldg_orientation(project, row['building_orientation'])

    # ... weather file
    if 'weather_file' in mod_categories:
        revise_weather_file(project, row['weather_file'])        

    # ... template apsys assignments
    if 'ap_system' in mod_categories:
        revise_ap_systems(project, row['ap_system'])

    # ... apsystem SCOP and SSEER
    if 'apsys_scop' in mod_categories:
        revise_ap_system_cop(project, row['apsys_scop'], 'scop')
    if 'apsys_sseer' in mod_categories:
        revise_ap_system_cop(project, row['apsys_sseer'], 'sseer')

    # ... template room setpoints
    if 'room_heating_setpoint' in mod_categories:
        set_heating_setpoint(project, row['room_heating_setpoint'])
    if 'room_cooling_setpoint' in mod_categories:
        set_cooling_setpoint(project, row['room_cooling_setpoint'])

    # ... template room free cooling (apsys only)
    if 'sys_free_cooling' in mod_categories:
        revise_free_cooling(project, row['sys_free_cooling'])

    # ... template infiltration
    if 'infiltration_rate' in mod_categories:
        revise_air_exchange(project, row['infiltration_rate'], 0)

    # ... template casual gains
    if 'gen_lighting_gain' in mod_categories:
        revise_gain(project, row['gen_lighting_gain'], iesve.LightingGain_type.general)
    if 'computer_gain' in mod_categories:
        revise_gain(project, row['computer_gain'], iesve.EnergyGain_type.computers)

    # ... room ncm terminal & local exhaust sfp (apsys & ncm only)
    if 'ncm_terminal_sfp' in mod_categories:
        revise_ncm_terminal_sfp(model, row['ncm_terminal_sfp'])
    if 'ncm_localexhaust_sfp' in mod_categories:
        revise_ncm_localexhaust_sfp(model, row['ncm_localexhaust_sfp'])

    # ... room ncm lighting parasitic power (apsys & ncm only)
    if 'ncm_light_pho_parasit' in mod_categories:
        revise_ncm_light_photoelectric_parasitic(model, row['ncm_light_pho_parasit'])
    if 'ncm_light_occ_parasit' in mod_categories:
        revise_ncm_light_occupancy_parasitic(model, row['ncm_light_occ_parasit'])

    # ... macroflo type openable area
    if 'window_openable_area' in mod_categories:
        set_openable_area(project, row['window_openable_area'])

    # ... ext glazing area (do before construction assignment)
    if 'ext_wall_glazing' in mod_categories:
        revise_glazing(model, row['ext_wall_glazing'])

    # ... construction assignments
    if 'wall_construction' in mod_categories:
        change_opaque_construction(
            model, row['wall_construction'], iesve.VESurface_type.ext_wall)
    if 'window_construction' in mod_categories:
        change_glazed_construction(model, row['window_construction'])
    if 'roof_construction' in mod_categories:
        change_opaque_construction(
            model, row['roof_construction'], iesve.VESurface_type.roof)
    if 'floor_construction' in mod_categories:
        change_opaque_construction(
            model, row['floor_construction'], iesve.VESurface_type.ground_floor)

    # ... construction layer material properties
    if 'outer_pane_transmittance' in mod_categories:
        revise_constr_layer(model, row['outer_pane_transmittance'],iesve.VESurface_type.ext_glazing,
        'transmittance', 0)
    if 'outer_pane_reflectance' in mod_categories:
        revise_constr_layer(model, row['outer_pane_reflectance'],iesve.VESurface_type.ext_glazing,
        'outside_reflectance', 0)

    # ... construction u value
    if 'wall_const_u_value' in mod_categories:
        revise_opaque_constr_u_value(model, row['wall_const_u_value'])
    if 'window_const_u_value' in mod_categories:
        revise_glazed_constr_u_value(model, row['window_const_u_value'])
    if 'roof_const_u_value' in mod_categories:
        revise_opaque_constr_u_value(model, row['roof_const_u_value'])
    if 'floor_const_u_value' in mod_categories:
        revise_opaque_constr_u_value(model, row['floor_const_u_value'])

    # ... local shading bodies
    if 'local_shade_overhang' in mod_categories:
        revise_shade_overhang(model, row['local_shade_overhang'])
    if 'local_shade_depth' in mod_categories:
        revise_shade_depth(model, row['local_shade_depth'])

    # ... renewables assignments
    if 'pv_area' in mod_categories:
        revise_pv_area(row['pv_area'])

    # ... set simulation options - HVAC file
    if 'asp_file' in mod_categories:
        set_sim_options(row['asp_file'])
