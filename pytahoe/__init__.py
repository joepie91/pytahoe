import urllib, urllib2, json, time, os, re, requests

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


class FilesystemException(Exception):
	pass

class ObjectException(Exception):
	pass

class UploadException(Exception):
	pass

class DependencyException(Exception):
	pass

class Filesystem:
	def __init__(self, url="http://localhost:3456/"):
		if url.strip() == "":
			raise FilesystemException("You must specify a Tahoe-LAFS WAPI URL.")
		
		# Ensure there is no trailing slash in the WAPI URL
		if url[-1:] == "/":
			url = url[:-1]
		
		try:
			result = urllib.urlopen("%s/statistics?t=json" % url).read()
		except urllib.URLError:
			raise FilesystemException("The provided WAPI URL is not reachable.")
		
		try:
			data = json.loads(result)
		except ValueError:
			raise FilesystemException("The provided WAPI URL is either not running Tahoe-LAFS, or running a version that is too old.")
		
		if "node.uptime" not in data['stats']:
			raise FilesystemException("The provided WAPI URL is either not running Tahoe-LAFS, or running a version that is too old.")
		
		self.url = url
		self.start_date = time.time() - data['stats']['node.uptime']
	
	def standard_request(self, destination, data=None):
		return self.do_json_request("/%s?t=json" % destination, data)
		
	def do_request(self, destination, data=None):
		if data is not None:
			post_data = urllib.urlencode(data)
		
		try:
			if data is None:
				return urllib.urlopen("%s%s" % (self.url, destination)).read()
			else:
				return urllib.urlopen("%s%s" % (self.url, destination), post_data).read()
		except urllib.URLError:
			raise FilesystemException("The WAPI could not be reached.")
	
	def do_json_request(self, destination, data=None):
		results = self.do_request(destination, data)
		
		try:
			return json.loads(results)
		except ValueError:
			raise FilesystemException("Corrupted data was received from the WAPI")
	
	def do_put_request(self, destination, data, headers):
		request = urllib2.Request("%s%s" % (self.url, destination), data, headers)
		return urllib2.urlopen(request).read()
	
	def Directory(self, uri, data=None):
		if data == None:
			data = self.standard_request("uri/%s" % urllib.quote(uri))
		
		return Directory(self, uri, data)
	
	def File(self, uri, data=None):
		if data == None:
			data = self.standard_request("uri/%s" % urllib.quote(uri))
		
		return File(self, uri, data)
	
	def Object(self, uri, data=None):
		if data == None:
			data = self.standard_request("uri/%s" % urllib.quote(uri))
		
		if "filenode" in data:
			return self.File(uri, data)
		elif "dirnode" in data:
			return self.Directory(uri, data)
		else:
			raise ObjectException("The specified object does not appear to exist.")
	
	def create_directory(self):
		result = self.do_request("/uri?t=mkdir", {})
		return self.Directory(result)
	
	def _sanitize_filename(self, name):
		return re.sub("[^a-zA-Z0-9 $_.+!*'(),-]+", "", name)
	
	def upload(self, filedata):
		if type(filedata) is str:
			try:
				filedata = open(filedata, "rb")
			except IOError:
				raise UploadException("The given path is not a valid file path.")
		elif type(filedata) is not file:
			raise UploadException("Cannot upload the file because the given file is not a valid file object or path.")
				
		file_uri = requests.put("%s/uri" % self.url, data=filedata.read()).text
		return self.File(file_uri)

class Directory:
	mutable = False
	writeable = False
	children = {}
	
	def __init__(self, filesystem, uri, data=None):
		self.filesystem = filesystem
		self.uri = uri
		
		if data == None:
			data = self.filesystem.standard_request("uri/%s" % urllib.quote(uri))
		
		if "dirnode" in data:
			details = data[1]
			
			self.mutable = details['mutable']
			self.readcap = details['ro_uri']
			
			if "verify_uri" in details:
				self.verifycap = details['verify_uri']
			
			if "rw_uri" in details:
				self.writable = True
				self.writecap = details['rw_uri']
				
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
	
	def __repr__(self):
		if self.writable == True:
			state = "writable"
		else:
			state = "read-only"
		
		return "<pytahoe.Directory %s (%s)>" % (self.uri, state)
	
	def mount(self, mountpoint):
		global fs_available
		
		if fs_available == False:
			raise DependencyException("Could not mount the directory because the 'fs' module was not found.")
		
		fs = TahoeLAFS(self.uri)
		
		try:
			return fuse.mount(fs, mountpoint)
		except OSError:
			try:
				return dokan.mount(fs, mountpoint)
			except OSError:
				raise DependencyException("Could not mount the directory because both the FUSE and dokan libraries are unavailable.")
	
	def upload(self, filedata, filename=None):
		if filename is None:
			if type(filedata) is str:
				filename = self._sanitize_filename(os.path.basename(filedata))
			elif type(filedata) is file:
				if type(filedata.name) is str:
					filename = self._sanitize_filename(filedata.name)
				else:
					# We could not determine the filename for the input... let's generate something.
					filename = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(15))
			else:
				raise UploadException("The given file is not a valid string or file object.")

class File:
	mutable = False
	writable = False
	
	def __init__(self, filesystem, uri, data=None):
		self.filesystem = filesystem
		self.uri = uri
		
		if data == None:
			data = self.filesystem.standard_request("uri/%s" % urllib.quote(uri))
		
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
		if self.writable == True:
			state = "writable"
		else:
			state = "read-only"
		
		if self.mutable == True:
			mutable = "mutable"
		else:
			mutable = "immutable"
		
		return "<pytahoe.File %s (%s, %s)>" % (self.uri, mutable, state)
