import sys, os
sys.path.append(os.path.dirname(sys.path[0]))
from auk_pack.kern import *
from auk_pack.proxycls import *
import socket, time
def execute(adrtuple):
	global success_counter
	while 1:
		s=socket.socket()
		s.setblocking(False)
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			s.connect(adrtuple)
		except BlockingIOError:
			pass
		except Exception as e:
			print(str(e))
			sched.new(execute(adrtuple))
			break
		yield WriteWait(s)
		try:
			s.sendall(request)
		except Exception as e:
			print(str(e))
			sched.new(execute(adrtuple))
			break
		yield ReadWait(s)
		try:
			resp1 = s.recv(1024)
		except Exception as e:
			print(str(e))
			sched.new(execute(adrtuple))
			break

		if 'aukauk' in resp1.decode():
			success_counter+=1
			# print("Success: ", success_counter)
			# yield Success()
		s.close()





# adrtuple=('127.0.0.1', 25000)
adrtuple=('52.214.17.228', 25000)
success_counter=0
request=prepareicanrequest()
start=time.time()
for i in range(1000):
	sched.new(execute(adrtuple))
sched.mainloop()
print(time.time()-start)
