from googleapiclient.discovery import build
import google.auth

import requests
import json

from __future__ import annotations

import sys
from typing import Any

from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1


# Variables
spreadsheet_id = ''
sheet_name = "ACTUALIZAR TIPOS DE MAQUINA"

vm_data_list = []

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def spreadsheet_auth():
    creds, _ = google.auth.default(scopes=SCOPES)

    service = build('sheets', 'v4', credentials=creds)

    return service


def get_google_sheet_data_service():
    service = spreadsheet_auth()
    result = service.spreadsheets().values.get(spreadsheetId=spreadsheet_id, range=sheet_name).execute()

    values = result.get('values', [])

    if len(values) > 1:
        headers = values[0]
        rows = values[1]
    
        json_data = [dict(zip(headers, row)) for row in rows]
    else:
        print("No data")
    return json_data

'''
# Function to get a google sheet with his ID, name and general API key. It returns a json.
def get_google_sheet_data(spreadsheet_id, sheet_name):
    url = 'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}!A1:Z?alt=json&key={api_key}'

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        return data
    
    except requests.exceptions.RequestException as e:
        print("Error: {e}")
        return None
'''

# Function to prepare a list of the class vm_data
def prepare_vm_list(json_obtained_data):
    json_data = json.loads(json_obtained_data)
    id = 0
    for item in json_data:
        id +=1
        vm_data_list.append(vm_data(id, item["ProjectName"], item["MachineName"], item["MachineType"], item["MachineZone"]))

# Function to stop a instance of Google VM
def stop_instance(vd: vm_data):
    instance_client = compute_v1.InstancesClient()

    # El ID no se obtiene del sheet, ademas, no se si el nombre de instancia es project name o machine name, voy a dejarlo con este ultimo
    operation = instance_client.stop(project=vd.id, zone=vd.machine_zone, instance=vd.machine_name)

    wait_for_extended_operation(operation, "instance stopping")

# Function to start a instance of Google VM
def start_instance(vd: vm_data):
    """
    Starts a stopped Google Compute Engine instance (with unencrypted disks).
    Args:
        project_id: project ID or project number of the Cloud project your instance belongs to.
        zone: name of the zone your instance belongs to.
        instance_name: name of the instance your want to start.
    """
    instance_client = compute_v1.InstancesClient()

    operation = instance_client.start(project=vd.id, zone=vd.machineZone, instance=vd.machine_name)

    wait_for_extended_operation(operation, "instance start")

# Function to change the machine type. THE INSTANCE MUST BE IN 'TERMINATED' State
def change_machine_type(vd: vm_data):
    """
    Changes the machine type of VM. The VM needs to be in the 'TERMINATED' state for this operation to be successful.

    Args:
        project_id: project ID or project number of the Cloud project you want to use.
        zone: name of the zone your instance belongs to.
        instance_name: name of the VM you want to modify.
        new_machine_type: the new machine type you want to use for the VM.
            For example: `e2-standard-8`, `e2-custom-4-2048` or `m1-ultramem-40`
            More about machine types: https://cloud.google.com/compute/docs/machine-resource
    """
    client = compute_v1.InstancesClient()
    instance = client.get(project=vd.id, zone=vd.machineZone, instance=vd.machine_name)

    if instance.status != compute_v1.Instance.Status.TERMINATED.name:
        raise RuntimeError(
            f"Only machines in TERMINATED state can have their machine type changed. "
            f"{instance.name} is in {instance.status}({instance.status_message}) state."
        )

    machine_type = compute_v1.InstancesSetMachineTypeRequest()
    machine_type.machine_type = (
        f"projects/{project_id}/zones/{zone}/machineTypes/{vd.machine_type}"
    )
    operation = client.set_machine_type(
        project=vd.id,
        zone=vd.machineZone,
        instance=vd.machine_name,
        instances_set_machine_type_request_resource=vd.machine_type
    )

    wait_for_extended_operation(operation, "changing machine type")

# Function to wait and report the results from an operation of an instance of Google VM
def wait_for_extended_operation(operation: ExtendedOperation, verbose_name: str = "operation", timeout: int = 300):
    """
    Waits for the extended (long-running) operation to complete.

    If the operation is successful, it will return its result.
    If the operation ends with an error, an exception will be raised.
    If there were any warnings during the execution of the operation
    they will be printed to sys.stderr.

    Args:
        operation: a long-running operation you want to wait on.
        verbose_name: (optional) a more verbose name of the operation,
            used only during error and warning reporting.
        timeout: how long (in seconds) to wait for operation to finish.
            If None, wait indefinitely.

    Returns:
        Whatever the operation.result() returns.

    Raises:
        This method will raise the exception received from `operation.exception()`
        or RuntimeError if there is no exception set, but there is an `error_code`
        set for the `operation`.

        In case of an operation taking longer than `timeout` seconds to complete,
        a `concurrent.futures.TimeoutError` will be raised.
    """
    result = operation.result(timeout=timeout)

    if operation.error_code:
        print(
            f"Error during {verbose_name}: [Code: {operation.error_code}]: {operation.error_message}",
            file=sys.stderr,
            flush=True,
        )
        print(f"Operation ID: {operation.name}", file=sys.stderr, flush=True)
        raise operation.exception() or RuntimeError(operation.error_message)

    if operation.warnings:
        print(f"Warnings during {verbose_name}:\n", file=sys.stderr, flush=True)
        for warning in operation.warnings:
            print(f" - {warning.code}: {warning.message}", file=sys.stderr, flush=True)

    return result





# Class to work the data from the json obtained from the google sheet
class vm_data:

    def __init__(self, id = 0, project_name = "", machine_name = "", machine_type = "", machine_zone = ""):
        self.__id = id
        self.__project_name = project_name
        self.__machine_name = machine_name
        self.__machine_type = machine_type
        self.__machine_zone = machine_zone

@property
def id(self):
    return self.__id

@id.setter
def project_name(self, id):
    self.__id = id

@property
def project_name(self):
    return self.__project_name

@project_name.setter
def project_name(self, project_name):
    self.__project_name = project_name

@property
def machine_name(self):
    return self.__machine_name

@machine_name.setter
def machine_name(self, machine_name):
    self.__machine_name = machine_name

@property
def machine_type(self):
    return self.__machine_type

@machine_type.setter
def machine_type(self, machine_type):
    self.__machine_type = machine_type

@property
def machine_zone(self):
    return self.__machine_zone

@machine_zone.setter
def machine_zone(self, machine_zone):
    self.__machine_zone = machine_zone