# Compowarm
Compose is a tool for defining and running complex applications with Docker. With Compose, you define a multi-container application in a single file named docker.yml, then spin your application up in a single command which does everything that needs to be done to get it running.

But the drawback of Compose is that  all the containters you defined in docker.yml will be runned just only in one nodes.In other words,it cannot deploy your containers in multiple nodes.

So Docker release another tool named Swarm,It is native clustering for Docker. It turns a pool of Docker hosts into a single, virtual host.With Swarm you can deploy your containers in multiple nodes,But at the moment,Swarm is a little complicated compared with compose.

Compowarm is a very very simple tools that mix the functions of swarm and compose.You can use this tool in the way that the same as compose.

The different is that there is a new  option called "ships" in the docker.yml which is not exists in Compose.WIth "ships",you can define the ip address of the nodes that you want your container to be runned on it.For example:
<pre><code>
ships:
  - 10.13.181.83
  - 10.13.181.84
</code></pre>

The theory of Compowarm is that when containers are runned,The containers which links other containers will has some environment variables,these variables' name are the name that this containier to linked plus "_ip",the values are the ip address of the nodes that run the linked containers.

<pre><code>
client:
  image: flask
  ports:
  - "5000:5000"
  links:
  - redis
  expose:
  - "5000"
redis:
  image: redis
  expose:
  - "6379"
  ports:
  - "6379:6379"
ships:
  - 192.168.1.83
  - 192.168.1.84
</code></pre>
In this example,container named client and redis will be runned in the nodes that defined by "ships" option.And client links redis,So once client is been runned,it will has a environment variable named "redis_ip",with the value 192.168.1.183 if redis is runned on the 192.168.1.183.And in client,you can get the ipaddress from environment variables.The you can communicate with redis through this variable.

At the momont,I just implements ps,start,stop.And the other function is still been developed.
