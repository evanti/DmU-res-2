import queue, os, requests,dns.resolver
from operator import attrgetter

class Proxy(object):
	ht=1
	http=2
	socks4=4
	socks5=5
	def __init__(self, oneline, newproxy=False):
		oneline=oneline.split(' ')
		self.proxyline = oneline[0]
		try:
			host, port = self.proxyline.split(':')
		except ValueError:
			print(oneline)
			exit()
		self.adrtuple = (host, int(port))
		if newproxy:
			self.proxytype = 0
			self.httpcheck = 0
			self.httpscheck = 0
			self.outgoingIP = 0
			self.transparent = 0
			self.numtries=0
			self.numsucctries=0
			self.rating=0
		else:
			self.proxytype = int(oneline[1])
			self.httpcheck = int(oneline[2])
			self.httpscheck = int(oneline[3])
			self.outgoingIP = oneline[4]
			self.transparent = int(oneline[5])
			self.numtries = int(oneline[6])
			self.numsucctries = int(oneline[7])
			self.rating = int(oneline[8])

	def saveself(self):
		res=(self.proxyline, self.proxytype, self.httpcheck, self.httpscheck, self.outgoingIP, self.transparent,
		     self.numtries, self.numsucctries, self.rating)
		ress=[str(x) for x in res]
		resss=' '.join(ress)
		return resss

	def __repr__(self):
		info={
			'Address':self.proxyline,
			# "Responds": self.responding,
			'Proxy type': self.proxytype,
			'HTTP': self.httpcheck,
			# 'Time': round(self.httptime,2),
			'HTTPS': self.httpscheck,
			# 'HTTPS Time': round(self.httpstime,2),
			'Transparent': self.transparent,
			'Outgoing IP': self.outgoingIP,
			'Number of tries': self.numtries,
			'Successful tries': self.numsucctries,
			'Rating' : self.rating
		}
		explain='Proxy summary:\r\n'
		explain+="\n".join("{}: {}".format(k, v) for k, v in info.items())
		return explain

	def __add__(self, other):
		if not isinstance(other, Proxy):
			raise TypeError('must be Proxies both')
		if self.proxyline!=other.proxyline:

			raise TypeError('must refer to the same proxies')

		resline=self.proxyline
		resproxytype=max(self.proxytype, other.proxytype)
		reshttpcheck=max(self.httpcheck, other.httpcheck)
		reshttpscheck = max(self.httpscheck, other.httpscheck)
		resoutIP=self.outgoingIP
		restransaprent=max(self.transparent, other.transparent)
		resnumtries=max(self.numtries,other.numtries)
		resnumsucctries = max(self.numsucctries, other.numsucctries)
		resrating=max(self.rating, other.rating)
		res=Proxy(resline, True)
		res.proxytype=resproxytype
		res.httpcheck=reshttpcheck
		res.httpscheck=reshttpscheck
		res.outgoingIP=resoutIP
		res.transparent=restransaprent
		res.numtries=resnumtries
		res.numsucctries=resnumsucctries
		res.rating=resrating
		return res


def routine_checks(oldname='MainDB-old.txt',newname='MainDB-new.txt', add_file= 'DBaddition.txt'):
	pass


def add_all(samefile):
	with open(samefile) as fi:
		content = fi.read().splitlines()
		a = []
		for i in content:
			if len(i) > 0:
				try:
					a.append(Proxy(i))
				except:
					print("Doesn't look like a valid proxyline", i)
					return
		b = sorted(a, key=attrgetter('proxyline'))
		q = 0
		while q < len(b) - 1:
			if b[q].proxyline == b[q + 1].proxyline:
				b[q] = b[q] + b[q + 1]
				del b[q + 1]
				continue
			else:
				q += 1
	with open(samefile, 'w') as fi:
		for i in b:
			fi.write(i.saveself() + '\r\n')
	print('there are now', q+1, 'in file ', samefile)


def prepareicanrequest():
	icanhaziprequest=[]
	icanhaziprequest.append('GET / HTTP/1.1')
	icanhaziprequest.append('Host: icanhazip.com')
	icanhaziprequest.append('Upgrade-Insecure-Requests: 1')
	icanhaziprequest.append('User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.162 Safari/537.36')
	icanhaziprequest.append('Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8')
	icanhaziprequest.append('Accept-Encoding: gzip, deflate, br')
	icanhaziprequest.append('Accept-Language: en-US,en;q=0.9')
	icanhaziprequest.append('Phone-num: 1371648')
	icanhaziprequest.append('X-Compress: null')
	icanhaziprequest.append('Cache-Control: no-cache')
	icanhaziprequest=('\r\n').join([x for x in icanhaziprequest])+'\r\n\r\n'
	icanhaziprequest=icanhaziprequest.encode()
	return icanhaziprequest
# os.rename('MainDB-new.txt', 'MainDB-old.txt')

def icancheck():
	r=requests.get('http://icanhazip.com')
	res1=r.status_code==200
	r2=requests.get('https://icanhazip.com')
	res2=r.status_code==200
	a=r.text[:len(r.text)]
	answers = dns.resolver.query('icanhazip.com', 'A')
	addresses=[str(i) for i in answers]
	return (res1, res2, a, addresses)

def s4response(respline):
	if len(respline)>1:
		z = [hex(x)[2:] for x in respline]
		if z[1] == '5a':
			return True
		else:
			# print(z)
			return False
	else: return False

def s51response(respline):
	if len(respline) > 1:
		z = [hex(x)[2:] for x in respline]
		if z[0] == '5' and z[1] == '0':
			return True
		else:
			# print(z)
			return False
	else: return False

def s52response(respline):
	if len(respline)>1:
		z2 = [hex(x)[2:] for x in respline]
		if z2[1] == '0':
			return True
		else:
			# print(z2)
			return False
	else: return False

def connectresponse(respline):
	if len(respline)>0:
		try:
			response = respline.decode()
		except:
			# print(respline)
			return False
		if "200 OK" in response:
			return True
		else:
			# print(response)
			return False
	else: return False

socks51handshake=b'\x05\x01\x00'
# print('proxycls imported')
