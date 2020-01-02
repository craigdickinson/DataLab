"""
Routines to access and stream data from Azure Cloud Storage.
"""
__author__ = "Craig Dickinson"

from tempfile import TemporaryFile

from azure.storage.blob import BlockBlobService
import os


def connect_to_azure_account(account_name, account_key):
    return BlockBlobService(account_name, account_key)


def check_azure_account_exists(account_name, account_key):
    bloc_blob_service = BlockBlobService(account_name, account_key)
    bloc_blob_service.list_containers(num_results=1)

    return bloc_blob_service


def extract_container_name_and_folders_path(fullpath):
    """Extract container name and virtual folders path."""

    # Convert fullpath to system path format then split into container name and virtual folders path
    dirs = os.path.normpath(fullpath).split(os.sep)
    container_name = dirs[0]
    virtual_folders_path = "/".join(dirs[1:])

    return container_name, virtual_folders_path


def get_blobs(bloc_blob_service, container_name, virtual_folders_path=""):
    generator = bloc_blob_service.list_blobs(
        container_name, prefix=virtual_folders_path
    )
    blobs = [blob.name for blob in generator]

    return blobs


def stream_blob(bloc_blob_service, container_name, blob_name):
    fp = TemporaryFile()
    bloc_blob_service.get_blob_to_stream(container_name, blob_name, stream=fp)
    fp.seek(0)

    return fp
