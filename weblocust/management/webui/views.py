
#coding:utf-8

import tornado
import random
from weblocust.core.locusts import TornadoBaseLocust
import json 
import tornadis 
from tornado.escape import json_encode
import urllib 
from weblocust import settings
from weblocust.util.db import RedisConnection,RedisPipeline

class MainHandler(tornado.web.RequestHandler):
    """
        控制台,总控制页面
    """
    def get(self):
        context = {
            'title':"tornado web framework with angularjs",
            'items':('a','b','c'),
            'message':"hello,world %d" % random.randrange(1,100),
        }
        
        #TornadoBaseLocust().current().runlocust()
        
        self.render('main/index.html',**context)
    

        
        
class InfoCenter(tornado.web.RequestHandler):
    """
        接收所有来自其它节点的信息，并做持久化;
        提供机群的信息
        代理administrator发出命令和请求
        一次更新所有能够获知的信息
    """
    def initialize(self):
        #self.__redis_client = tornadis.Client(host=settings.REDIS_SERVER,port=6379,autoconnect=True)
        pass
        
    @tornado.gen.coroutine
    def get(self):
        """
            提供整个集群的信息
            请求地址：/infocenter
        """
        redis_pipeline = RedisPipeline()
        #redis_pipeline.stack_call("llen",settings.REQUEST_QUEUE)
        redis_pipeline.stack_call("smembers",settings.CLUSTER_NODE_SET)
        cluster_info = yield RedisConnection().call(redis_pipeline)
        # 第一次redis访问查看 队列长度 和 slave nodes
        
        redis_pipeline = RedisPipeline()
        for node in cluster_info[0]:
            redis_pipeline.stack_call("hgetall",node)

        nodes_info = yield RedisConnection().call(redis_pipeline)
        # 第二次查询 获得所有的节点信息
        sysinfo = {
            "task_queue_length":999,
            "tooken":random.randrange(1,10000),
            "nodes":nodes_info,
        }

        self.write(sysinfo)
        self.finish()
        
    @tornado.gen.coroutine           
    def post(self):
        """
           接收slave发过来的节点数据，并将写到redis当中
        """
        nodeinfo = {
            "ip":self.get_body_argument("ip"),
            "role":self.get_body_argument("role"),
            "port":self.get_body_argument("port"),
            "running":True if self.get_body_argument("running")=="True" else False,
            "paused":True if self.get_body_argument("paused")=="True" else False,
            "load_factor":self.get_body_argument("load_factor"),
            "concurrency":self.get_body_argument("concurrency"),
            "qsize":self.get_body_argument("qsize"),

        }
        redis_pipeline = RedisPipeline()
        
        node_name = u"%s:%s"%(nodeinfo["ip"],nodeinfo["port"]) 
        
        #redis_param = []
        #for k,v in nodeinfo.items():
        #    redis_param.extend([k,v])
        redis_param = json.dumps(nodeinfo)
        
        redis_pipeline.stack_call("sadd",settings.CLUSTER_NODE_SET,node_name)
        redis_pipeline.stack_call("hmset",node_name,"node_info",redis_param)
        redis_pipeline.stack_call("expire",node_name,8)
        result = yield RedisConnection().call(redis_pipeline)
        self.finish()
        
class LocustController(tornado.web.RequestHandler):
    """
    
    def prepare(self):
        if self.request.headers["Content-Type"].startswith("application/json"):
            self.json_args = json.loads(self.request.body)
        else:
            self.json_args = None    
    """
            
    def post(self):
        operation = json.loads(self.request.body).get("action")
        if hasattr(self,operation):
            reply = getattr(self,operation)()
        else:
            reply = {"error":1,"msg":"errors"}
            
        self.write(reply)
            
    def start(self):
        TornadoBaseLocust().current().runlocust()
        return {"error":0,"smg":"start the locust"}
    
    def restart(self):
        TornadoBaseLocust().current().restart()
        return {"error":0,"smg":"start the locust"}
    
    def pause(self):
        TornadoBaseLocust().current().pause()
        return {"error":0,"smg":"pause the locust"}        
        
    def resume(self):
        TornadoBaseLocust().current().resume()
        return {"error":0,"smg":"pause the locust"}