#coding:utf-8

from tornado import httpclient,gen,ioloop,queues
from . import SigleInstance
import tornadis 
from .httpclient import Request
import json
from weblocust.util.db import RedisConnection,RedisPipeline
from . import SigleInstance
from weblocust import settings

class TaskQueue(object):
    """
    all task queue derive from this class
    """
    #__metaclass__ = SigleInstance
    

    def get(self):
        raise NotImplementedError

    def put(self,request):
        raise NotImplementedError

    def qsize(self):
        raise NotImplementedError
    
        
        
class NormalTaskQueue(TaskQueue):
    """
    this queue use tornado built in queue,since we need an asychronous queue;
    
    """

    def __init__(self):
        self.queue = queues.Queue()


    @gen.coroutine
    def get(self):
        task = yield self.queue.get()
        raise gen.Return(task)
    
    @gen.coroutine
    def put(self,request):
        ack = yield self.queue.put(request)
        raise gen.Return(ack)

    @gen.coroutine
    def qsize(self):
        qsize = yield self.queue.qsize()
        raise gen.Return(qsize)

    
class RedisTaskQueue(TaskQueue):
    """
    this queue use redis the memory database;by this way ,
    this framework turn into a distribute system be possible
    """
    #__metaclass__ = SigleInstance
    def __init__(self,queue_name):
        self.queue_name = queue_name

    @gen.coroutine    
    def get(self):
        """
        get a request instance from queue
        """
        r = yield RedisConnection().call("LPOP",self.queue_name)
        while not r:
            # 没有任务的情况下肯定会阻塞，所以暂时交出控制权
            # 只有一条redis链接，这里要是阻塞了，所有的都会阻塞。所以没有用BLPOP
            yield gen.sleep(2)
            r = yield RedisConnection().call("LPOP",self.queue_name)
            
            
        if isinstance(r,tornadis.TornadisException):
            # 发生exceptions 的情况下，返回None
            # 或者直接raise一个exception
            print "got exception: %s " % r
            raise gen.Return(None)

        #反序列化，恢复Request    
        req = json.loads(r)
        request = Request(**req)
        raise gen.Return(request)
        
    @gen.coroutine    
    def put(self,request):
        """ 
        put request's attribute to queue 
        since we can't push a python instance to redis,
        we have to make all attribute to string
        fortunately,json.dumps make dict to string,and instance's attributes
        stores in instance.__dict__
        """
        r = request.__dict__
        req = json.dumps(r)
        ack = yield RedisConnection().call("rpush",self.queue_name,req)
        raise gen.Return(ack)

    @gen.coroutine
    def qsize(self):
        yield RedisConnection().call("expire",self.queue_name,1*60*60)
        qsize = yield RedisConnection().call("llen",self.queue_name)
        raise gen.Return(qsize)
        
