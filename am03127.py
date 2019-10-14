#!/usr/bin/python
# -*- encoding: utf-8 -*-
# implementation of the serial protocol used by
# AM03127 LED signs. Based on the document
# AM004 - 03128/03127 LED Display Board Communication
# Version 2.2, Date Aug. 13, 2005

# My LED board is a "Mc Crypt 590996 / 590998"
# LED Light Writing Board

import time

def ascii_range(c,first,last) :
	if type(c) != str or len(c) != 1 :
		return False
	if ord(c) < ord(first) or ord(c) > ord(last) :
		return False
	return True

special_map = {
	u'\n': ' ',
	u'\r': '',
	u'{': '<',
	u'}': '>',
	u'<': '<UBC>',
	u'>': '<UBE>'
}

def encode_charset(unicode_str) :
	s = ''
	i = iter(unicode(unicode_str))
	for u in i :
		if u == '\033' :
			s = s + '<' + i.next() + i.next() + '>'
		elif u in special_map :
			s = s + special_map[u]
		else :
			s = s + u.encode('cp1252')
	return s

def send_page_msg(line=1,page='A',lead=None,disp='A',wait=5,lag=None,col=None,font=None,msg='') :
	default_lead_lag = 'E'

	if not lead :
		lead = default_lead_lag
	if not lag  :
		lag  = default_lead_lag

	if line < 1 or line > 8 :
		raise RuntimeError('Line not in range 1..8')
	if not ascii_range(page,'A','Z') :
		raise RuntimeError('Page not in range A..Z')
	if not ascii_range(lead,'A','S') :
		raise RuntimeError('Lead not in range A..S')
	if not (disp in 'ABCDEQRSTUabcdeqrstu') :
		raise RuntimeError('Display not one of {ABCDEQRSTUabcdeqrstu}')
	if wait < 0 or wait > 25 :
		raise RuntimeError('Waittime not in range 0..25sec (0=0.5 sec)')
	if not ascii_range(lag,'A','S') :
		raise RuntimeError('Lag not in range A..S')
	if not (col in 'ABCDEFGHIJKLMNPQRS') :
		raise RuntimeError('Colour not one of {ABCDEFGHIJKLMNPQRS}')
	if not (font in 'ABCDE') :
		raise RuntimeError('Font not one of {ABCDE}')
	return '<L%d><P%c><F%c><M%c><W%c><F%c><C%c><A%c>'%(
		line,page,lead,disp,chr(wait+65),lag,col,font)+msg

def set_clock_msg(unixtime=None) :
	if not unixtime :
		unixtime = time.time()
	lt = time.localtime(unixtime)
	return time.strftime('<SC>%y0%u%m%d%H%M%S',lt)

def encode_msg(board_id,data) :
	if board_id < 0 or board_id > 255 :
		raise RuntimeError('Board ID not in range 0..255')
	chksum = 0
	for c in data :
		chksum ^= ord(c)
	return '<ID%02X>'%(board_id) + data + '%02X<E>'%(chksum)

def sync_transceive(port,board_id,data) :
	port.setTimeout(1)
	port.write(encode_msg(board_id,data))


	replies = [ 'ACK', 'NACK' ]
	buf = ''

	while True :
		c = port.read(1)
		if c == '' :
			return 'TIMEOUT'
		buf = buf + c

		valid_start = False
		for r in replies :
			if len(buf) > len(r) :
				continue
			if buf == r[0:len(buf)] :
				valid_start = True
				if len(buf) == len(r) :
					return buf
		if not valid_start :
			return buf # invalid

def sync_set_sign_id(port,board_id) :
	port.setTimeout(1)
	port.write('<ID><%02X><E>'%(board_id))

	buf = port.read(2)

	if len(buf) < 2 :
		raise RuntimeError('Timeout reading from port.')

	if buf == '%02X'%(board_id) :
		return True
	return False

if __name__ == '__main__' :
	import serial
	import optparse
	import sys

	P = optparse.OptionParser(usage='%prog [options] Message...')
	P.add_option('-p','--port',metavar='DEV',action='store',
		     help='Serial port (default: /dev/ttyUSB0)',
		     default='/dev/ttyUSB0')
	P.add_option('-b','--baud',metavar='BAUD',action='store',
		     type='int',help='Set baudrate (default: 9600)',
		     default=9600)
	P.add_option('-s','--signid',metavar='SIGNID',action='store',
		     type='int',help='Sign ID (default: 1)',
		     default=1)

	P.add_option('--page',metavar='PAGE',action='store',default='A',
		     help='Page (A..Z, default: A)')
	P.add_option('--lead',metavar='LEAD',action='store',default='E',
		     help='Lead (appear) effect, default: E')
	P.add_option('--lag',metavar='LAG',action='store',default='E',
		     help='Lag (disappear) effect, default: E')
	P.add_option('--disp',metavar='DISP',action='store',default='A',
		     help='Display speed (and blink/song effect), A..E, Q..U, a..e, q..u')
	P.add_option('--line',metavar='LINE',action='store',type='int',default=1,
		     help='Line (default: 1)')
	P.add_option('--wait',metavar='S',action='store',type='int',default=1,
		     help='Wait S seconds (S=0..25, 0=0.5)')
	P.add_option('--col',metavar='COLOUR',action='store',default='A',
		     help='Colour of text, default: A')
	P.add_option('--font',metavar='FONTSTYLE',action='store',default='A',
		     help='Font of text, default: A')

	P.add_option('--schedule',metavar='SCHEDULE',action='store',
		     default=None,help='Schedule (pages to display).')

	P.add_option('--settime',action='store_true',default=False,
		     help='Set sign time.')
	P.add_option('--message',action='store_true',
		     default=False,help='Send a message.')

	P.add_option('-v','--verbose',action='store_true',default=False,
		     help='Be verbose.')


	opts,args = P.parse_args()

	tty = serial.Serial(opts.port,opts.baud)

	packets = []

	if opts.schedule :
		if opts.verbose :
			print >>sys.stderr,'Setting schedule (pages %s)...'%(
				opts.schedule)
		packets.append('<TA>00010100009912312359%s'%(opts.schedule))

	if opts.settime :
		if opts.verbose :
			print >>sys.stderr,'Setting time...'
		packets.append(set_clock_msg())

	if opts.message :
		if opts.verbose :
			print >>sys.stderr,'Setting message...'

		if len(args) > 0 :
			text = u''.join(map(unicode,args))
		else :
			text=sys.stdin.read().strip()

		msg = encode_charset(text)

		if opts.verbose :
			print >>sys.stderr,'Setting message (%s)...'%(msg)

	       	data = send_page_msg(msg=msg,
		     page=opts.page,     line=opts.line,
		     lead=opts.lead,     lag=opts.lag,
		     disp=opts.disp,     wait=opts.wait,
             col=opts.col,		 font=opts.font,)

		packets.append(data)

	for data in packets :
		ret = sync_transceive(tty,opts.signid,data);
		if opts.verbose :
			print >>sys.stderr,'%s --> %s'%(data,ret)
		if ret != 'ACK' :
			print >>sys.stderr,'Could not send message %s.'%(data)
			sys.exit(1)

	sys.exit(0)
