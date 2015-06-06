# -*- coding:utf-8 -*-
import yaml
import docker
import yaml
# from Queue import Queue

yml_file = "docker.yml"
ip_list = []
used_ip_list = []
app_list = []  # container name list
container_list = {}  # container list
port = 2375
containers_info = {}  # 记录每个container的信息，记录每一个启动之后的container的信息
config_file = "/home/my_compose.yml"

def is_independent_service(service):
    '''
    判断是否是独立的service
    :param service:
    :return:独立则为True，不独立则为False
    '''
    if not service.has_key("links"):
        return True
    return False


def __get_container_ip(image_tag):
    '''
    get the ip address that has the image named app_name
    :param image_tag:
    :return:
    '''
    global ip_list,used_ip_list  # the word "global" is necessary

    container_ip = None

    if 0 == len(ip_list):
       ip_list,used_ip_list = used_ip_list,ip_list

    print "ip_list in __get_container_ip is {0}".format(ip_list)
    print "used_ip_list in __get_container_ip is {0}".format(used_ip_list)

    image_name = image_tag if ":" in image_tag else image_tag +":latest"
    # print "image_name={0}".format(image_name)

    print "image_name = {0}".format(image_name)

    # 先查找ip_list里面的节点是否可用
    for ip in ip_list:
        cli = docker.Client(base_url="{ip}:{port}".format(ip=ip,port=port))
        images = cli.images()
        for image in images:
            name = image.get("RepoTags")
            # print "name = {0}".format(name[0])
            if image_name == str(name[0]):
                container_ip = ip
                used_ip_list.append(ip)
                ip_list.remove(ip)

    if container_ip is None:
        for ip in used_ip_list:
            cli = docker.Client(base_url="{ip}:{port}".format(ip=ip,port=port))
            images = cli.images()
            for image in images:
                name = image.get("RepoTags")
                if image_name == str(name[0]) :   # 注意：这里一定要用str转化为字符串，因为获取到的是unicode
                    container_ip = ip

    if container_ip is None:
        # if all the nodes in the cluster does not have the image
        # then pull down the image
        cli = docker.Client(base_url="{ip}:{port}".format(ip=ip_list[0],port=port))
        cli.pull(image_name)
        container_ip = ip_list[0]
        ip_list.remove(container_ip)
        used_ip_list.append(container_ip)

    print "image:{0}  ip:{1}".format(image_name,container_ip)

    return container_ip


def exec_containers(yml_data):
    '''
    启动容器
    :param yml_data:
    :return:
    '''
    for app in app_list:
        contair_detial = yml_data.get(app)
        image = contair_detial.get("image") if contair_detial.has_key("image") else None
        if image is None:
            print "image不能为空"  # raise error
            return

        # get the node ip that run the container
        ip_address = __get_container_ip(image)

        ports_str = contair_detial.get("ports") if contair_detial.has_key("ports") else None
        volumes = contair_detial.get("volumes") if contair_detial.has_key("volumes") else None
        command = contair_detial.get("commands") if contair_detial.has_key("commands") else None
        expose_str = contair_detial.get("expose") if contair_detial.has_key("expose") else None
        links_str = contair_detial.get("links") if contair_detial.has_key("links") else None

        port_bindings = {} # 要绑定的端口
        if ports_str is not None:
            for i in range(0,len(ports_str)):
                port_bindings[ports_str[i].split(":")[1]] = ports_str[i].split(":")[0]

        # print "port_bindings = {0}".format(port_bindings)

        expose_ports = [] # 要暴露的端口
        if expose_str is not None:
            for port in expose_str:
                expose_ports.append(int(port))

        volumes_binds = {} # 要挂载的卷
        if volumes is not None:
            for volume in volumes:
                v = volume.split(":")
                binds = {}
                binds["ro"] = False
                binds["bind"] = v[1]
                volumes_binds[v[0]] = binds
        # print "volumes_binds = {0}".format(volumes_binds)

        environment = {}
        if links_str is not None:
            for link in links_str:
                ip_env_key = link + "_ip_"
                ip_env_value = container_list.get(link).get("ip")
                port_env_key = link + "_port_"
                port_env_value = container_list.get(link).get("port")
                environment[ip_env_key] = ip_env_value
                environment[port_env_key] = port_env_value

        cli = docker.Client(base_url="{host}:{port}".format(host=ip_address,port=2375))
        container = cli.create_container(image=image,ports=expose_ports,
                                         name=app,
                                         environment=environment,
                                         command=command)
        cli.start(container,port_bindings=port_bindings,binds=volumes_binds)

        # put the node info into the container_list
        info = {}
        info["ip"] = ip_address
        info["port"] = ports_str[i].split(":")[0]
        info["image"] = image
        container_list[app] = info
        # print "container_list = {0}".format(container_list)

        # 记录每个启动的日容器的信息,包括
        container_info = {}
        container_info["node_ip"] = ip_address  # 运行容器的主机IP
        image_name = image if ":" in image else image +":latest"
        container_info["image"] = image_name # 运行的服务的名称
        container_info["status"] = "up"  # 当前的状态为up
        containers_info[app] = container_info

    # 把所有的运行了的容器的信息保存到文件里面去
    f = open(config_file,"w")
    yaml.dump(containers_info,f)
    f.close()


def exec_container(name,service,host):
    '''
    启动一个容器
    :param name:要运行的服务的名称
    :param service:要运行的服务
    :param host:运行服务的主机的IP地址
    :return:
    '''
    print "service的名字是{0}".format(name)
    print "service in exec_container is {0}".format(service)
    image = service.get("image") if service.has_key("image") else None
    print "image is {0}".format(image)
    if image is None:
        print "image不能为空"
        return

    ports_str = service.get("ports") if service.has_key("ports") else None
    volumes = service.get("volumes") if service.has_key("volumes") else None
    command = service.get("commands") if service.has_key("commands") else None
    expose_str = service.get("expose") if service.has_key("expose") else None
    links_str = service.get("links") if service.has_key("links") else None

    print "links_str = {0}".format(links_str)

    port_bindings = {} # 要绑定的端口
    if ports_str is not None:
        for i in range(0,len(ports_str)):
            port_bindings[ports_str[i].split(":")[1]] = ports_str[i].split(":")[0]

    print "port_bindings = {0}".format(port_bindings)

    expose_ports = [] # 要暴露的端口
    if expose_str is not None:
        for port in expose_str:
            expose_ports.append(int(port))

    print "expose_ports = {0}".format(expose_ports)


    volumes_binds = {} # 要挂载的卷
    if volumes is not None:
        for volume in volumes:
            v = volume.split(":")
            binds = {}
            binds["ro"] = False
            binds["bind"] = v[1]
            volumes_binds[v[0]] = binds
    print "volumes_binds = {0}".format(volumes_binds)

    links = ""
    if links_str is not None:
        links = links_str[0]

    environment = {links+"_my_compose__":"10.13.181.83"} # the env pass to client

    cli = docker.Client(base_url="{host}:{port}".format(host=host,port=2375))
    container = cli.create_container(image=image,ports=expose_ports,
                                     name=name+"_my_compose__",
                                     environment=environment)
    cli.start(container,port_bindings=port_bindings,binds=volumes_binds)
    print "begin to exec {0}".format(name)


def compose(file_name):
    f = open(file_name)

    yml_data = yaml.load(f)
    f.close()
    print "yml_data = {0}".format(yml_data)
    global ip_list
    # ships = [] # 记录所有的的节点的IP
    if yml_data.has_key("ships"):
        ip_list = yml_data.pop("ships")
    else:
        print "没有ships选项"  # 替换为raise error
        return

    __set_app_list(yml_data.keys(),yml_data)
    print "app_list = {0}".format(app_list)

    exec_containers(yml_data)


def ps(all=False):
    '''
    list the info of all the containers descriptes in the docker.yml file
    :return:
    '''
    # 从配置文件中读取正在运行的容器的信息
    f = open(config_file,"r")
    containers = yaml.load(f)
    f.close()

    print "containers={0}".format(containers)
    for container in containers.keys():
        print "container = {0}".format(container)
        info = containers.get(container)
        # print "info = {0}".format(info)
        ip = info.get("node_ip")
        image = info.get("image")
        # print "image_name = {0}".format(image)
        cli = docker.Client(base_url="{ip}:{port}".format(ip=ip,port=port))
        containers_in_node = cli.containers(all=all)  # 节点上所有运行的container
        for container_node in containers_in_node:
            container_name = container_node.get("Names")
            if "/" + container == str(container_name[0]):
                for i in container_node.keys():
                    print "{0}:{1}".format(i,container_node.get(i))


def stop(remove=False):
    '''
    stop all the conotainers
    :return:
    '''
    f = open(config_file,"r")  # 从文件中读取信息
    containers = yaml.load(f)
    f.close()

    remove_list = []  # 要删除的容器的列表

    for container in containers.keys():
        print "container = {0}".format(container)
        info = containers.get(container)
        ip = info.get("node_ip")
        image = info.get("image")
        print "image_name = {0}".format(image)
        cli = docker.Client(base_url="{ip}:{port}".format(ip=ip,port=port))
        containers_in_node = cli.containers(all=True)  # 节点上所有运行的container
        for container_node in containers_in_node:
            container_name = container_node.get("Names")
            print "str(container_name[0])={0}".format(str(container_name[0]))
            if "/" + container == str(container_name[0]):
                print "image = {0}".format(image)
                cli.stop(container)
                info["status"] = "stop"  # 设置状态信息为stop
                if remove:
                    cli.remove_container(container)
                    # 如果删除了container，则记录要删除的容器
                    # containers.pop(container)
                    remove_list.append(container)

    print "remove_list = {0}".format(remove_list)
    # 删除要删除的容器
    if remove:
        for l in remove_list:
            containers.pop(l)

    # 更新文件数据
    f = open(config_file,"w")
    yaml.dump(containers,f)
    f.close()

def __set_app_list(apps_name,yml_data):
    '''
    get the app list defined in the yaml file
    根据依赖关系确定container的启动顺序
    :param apps_name:
    :param yml_data:
    :return:
    '''
    global app_list
    for app_name in apps_name:
        container_detial = yml_data.get(app_name)
        if not container_detial.has_key("links"):
            if app_name not in app_list:
                app_list.append(app_name)
                return
        else:
            depend_service_name = container_detial.get("links")
            __set_app_list(depend_service_name,yml_data)
            if app_name not in app_list:
                # this code is important,put the current app_name to the list
                app_list.append(app_name)


if __name__ == "__main__":
    # stop(remove=True)
    compose(yml_file)
    # ps(all=False)