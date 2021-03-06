"""
RenderThread.py thread and workload communication functions for client side threads.

It defines a single class RenderThread that retrieves renderrequests from a queue,
renders a frame or part of a still and communicates tatistics to a queue. It does
not implement the render() function itself but depends on a subclass to do so.
(see L{NetworkRender.AnimRenderThread} or L{NetworkRender.StillRenderThread})
"""

__author__   ='Michel Anders (varkenvarken)'
__copyright__='(cc) non commercial use only and attribution by'
__url__      =["Author's site, http://www.swineworld.org/blender"]
__email__    =['varkenvarken is my nick at blendernation.org, PM me there']
__version__  ='1.00 2008-10-20'
__history__  =['1.00 2008-10-20, initial version'
                ]

import time, xmlrpclib, socket, NetworkRender

from threading import Thread

NetworkRender.debugset()
from NetworkRender import debug

class RenderThread(Thread):
	def __init__(self, uri, scenename, context, fqueue, squeue):
		"""
		@param uri: uri of remote render server OR 'localhost'
		@type uri: string
		@param scenename: name of current scene
		@type scenename: string
		@param context: current rendering context
		@type context: Scene.Renderdata
		@param fqueue: worklist
		@type fqueue: Queue.queue
		@param squeue: rendering statistics
		@type squeue: Queue.queue
		"""

		Thread.__init__(self,name = 'thread' + uri)
		self.frames = fqueue
		self.stats = squeue
		self.failure = False
		self.stop = False

	def requestStop(self):
		self.stop = True

	def serviceAlive(self):
		"""
		Check if queue servicing is alive or finished it successfully
		"""
		return self.isAlive() or not self.failure

	def run(self):
		"""
		Run as long as there is work available in the workqueue.
		
		If an exception is caught while rendering, the workitem is put
		back on the worklist and a statistic is recorded as a failed render.

		@warning: Note that this might end up as an endless loop if a remote server
		continues to fail and the localhost thread is never fast enough to
		snatch the workitem from the queue. This needs some work!
		"""

		# this might not be correct, get(nonblocking) better?
		while not self.stop and not self.frames.empty():
			debug('%s retrieving frame from queue' % self.uri) 
			frame = self.frames.get()
			ts = time.time()
			debug('%s got frame %d' % (self.uri,frame))

			try:
				self.render(frame) # provided by mixin/subclass
			except (xmlrpclib.Error, socket.error),e:
				print 'remote exception caught',e
				print 'requeueing frame',frame

				# Need this for correct joining to the frame queue
				# (formally task is done and queue after requeueing of buggy
				# frame it will be another task)
				self.frames.task_done()

				self.frames.put(frame)
				te = time.time()
				self.stats.put((self.uri, frame, te - ts, 1, 'none'))
				self.failure = True
				break 

			te = time.time()
			self.frames.task_done()
			self.stats.put((self.uri, frame, te - ts, 0, self.result))
		debug('%s renderthread terminated' % self.uri)

