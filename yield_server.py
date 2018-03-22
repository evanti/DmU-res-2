#!/usr/bin/python3
import socket, time, queue, selectors, os, sys, threading


class Task(object):
	taskid=0
	def __init__(self, target):
		self.target=target
		self.sendval=None
		Task.taskid+=1
		self.tid=Task.taskid

	def run(self):
		return self.target.send(self.sendval)

class Scheduler(object):
	def __init__(self):
		self.mainQ = queue.Queue()
		self.taskmap = {}
		self.exit_waiting={}
		self.read_waiting={}
		self.write_waiting={}

	def waitforread(self, task, fd):
		self.read_waiting[fd]=task
	def waitforwrite(self, task, fd):
		self.write_waiting[fd]=task

	def new(self, target):
		newtask=Task(target)
		self.taskmap[newtask.tid] = newtask
		self.schedule(newtask)
		return newtask.tid

	def schedule(self, task):
		self.mainQ.put(task)

	def mainloop(self):

		while self.taskmap:
			while 1:
				try:
					task=self.mainQ.get(False)
					self.execute(task)
				except queue.Empty:
					break
			if self.write_waiting or self.read_waiting:
				events = sel.select(None)
				# print('client', events)
				if events:
					for key, mask in events:
						if mask == 2:
							if key.fd in self.write_waiting:
								sel.unregister(key.fileobj)
								task=self.write_waiting.pop(key.fd)
								self.execute(task)
						elif mask == 1:
							if key.fd in self.read_waiting:
								sel.unregister(key.fileobj)
								task=self.read_waiting.pop(key.fd)
								self.execute(task)

	def execute(self, task):
		try:
			result = task.run()
			if isinstance(result, SystemCall):
				result.task=task
				result.sched = self
				result.handle()
				return
		except StopIteration:
			self.exit(task)
			print('exit')
			return
		self.schedule(task)


	def exit(self, task):
		print("Task %s stopped" %task.tid)
		del self.taskmap[task.tid]
		for task in self.exit_waiting.pop(task.tid,[]):
			self.schedule(task)
	def waitforexit(self, task, waitid):
		if waitid in self.taskmap:
			self.exit_waiting.setdefault(waitid,[]).append(task)
			return True
		else: return False

class SystemCall(object):
	def handle(self):
		pass
class GetTid(SystemCall):
	def handle(self):
		self.task.sendval=self.task.tid
		self.sched.schedule(self.task)
class NewTask(SystemCall):
	def __init__(self, target):
		self.target=target
	def handle(self):
		tid=self.sched.new(self.target)
		self.task.sendval=tid
		self.sched.schedule(self.task)
class KillTask(SystemCall):
	def __init__(self, tid):
		self.tid=tid
	def handle(self):
		task2kill=self.sched.taskmap.get(self.tid, None)
		if task2kill:
			task2kill.target.close()
			self.task.sendval=True
		else: self.task.sendval=False
		self.sched.schedule(self.task)
class WaitTask(SystemCall):
	def __init__(self, tid):
		self.tid=tid
	def handle(self):
		result = self.sched.waitforexit(self.task, self.tid)
		self.task.sendval=result
		if not result: self.sched.schedule(self.task)
class ReadWait(SystemCall):
	def __init__(self, fobject):
		self.fobject=fobject
	def handle(self):
		fd = self.fobject.fileno()
		self.sched.waitforread(self.task, fd)
		sel.register(self.fobject, selectors.EVENT_READ)
class WriteWait(SystemCall):
	def __init__(self, fobject):
		self.fobject=fobject
	def handle(self):
		fd=self.fobject.fileno()
		# print(fd)
		self.sched.waitforwrite(self.task, fd)
		sel.register(self.fobject, selectors.EVENT_WRITE)

################################################################################################################

def handle_client(client,addr):
	global income_counter
	# while True:
	yield ReadWait(client)
	try:
		data = client.recv(2048)
	except ConnectionResetError:
		return
	if not data:
		return
	coresponse = data
	try:
		checkresp=data.decode()
		if control_line in checkresp:
			income_counter+=1
			log="From: "+str(addr)+" Time: " + str(time.time())+" Counter: "+str(income_counter)+'\n'
			with open(log_file, 'a') as fi:
				fi.write(log)
	except Exception as e:
		print(str(e))
	response = ''
	response += 'HTTP/1.1 200 OK\r\n'
	response += 'Content-Type: text/plain; charset=UTF-8\r\nContent-Length: ' + str(len(
		coresponse)) + '\r\nOrigin: ' + str(addr[0]) + '\r\nOwner: aukauk' + '\r\n\r\n'
	response = response.encode()
	response+= coresponse

	yield WriteWait(client)
	try:
		client.send(response)
	except:
		pass

	client.close()
def server(port):
	global income_counter
	sock = socket.socket()
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind(("",port))
	# print(sock.fileno())
	sock.listen(128)
	while True:
		yield ReadWait(sock)
		try:
			client,addr = sock.accept()
		except: continue
		# print(income_counter)
		yield NewTask(handle_client(client,addr))

def monit():
	global income_counter
	while 1:
		start=income_counter
		time.sleep(1)
		total = income_counter-start
		if total>0:
			with open(monit_log, 'a') as fi:
				fi.write(str(total)+'\n')

##############################################################################################################

control_line='1371648'
log_file=os.path.join(os.path.dirname(__file__), 'serverlogz.txt')
monit_log = os.path.join(os.path.dirname(__file__), 'monit_logs.txt')
print(log_file)
print(monit_log)
income_counter=0
sel=selectors.DefaultSelector()
sched=Scheduler()
sched.new(server(25000))

start=time.time()
workers=[]
workers.append(threading.Thread(target=sched.mainloop))
workers.append(threading.Thread(target=monit))
for i in workers:
	i.start()
# sched.mainloop()

