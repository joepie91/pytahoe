import json, time, os, re, requests, urllib

try:
	from fs.contrib.tahoelafs import TahoeLAFS
except ImportError:
	fs_available = False
else:
	try:
		from fs.expose import fuse, dokan
	except ImportError:
		fs_available = false
	else:
		fs_available = True


class PytahoeException(Exception):
	"""Generic base class for pytahoe-related exceptions."""
	pass

class FilesystemException(PytahoeException):
	"""Exception class for 'filesystem exceptions'; ie. the WAPI being unreachable or otherwise non-functional."""
	pass

class ObjectException(PytahoeException):
	"""Exception class for object-related exceptions (files and directories)."""
	pass

class UploadException(PytahoeException):
	"""Exception class specifically for errors encountered during upload of files."""
	pass

class DependencyException(PytahoeException):
	"""Exception class for missing or non-functional dependencies."""
	pass

class MountException(PytahoeException):
	"""Exception class for errors encountered during mounting of a directory."""
	pass

class Filesystem:
	"""Represents a Tahoe-LAFS 'filesystem' or 'grid'."""
	
	def __init__(self, url="http://localhost:3456/"):
		"""Creates a new Filesystem object representing a Tahoe-LAFS grid.
		
		Keyword arguments:
		url -- The URL for the WAPI that should be used for this Filesystem.
		"""
		if url.strip() == "":
			raise FilesystemException("You must specify a Tahoe-LAFS WAPI URL.")
		
		# Ensure there is no trailing slash in the WAPI URL
		if url[-1:] == "/":
			url = url[:-1]
		
		try:
			data = requests.get("%s/statistics?t=json" % url).json()
		except requests.exceptions.RequestException:
			raise FilesystemException("The provided WAPI URL is either not reachable, or not running a recent version of Tahoe-LAFS.")
		except:
			raise FilesystemException("The provided URL is not running a recent version of Tahoe-LAFS.")
			
		self.url = url
		self.start_date = time.time() - data['stats']['node.uptime']
	
	def __repr__(self):
		return "<pytahoe.Filesystem %s>" % self.url
	
	def Directory(self, uri, data=None):
		"""Create and return a new Directory object for the specified URI for this filesystem.
		
		uri -- The URI to represent
		
		Keyword arguments:
		data -- The data, if any, to populate this object with - if none is given, the data will be retrieved from the filesystem.
		"""
		
		if data is None:
			try:
				data = requests.get("%s/uri/%s?t=json" % (self.url, urllib.quote(uri))).json()
			except:
				raise FilesystemException("Could not reach the WAPI or did not receive a valid response.")
		
		return Directory(self, uri, data)
	
	def File(self, uri, data=None):
		"""Create and return a new File object for the specified URI for this filesystem.
		
		uri -- The URI to represent
		
		Keyword arguments:
		data -- The data, if any, to populate this object with - if none is given, the data will be retrieved from the filesystem.
		"""
		
		if data is None:
			try:
				data = requests.get("%s/uri/%s?t=json" % (self.url, urllib.quote(uri))).json()
			except:
				raise FilesystemException("Could not reach the WAPI or did not receive a valid response.")
		
		return File(self, uri, data)
	
	def Object(self, uri, data=None):
		"""Create and return a new Directory or File object for this filesystem, depending on what the URI represents.
		
		uri -- The URI to represent
		
		Keyword arguments:
		data -- The data, if any, to populate this object with - if none is given, the data will be retrieved from the filesystem.
		"""
		
		if data is None:
			try:
				data = requests.get("%s/uri/%s?t=json" % (self.url, urllib.quote(uri))).json()
			except:
				raise FilesystemException("Could not reach the WAPI or did not receive a valid response.")
		
		if "filenode" in data:
			return self.File(uri, data)
		elif "dirnode" in data:
			return self.Directory(uri, data)
		else:
			raise ObjectException("The specified object does not appear to exist.")
	
	def create_directory(self):
		"""Create a new directory node in the filesystem, and return a Directory object representing it."""
		
		result = requests.post("%s/uri?t=mkdir" % self.url, {}).text
		return self.Directory(result)
	
	def _sanitize_filename(self, name):
		"""Strip all potentially unsafe characters from the given filename."""
		return re.sub("[^a-zA-Z0-9 $_.+!*'(),-]+", "", name)
	
	def upload(self, filedata):
		"""Uploads a file to the storage grid and returns a File object representing it.
		
		filedata -- Either a file-like object, or the path to a file.
		"""
		
		if type(filedata) is str:
			try:
				filedata = open(filedata, "rb")
			except IOError:
				raise UploadException("The given path is not a valid file path.")
		elif type(filedata) is not file:
			raise UploadException("Cannot upload the file because the given file is not a valid file object or path.")
				
		file_uri = requests.put("%s/uri" % self.url, data=filedata.read()).text
		return self.File(file_uri)
		
	def attach(self, obj, directory, filename, **kwargs):
		"""Attaches an object to a file node in the filesystem.
		
		obj -- The object to attach.
		directory -- The directory in the filesystem to place the object in.
		filename -- The filename to use for the object.
		
		Keyword arguments:
		writable -- A boolean indicating whether the object should be attached as a writeable node. This will fail if a read-only cap is used.
		"""
		
		try:
			obj.readcap
		except KeyError:
			raise ObjectException("No valid object was specified.")
		
		try:
			directory.readcap
		except KeyError:
			raise ObjectException("No valid tahoepy.Directory was specified.")
		
		if directory.writable == False:
			raise ObjectException("The specified directory is not writable.")
		
		filename = self._sanitize_filename(filename)
		
		if "writable" in kwargs:
			if kwargs["writable"] == True:
				if obj.writable == True:
					filecap = obj.writecap
				else:
					raise ObjectException("Cannot attach object as writable file; the object is not writable.")
			else:
				filecap = obj.readcap
		else:
			filecap = obj.readcap
			
		result = requests.put("%s/uri/%s/%s?t=uri&replace=false" % (self.url, directory.writecap, filename), data=filecap)
		
		if result.status_code == 200:
			return filename
		else:
			raise ObjectException("Could not attach object - the request failed with code %d." % result.status_code)

class Directory:
	"""Represents a directory node in a Tahoe-LAFS grid.
	
	Properties:
	children -- A dictionary of File and Directory objects, with their name as key.
	"""
	mutable = False
	writeable = False
	children = {}
	
	def __init__(self, filesystem, uri, data=None):
		"""Creates a new Directory object.
		
		filesystem -- The Filesystem this Directory belongs to.
		uri -- The original URI for the Directory.
		
		Keyword arguments:
		data -- The data, if any, to populate the object with. Will be retrieved from the filesystem if not specified.
		"""
		
		self.filesystem = filesystem
		self.uri = uri
		
		# We always need to retrieve the data for a directory. Why? Because otherwise we have no data about the children.
		self._get_data()
	
	def __repr__(self):
		"""Returns a string representation for this Directory."""
		
		if self.writable == True:
			state = "writable"
		else:
			state = "read-only"
		
		return "<pytahoe.Directory %s (%s)>" % (self.uri, state)
		
	def _get_data(self):
		"""Actually retrieves the data for this Directory."""
		try:
			data = requests.get("%s/uri/%s?t=json" % (self.filesystem.url, urllib.quote(self.uri))).json()
		except:
			raise FilesystemException("Could not reach the WAPI or did not receive a valid response.")
		
		if "dirnode" in data:
			details = data[1]
			
			self.mutable = details['mutable']
			self.readcap = details['ro_uri']
			
			if "verify_uri" in details:
				self.verifycap = details['verify_uri']
			
			if "rw_uri" in details:
				self.writable = True
				self.writecap = details['rw_uri']
			else:
				self.writable = False
			
			self.children = {}
			
			for child_name, child_data in details['children'].iteritems():
				if "rw_uri" in child_data[1]:
					child_uri = child_data[1]['rw_uri']
				else:
					child_uri = child_data[1]['ro_uri']
				
				self.children[child_name] = self.filesystem.Object(child_uri, child_data)
			
		elif "unknown" in data:
			raise ObjectException("The specified object does not appear to exist.")
		else:
			raise ObjectException("The specified object is not a directory.")
	
	def mount(self, mountpoint):
		"""Mount this Directory to a mount point on the actual filesystem.
		
		mountpoint -- The point to mount the Directory on (on Windows, this will be a drive letter).
		"""
		
		global fs_available
		
		if fs_available == False:
			raise DependencyException("Could not mount the directory because the 'fs' module was not found.")
		
		fs = TahoeLAFS(self.uri, webapi=self.filesystem.url)
		
		try:
			return fuse.mount(fs, mountpoint)
		except OSError:
			try:
				return dokan.mount(fs, mountpoint)
			except OSError:
				raise DependencyException("Could not mount the directory because both the FUSE and dokan libraries are unavailable.")
			except RuntimeError, e:
				raise MountException("Could not mount the directory because a dokan error was encountered: %s" % e.message)
		except RuntimeError, e:
			raise MountException("Could not mount the directory because a FUSE error was encountered: %s" % e.message)
	
	def upload(self, filedata, filename=None):
		"""Upload a file to the storage grid and return a File object representing it.
		
		filedata -- Either a file-like object or the path to a file.
		
		Keyword arguments:
		filename -- The filename to store this file under. If not specified, a random filename will be generated.
		"""
		
		if filename is None:
			if type(filedata) is str:
				filename = self.filesystem._sanitize_filename(os.path.basename(filedata))
			elif type(filedata) is file:
				if type(filedata.name) is str:
					filename = self.filesystem._sanitize_filename(filedata.name)
				else:
					# We could not determine the filename for the input... let's generate something.
					filename = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(15))
			else:
				raise UploadException("The given file is not a valid string or file object.")
		
		new_file = self.filesystem.upload(filedata)
		new_file.attach(self, filename)
		
		return new_file
	
	def attach(self, directory, filename=None, **kwargs):
		"""Attach this Directory to a Directory in the filesystem.
		
		directory -- The Directory to attach this Directory to.
		
		Keyword arguments:
		filename -- The filename to attach this Directory under.
		writable -- Attach the Directory as a writable directory in the filesystem. This will fail if a read-only cap is used.
		"""
		
		return self.filesystem.attach(self, directory, filename, **kwargs)
		
	def create_directory(self, name):
		"""Creates a new subdirectory in this Directory.
		
		Note that the .children attribute of this Directory is not updated until the Directory.refresh() method is called.
		
		name -- The name for the subdirectory.
		"""
		
		new_dir = self.filesystem.create_directory()
		new_dir.attach(self, self.filesystem._sanitize_filename(name), writable=True)
		
		return new_dir
		
	def refresh(self):
		"""Refreshes the data that this Directory object holds."""
		self._get_data()

class File:
	"""Represents a file node in a Tahoe-LAFS grid."""
	mutable = False
	writable = False
	request = None
	
	def __init__(self, filesystem, uri, data=None):
		"""Create a new File object.
		
		filesystem -- The filesystem this File belongs to.
		uri -- The original URI that this File represents.
		
		Keyword arguments:
		data -- The data, if any, to populate the object with. Will be retrieved from the filesystem if not specified.
		"""
		
		self.filesystem = filesystem
		self.uri = uri
		
		if data is None:
			try:
				data = requests.get("%s/uri/%s?t=json" % (self.filesystem.url, urllib.quote(uri))).json()
			except:
				raise FilesystemException("Could not reach the WAPI or did not receive a valid response.")
		
		if "filenode" in data:
			details = data[1]
			
			self.mutable = details['mutable']
			self.readcap = details['ro_uri']
			self.size = details['size']
			
			if "metadata" in details and "tahoe" in details['metadata']:
				self.creation_date = details['metadata']['tahoe']['linkcrtime']
				self.modification_date = details['metadata']['tahoe']['linkmotime']
			
			if "verify_uri" in details:
				self.verifycap = details['verify_uri']
			
			if "rw_uri" in details:
				self.writable = True
				self.writecap = details['rw_uri']
		elif "unknown" in data:
			raise ObjectException("The specified object does not appear to exist.")
		else:
			raise ObjectException("The specified object is not a file.")
	
	def __repr__(self):
		"""Return a string representation of the File."""
		
		if self.writable == True:
			state = "writable"
		else:
			state = "read-only"
		
		if self.mutable == True:
			mutable = "mutable"
		else:
			mutable = "immutable"
		
		return "<pytahoe.File %s (%s, %s)>" % (self.uri, mutable, state)
		
	def attach(self, directory, filename=None, **kwargs):
		"""Attach this File to a Directory in the filesystem.
		
		directory -- The Directory to attach this File to.
		
		Keyword arguments:
		filename -- The filename to attach this File under.
		writable -- Attach the File as a writable file in the filesystem. This will fail if a read-only cap is used.
		"""
		
		return self.filesystem.attach(self, directory, filename, **kwargs)
		
	def read(self, length=None):
		"""Read from the File and return the output.
		
		Keyword arguments:
		length -- The amount of bytes to read.
		"""
		if self.request is None:
			self.request = requests.get("%s/uri/%s" % (self.filesystem.url, self.uri), prefetch=False)
		
		if length is None:
			return self.request.content
		else:
			return self.request.raw.read(amt=length)
			
