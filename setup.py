from setuptools import setup

setup(name='pytahoe',
      version='1.0.1',
      description='Python module for working with the Tahoe-LAFS filesystem.',
      long_description='''
	This module allows for easy interaction with a Tahoe-LAFS grid, via the WebAPI.
	
	Current functionality includes:
	* Retrieving information about files and directories
	* Creating directories and subdirectories
	* Uploading immutable files
	* Attaching files or subdirectories to directories
	* Mounting a directory to a mountpoint via FUSE or dokan
	* Retrieving files
	
	Functionality that is currently notably absent, but will be added in the future:
	* Verifying and repairing objects
	* Renewing share leases
	* Deleting files from directories
	* Uploading of mutable files (SDMF and MDMF)
      ''',
      author='Sven Slootweg',
      author_email='pytahoe@cryto.net',
      url='http://cryto.net/pytahoe',
      packages=['pytahoe'],
      provides=['pytahoe'],
      install_requires=['fs', 'requests >= 1.0']
     )
