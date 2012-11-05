import pytahoe

fs = pytahoe.Filesystem("http://tahoe.ccnmtl.columbia.edu/")
#fs = pytahoe.Filesystem("http://localhost:3456/")
#print fs
#tdir = fs.Directory("URI:DIR2:jjw572jvowd473fo2n7rw6uiai:hloglrouhwgjpubcpyq5nrb4ezyijdfiboe3hquadgzjrmkdikxa")
#print tdir
#for name, item in tdir.children.iteritems():
#	print "%s: %s" % (name, item)

#print fs.create_directory().mount("test")
#print fs.upload("test.py")

tdir = fs.Directory("URI:DIR2:cbk47f5lybaj5qh6bm6eedezwe:m525plntx47u44xvf44r6rliec3gp6yeyio7olndibtke75zb6fa")

#print tdir.attach(fs.File("URI:CHK:j3jkuy73tnkj7glyatasluq2xe:hcluqizbrhdpqa7fugmiwtaxf42f2ssvk7emyyat7wm4xr3ehgfa:3:10:534"), "derp.py")
print tdir.attach(fs.File("URI:CHK:j3jkuy73tnkj7glyatasluq2xe:hcluqizbrhdpqa7fugmiwtaxf42f2ssvk7emyyat7wm4xr3ehgfa:3:10:534"), "This is just a (*@Y#%)()@#&%)(*@&#% test to see how well it sanitizes a filename..py")
