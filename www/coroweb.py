#__author: Administrator
#date: 2018/1/23
#!/usr/bin/env python3
#-*- coding:utf-8 -*-

__author__ = 'Michael Liao'

import asyncio, os, inspect, logging, functools

from urllib import parse

from aiohttp import web

from apis import APIError

def get(path):
    """装饰Get方法

    :param path:路径
    :return:
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args,**kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

def post(path):
    """装饰Post方法

    :param path: 路径
    :return:
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator


def get_required_kw_args(fn):
    """获取必要参数（及默认值为空的参数）

    :param fn:函数
    :return:返回关键词元组
    """
    args = []       # 定义空队列
    params = inspect.signature(fn).parameters   # 获取该函数的所有参数
    for name, param in params.items():          # 获取参数
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:   # 如果参数类型为关键字参数，并且默认值为空
            args.append(name)                   # 将参数名放入队列
    return tuple(args)                          # 返回参数名元组

def get_name_kw_args(fn):
    """获取所所有关键字参数

    :param fn:
    :return:
    """
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_name_kw_args(fn):
    """是否存在关键字参数

    :param fn:
    :return:
    """
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_args(fn):
    """是否存在字典类型参数（**kw）

    :param fn:
    :return:
    """
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    """是否存在request参数

    :param fn:
    :return:
    """
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

class RequestHandler(object):
    """请求捕获

    """

    def __init__(self, app, fn):
        """初始化

        :param app:web Application
        :param fn:函数
        """
        self._app = app                                     # APP
        self._func = fn                                     # 处理函数
        self._has_request_arg = has_request_arg(fn)         # 是否处理request参数
        self._has_var_kw_arg = has_var_kw_args(fn)          # 是否有字典类型参数
        self._has_named_kw_args = has_name_kw_args(fn)      # 是否有名称参数
        self._named_kw_args = get_name_kw_args(fn)          # 获取名称参数
        self._required_kw_args = get_required_kw_args(fn)   # 获取必要参数

    async def __call__(self, request):
        """调用参数

        :param request:客户端所提交的数据
        :return:
        """
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:   # 如果处理函数有参数
            if request.method == 'POST':                                        # 如果提交类型为POST
                if not request.content_type:                                    # 如果内容类型不存在返回类型丢失错误
                    return web.HTTPBadRequest('Missing Content-Type')
                ct = request.content_type.lower()                               # 将返回类型字符串处理为小写
                if ct.startswith('application/json'):                           # 如果开头为json类型
                    params = await request.json()                               # 获取json数据
                    if not isinstance(params, dict):                            # 如果获取的类型不为字典类型，则返回错误，提示json的体应为一个对象
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params                                                 # 将数据存入kw
                # http://blog.csdn.net/xiaoliuliu2050/article/details/52875881
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()                               # 获取所提交的数据
                    kw = dict(**params)                                         # 转换为dict并存入kw
                else:                                                           # 如果都不是就报错
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':                                         # 如果提交类型为GET
                qs = request.query_string                                       # 获取地址栏中所提交的查询字符串
                if qs:                                                          # 如果存在这将这些查询依次存入字典
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:                                                          # 如果处理函数没有参数
            kw = dict(**request.match_info)                                     # match_info内部暂时不清楚
        else:
            if not self._has_var_kw_arg and self._named_kw_args:                # 不存在字典类型参数并且存在关键字参数
                copy = dict()                                                   # 创建一个空字典
                for name in self._named_kw_args:                                # 获取关键字
                    if name in kw:                                              # 如果关键字在参数中
                        copy[name] = kw[name]                                   # 将数据存入字典
                kw = copy
            for k, v in request.match_info.items():                             # 如果
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request

        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutine(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__metod__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)


