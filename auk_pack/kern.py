import time, queue, selectors

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
		self.timeout_waiting={}
		self.success_rate={}

	def waitforread(self, task, fd, fileobj, expire):
		self.read_waiting[fd]=(task, fileobj, expire)

	def waitforwrite(self, task, fd, fileobj, expire):
		self.write_waiting[fd]=(task, fileobj, expire)

	def got_success(self, target):
		try:
			self.success_rate[target.gi_code]+=1
		except KeyError:
			print('WE HAVE A SERIOUS PROBLEM')
			return

	def define_success(self, target):
		try:
			if self.success_rate[target.gi_code]>0: return
		except KeyError:
			self.success_rate[target.gi_code]=0

	def new(self, target):
		newtask=Task(target)
		self.taskmap[newtask.tid] = newtask
		self.schedule(newtask)
		self.define_success(target)
		return newtask.tid

	def schedule(self, task):
		self.mainQ.put(task)

	def mainloop(self, counter=0, target=None):
		def event_buffer(buffsize=10, t_out=3):
			eventis = []
			if t_out:
				l_start=int(time.time())
				l_finish=l_start+t_out
			while 1:
				eventsnew = sel.select(3)
				eventis += eventsnew
				res_events=set(eventis)
				if len(res_events) > buffsize:
					return res_events
				if t_out:
					if time.time()>l_finish:
						return res_events
		loopcounter=0
		currentcounter = 0
		c2=0
		caught=1
		while self.taskmap:
			# if self.stopall: exit()
			loopcounter+=1

			if target and counter>0:
				currentcounter=self.success_rate[target.gi_code]
				if currentcounter> counter: return
			work2do=self.mainQ.qsize()

			for i in range(work2do):
				try:
					task=self.mainQ.get(False)
					self.execute(task)
					task.sendval=None
				except queue.Empty:
					break

			if self.write_waiting or self.read_waiting:
				lenread=len(self.read_waiting)
				lenwrite = len(self.write_waiting)
				c1=time.time()
				looptime=int((c1-c2)*1000000)
				if caught!=0:
					timeperevent = looptime/caught
				else: timeperevent=0
				events=event_buffer()
				caught=len(events)
				# if caught==0:
				# 	break
				c2=time.time()
				eventtime=str(int((c2-c1)*1000000))
				# print(events)
				print('events:', caught, 'event_time:', eventtime, 'loop_time:', str(looptime), 'time/event', str(timeperevent))
				# print('loops:', loopcounter, 'events:', caught, 'event_time:', eventtime, 'loop_time:', str(looptime),
				#       'write:', lenwrite, 'read:',lenread, 'workers:', lenread+lenwrite, 'time/event:',
				#       str(timeperevent), file=open('mainlogs.txt','a')) #
				# 'hits:',currentcounter,
				for key, mask in events:
					if mask == 2:
						if key.fd in self.write_waiting:
							sel.unregister(key.fileobj)
							task=self.write_waiting.pop(key.fd)[0]
							self.execute(task)
					elif mask == 1:
						if key.fd in self.read_waiting:
							sel.unregister(key.fileobj)
							task=self.read_waiting.pop(key.fd)[0]
							self.execute(task)
				self.garbcollect()
			# print(self.taskmap)


	def garbcollect(self):
		now = int(time.time())

		if self.write_waiting:
			todel=[]
			for i,j in self.write_waiting.items():
				if j[2]>0 and j[2]<now:
					sel.unregister(j[1])
					task=self.write_waiting.get(i)[0]
					task.sendval = True
					self.schedule(task)
					todel.append(i)

			for z in todel:
				self.write_waiting.pop(z)
		now = int(time.time())
		if self.read_waiting:
			todel = []
			for i,j in self.read_waiting.items():
				if j[2]>0 and j[2]<now:
					sel.unregister(j[1])
					task=self.read_waiting.get(i)[0]
					task.sendval = True
					self.schedule(task)
					todel.append(i)
			for z in todel:
				self.read_waiting.pop(z)


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
	def __init__(self, fobject, timeout=60):
		self.fobject=fobject
		self.timeout=timeout
	def handle(self):
		fd = self.fobject.fileno()
		sel.register(self.fobject, selectors.EVENT_READ)
		if self.timeout:
			expire = int(time.time())+self.timeout
		else: expire=None
		self.sched.waitforread(self.task, fd, self.fobject, expire)
class WriteWait(SystemCall):
	def __init__(self, fobject, timeout=60):
		self.fobject=fobject
		self.timeout = timeout
	def handle(self):
		fd=self.fobject.fileno()
		try:
			sel.register(self.fobject, selectors.EVENT_WRITE)
		except ValueError:
			print(self.fobject)
			print(fd)
		if self.timeout:
			expire = int(time.time()) + self.timeout
		else: expire=None
		self.sched.waitforwrite(self.task, fd, self.fobject, expire)
class Success(SystemCall):
	def handle(self):
		self.target=self.task.target
		self.sched.got_success(self.target)
		self.sched.schedule(self.task)

sel=selectors.DefaultSelector()
sched=Scheduler()
print('kern imported')
