import os

stat = os.statvfs("/")
size = stat[1] * stat[2]
free = stat[0] * stat[3]
used = size - free

KB = 1024
MB = 1024 * 1024

print("Size : {:,} bytes, {:,} KB, {} MB".format(size, size / KB, size / MB))
print("Used : {:,} bytes, {:,} KB, {} MB".format(used, used / KB, used / MB))
print("Free : {:,} bytes, {:,} KB, {} MB".format(free, free / KB, free / MB))

print('/:', os.listdir())
print('/lib:', os.listdir('/lib'))
print('/anims:', os.listdir('/anims'))
