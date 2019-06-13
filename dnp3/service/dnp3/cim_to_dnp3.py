import json
import yaml
import sys


from typing import List, Dict, Union, Any
#
# from fncs import fncs

from dnp3.points import (
    PointArray, PointDefinitions, PointDefinition, DNP3Exception, POINT_TYPE_ANALOG_INPUT, POINT_TYPE_BINARY_INPUT
)

out_json = list()

'''Dictionary for mapping the attribute values of control poitns for Capacitor, Regulator and Switches'''

attribute_map = {
    "capacitors": {
        "attribute": ["RegulatingControl.mode", "RegulatingControl.targetDeadband", "RegulatingControl.targetValue",
                      "ShuntCompensator.aVRDelay", "ShuntCompensator.sections"]}
    ,
    "switches": {
        "attribute": "Switch.open"
    }
    ,

    "regulators": {
        "attribute": ["RegulatingControl.targetDeadband", "RegulatingControl.targetValue", "TapChanger.initialDelay",
                      "TapChanger.lineDropCompensation", "TapChanger.step", "TapChanger.lineDropR",
                      "TapChanger.lineDropX"]}

}


class DNP3Mapping():
    """ This creates dnps input and ouput points for incoming CIM messages  and model dictionary file respectively."""

    def __init__(self, map_file):
        self.c_ao = 0
        self.c_bo = 0
        self.c_ai = 0
        self.c_bi = 0
        self.measurements = dict()
        self.out_json = list()
        self.file_dict = map_file
        self.processor_point_def = PointDefinitions()


    def on_message(self, simulation_id,message):
        """ This method handles incoming messages on the fncs_output_topic for the simulation_id.
        Parameters
        ----------
        headers: dict
            A dictionary of headers that could be used to determine topic of origin and
            other attributes.
        message: object

        """

        try:
            message_str = 'received message ' + str(message)

            json_msg = yaml.safe_load(str(message))

            print("Alka")
            if type(json_msg) != dict:
                raise ValueError(
                    ' is not a json formatted string.'
                    + '\njson_msg = {0}'.format(json_msg))

            fncs_input_message = {"{}".format(simulation_id): {}}
            measurement_values = json_msg["message"]["measurements"]

            # storing the magnitude and measurement_mRID values to publish in the dnp3 points for measurement key values
            for y in measurement_values:
                if "magnitude" in y.keys():
                    for point in self.processor_point_def.all_points():
                        if y.get("measurement_mrid") == point.measurement_id and point.magnitude != y.get("magnitude"):
                             point.magnitude = y.get("magnitude")
                             # print("test message", point.magnitude, y.get("measurement_mrid"))
                elif "value" in y.keys():
                    for point in self.processor_point_def.all_points():
                        if y.get("measurement_mrid") == point.measurement_id and point.value != y.get("value"):
                             point.value = y.get("value")

        except Exception as e:
            message_str = "An error occurred while trying to translate the  message received" + str(e)

    def assign_val_a(self, data_type, group, variation, index, name, description, measurement_type, measurement_id):
        """ Method is to initialize  parameters to be used for generating  output  points for measurement key values """
        records = dict()  # type: Dict[str, Any]
        records["data_type"] = data_type
        records["index"] = index
        records["group"] = group
        records["variation"] = variation
        records["description"] = description
        records["name"] = name
        records["measurement_type"] = measurement_type
        records["measurement_id"] = measurement_id
        records["magnitude"] = "0"
        self.out_json.append(records)

    def assign_val_d(self, data_type, group, variation, index, name, description, measurement_type, measurement_id):
        """ This method is to initialize  parameters to be used for generating  output  points for output points"""
        records = dict()
        records["data_type"] = data_type
        records["index"] = index
        records["group"] = group
        records["variation"] = variation
        records["description"] = description
        records["name"] = name
        records["measurement_type"] = measurement_type
        records["measurement_id"] = measurement_id
        records["value"] = "0"
        self.out_json.append(records)

    def assign_valc(self, data_type, group, variation, index, name, description, object_id, attribute):
        """ Method is to initialize  parameters to be used for generating  dnp3 control as Analog/Binary Input points"""
        records = dict()
        records["data_type"] = data_type
        records["index"] = index
        records["group"] = group
        records["variation"] = variation
        records["description"] = description
        records["name"] = name
        records["object_id"] = object_id
        records["attribute"] = attribute
        self.out_json.append(records)

    def load_json(self, out_json, out_file):
        with open(out_file, 'w') as fp:
            out_dict = dict({'points': out_json})
            json.dump(out_dict, fp, indent=2, sort_keys=True)

    def load_point_def(self, point_def):
        self.processor_point_def = point_def

    def _create_dnp3_object_map(self):
        """This method creates the points by taking the input data from model dictionary file"""
        feeders = self.file_dict.get("feeders", [])
        # print(self.file_dict)
        # print(feeders)
        measurements = list()
        capacitors = list()
        regulators = list()
        switches = list()
        solarpanels = list()
        batteries = list()
        for x in feeders:
            measurements = x.get("measurements", [])
            capacitors = x.get("capacitors", [])
            regulators = x.get("regulators", [])
            switches = x.get("switches", [])
            solarpanels = x.get("solarpanels", [])
            batteries = x.get("batteries", [])

        for m in measurements:
            measurement_type = m.get("measurementType")
            measurement_id = m.get("mRID")
            name = m.get("name")
            description = "Equipment is " + m['name'] + "," + m['ConductingEquipment_type'] + " and phase is " + m['phases']
            if m['MeasurementClass'] == "Analog":
                self.assign_valc("AI", 30, 3, self.c_ai,name, description, measurement_type, measurement_id)
                self.c_ai += 1

            if m['MeasurementClass'] == "Discrete":
                self.assign_valc("BI", 1, 1, self.c_bi, name, description, measurement_type, measurement_id)
                self.c_bi += 1


        for m in capacitors:
            object_id = m.get("mRID")
            name = m.get("name")
            phase_value = list(m['phases'])
            description1 = "Capacitor, " + m['name'] + "," + "phase -" + m['phases']
            cap_attribute = attribute_map['capacitors']['attribute']  # type: List[str]
            for l in range(0, 4):
                # publishing attribute value for capacitors as Bianry/Analog Input points based on phase  attribute
                self.assign_val_a("AO", 42, 3, self.c_ao, name, description1, object_id, cap_attribute[l])
                self.c_ao += 1
                for j in range(0, len(m['phases'])):
                    description = "Capacitor, " + m['name'] + "," + "phase -" + phase_value[j]
                    self.assign_val_d("BO", 11, 1, self.c_bo, name, description, object_id, cap_attribute[4])
                    self.c_bo += 1

        for m in solarpanels:
            measurement_id = m.get("mRID")
            name = m.get("name")
            description = "Solarpanel " + m['name'] + "phases - " + m['phases']
            self.assign_val_a("AO", 42, 3, self.c_ao, name, description, None, measurement_id)
            self.c_ao += 1

        for m in batteries:
            measurement_id = m.get("mRID")
            name = m.get("name")
            description = "Battery, " + m['name'] + "phases - " + m['phases']
            self.assign_val_a("AO", 42, 3, self.c_ao, name, description, None, measurement_id)
            self.c_ao += 1

        for m in switches:
            object_id = m.get("mRID")
            name = m.get("name")
            for k in range(0, len(m['phases'])):
                phase_value = list(m['phases'])
                description = "Switch, " + m["name"] + "phases - " + phase_value[k]
                self.assign_val_d("BO", 11, 1, self.c_bo, name, description, object_id,
                                 attribute_map['switches']['attribute'])
                self.c_bo += 1

        for m in regulators:
            name = m.get("bankName")
            reg_attribute = attribute_map['regulators']['attribute']
            bank_phase = list(m['bankPhases'])
            description = "Regulator, " + m['bankName'] + " " + "phase is  -  " + m['bankPhases']
            for n in range(0, 5):
                object_id = m.get("mRID")
                self.assign_val_a("AO", 42, 3, self.c_ao, name, description, object_id[0], reg_attribute[n])
                self.c_ao += 1
                for i in range(4, 7):
                    reg_phase_attribute = attribute_map['regulators']['attribute'][i]
                for j in range(0, len(m['bankPhases'])):
                    description = "Regulator, " + m['tankName'][j] + " " "phase is  -  " + m['bankPhases'][j]
                    object_id = m.get("mRID")
                    self.assign_val_a("AO", 42, 3, self.c_ao, name, description, object_id[j], reg_phase_attribute)
                    self.c_ao +=1

        return self.out_json



