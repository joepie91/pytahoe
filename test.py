import pytahoe

fs = pytahoe.Filesystem("http://localhost:3456/")
#tdir = fs.Directory("URI:DIR2:jjw572jvowd473fo2n7rw6uiai:hloglrouhwgjpubcpyq5nrb4ezyijdfiboe3hquadgzjrmkdikxa")
#print tdir
#for name, item in tdir.children.iteritems():
#	print "%s: %s" % (name, item)

#print fs.create_directory().mount("test")
print fs.upload("test.py")
