import pytahoe


#fs = pytahoe.Filesystem("http://localhost:3456/")
#print fs
#tdir = fs.Directory("URI:DIR2:jjw572jvowd473fo2n7rw6uiai:hloglrouhwgjpubcpyq5nrb4ezyijdfiboe3hquadgzjrmkdikxa")
#print tdir
#for name, item in tdir.children.iteritems():
#	print "%s: %s" % (name, item)

#print fs.create_directory().mount("test")
#print fs.upload("test.py")



#print tdir.attach(fs.File("URI:CHK:j3jkuy73tnkj7glyatasluq2xe:hcluqizbrhdpqa7fugmiwtaxf42f2ssvk7emyyat7wm4xr3ehgfa:3:10:534"), "derp.py")
#print tdir.attach(fs.File("URI:CHK:j3jkuy73tnkj7glyatasluq2xe:hcluqizbrhdpqa7fugmiwtaxf42f2ssvk7emyyat7wm4xr3ehgfa:3:10:534"), "This is just a (*@Y#%)()@#&%)(*@&#% test to see how well it sanitizes a filename..py")

fs = pytahoe.Filesystem("http://tahoe.ccnmtl.columbia.edu/")

#tfile = fs.File("URI:CHK:iyq5houj2fqavmnqccqezcssle:5px5tdctmmvci4al2r3vskpblhrepuugfe6ghiuutpe6cllvo36a:3:10:997")
#print tfile.read(65)

#print fs
#
#tfile = fs.upload("test.py")
#print tfile
#
tdir = fs.Directory("URI:DIR2:cbk47f5lybaj5qh6bm6eedezwe:m525plntx47u44xvf44r6rliec3gp6yeyio7olndibtke75zb6fa")

print tdir.create_directory("testing subdir4")
tdir.refresh()
print tdir.children
#print tdir.upload("test.py")

#print tdir
#
#print tfile.attach(tdir, "sample // file 2.py")
