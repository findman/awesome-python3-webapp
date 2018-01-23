#__author: Administrator
#date: 2018/1/17
#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import asyncio, logging

import aiomysql

def log(sql, args=()):
    """日志函数

    :param sql:所执行的SQL语句
    :param args:
    :return:
    """
    logging.info('SQL: %s' % sql)

async def create_pool(loop, **kw):
    """ 创建MySQL链接池

    :param loop: 事件循环实例
    :param kw:参数
    :return:
    """
    logging.info('create database connection pool...')
    global __pool   # 创建全局__pool对象

    __pool = await aiomysql.create_pool(        # 创建池 create_pool(minsize=1, maxsize=10, loop=None, **kwargs)
        host=kw.get('host', 'localhost'),       # Mysql服务器地址
        port=kw.get('port', 3306),              # 服务器端口
        user=kw['user'],                        # 用户名
        password=kw['password'],                # 密码
        db=kw['db'],                            # 所用数据库名
        charset=kw.get('charset', 'utf8'),      # 字符集
        autocommit=kw.get('autocommit', True),  # 是否自动提交
        maxsize=kw.get('maxsize', 10),          # 最大链接数
        minsize=kw.get('minsize', 1),           # 最小链接数
        loop=loop                               # 事件循环实例
    )

async def select(sql, args, size=None):
    """数据库select操作

    :param sql:查询语句
    :param args:查询值
    :param size:指定的返回数量
    :return:
    """
    log(sql, args)  # 日志中记录SQL语句和查询值
    global __pool   # 链接池
    async with __pool.get() as conn:    # 从链接池中获取链接对象
        async with conn.cursor(aiomysql.DictCursor) as cur:         # 获取游标
            await cur.execute(sql.replace('?', '%s'), args or ())   # 先将SQL语句中的'?'替换为查询值，如果值为None则设置为空元组，然后执行SQL语句
            if size:
                # 取出指定数量的记录
                rs = await  cur.fetchmany(size)
            else:
                # 取出所有记录
                rs = await cur.fetchall()

        logging.info('row returned: %s' % len(rs))  # 返回查询的记录条数
        return rs

async def execute(sql, args, autocommit=True):
    """数据库执行操作

    :param sql: SQL语句
    :param args: 参数
    :param autocommit: 是否自动提交
    :return: 返回执行SQL语句所影响的行数
    """

    log(sql)    # 日志SQL语句
    async with __pool.get() as conn:    # 从链接池中获取链接对象
        if not autocommit:              # 如果不自动提交
            await conn.begin()          # 开始链接
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur: # 获取游标
                await cur.execute(sql.replace('?','%s'), args)  # 先将SQL语句中的'?'替换为查询值，如果值为None则设置为空元组，然后执行SQL语句
                affected = cur.rowcount # 所影响的行数
            if not autocommit:          # 如果不自动提交
                await conn.commit()     # 提交链接
        except BaseException as e:      # 如果存在错误
            if not autocommit:          # 如果不自动提交
                await conn.rollback()   # 滚回
            raise                       # 抛出错误
        return affected                 # 返回所影响的函数

def create_args_string(num):
    """创建参数字符串

    :param num: 参数数量
    :return: 参数字符串
    """
    L = []                  # 定义空队列
    for n in range(num):    # 循环指定次数
        L.append('?')       # 添加'?'到队列
    return ', '.join(L)     # 使用', '分割队列组成字符串。例如：'?, ?, ...'

class Field(object):
    """字段基类

    """

    def __init__(self, name, column_type, primary_key, default):
        """初始化

        :param name:名称
        :param column_type:列类型
        :param primary_key:是否为主键
        :param default:默认值
        """
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        """打印字段信息

        :return:
        """
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


class StringField(Field):
    """字符串字段

    """

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        """初始化

        :param name:名称
        :param primary_key:是否为主键（默认为否）
        :param default:默认值
        :param ddl:数据定义语言，这里本质是对应列类型
        """
        super().__init__(name,ddl,primary_key,default)

class BooleanField(Field):
    """布尔字段

    """

    def __init__(self, name=None, default=False):
        """初始化

        :param name:名称
        :param default:默认值为否
        """
        super().__init__(name,'boolean',False,default)  # 列类型为boolean

class IntegerField(Field):
    """整形字段

    """

    def __init__(self, name=None, primary_key=False, default=0):
        """初始化

        :param name:名称
        :param primary_key:是否为主键
        :param default:默认值
        """
        super().__init__(name, 'bigint', primary_key, default)  # 列类型为'bigint'

class FloatField(Field):
    """单精字段

    """

    def __init__(self, name=None, primary_key=False, default=0.0):
        """初始化

        :param name:名称
        :param primary_key:是否为主键
        :param default:默认值为0.0
        """
        super().__init__(name, 'real', primary_key, default)    # 列类型为'real'

class TextField(Field):
    """文本字段

    """

    def __init__(self, name=None, default=None):
        """初始化

        :param name:名称
        :param default:默认值
        """
        super().__init__(name, 'text', False, default)  #列类型为'text'

class ModelMetaclass(type):
    """数据模型元类

    """

    def __new__(cls, name, bases, attrs):
        """__new__魔术方法创建这个类实例

        :param name:类名
        :param bases:基类
        :param attrs:属性
        :return:
        """
        if name == 'Model': # 如果类名为Model则直接返回原始的Model类不进行修改
            return type.__new__(cls, name, bases, attrs)

        tableName = attrs.get('__table__', None) or name                # 获取'__table__'属性如果为None则使用类名
        logging.info('found model:%s (table: %s)' % (name, tableName))  # 日志记录找到模型及对应的表
        mappings = dict()                                               # 创建映射空字典
        fields = []                                                     # 创建字段空列表
        primaryKey = None                                               # 定义主键为空
        for k,  v in attrs.items():                                     # 循环获取属性对象
            if isinstance(v, Field):                                    # 如果属性是字段类型
                logging.info(' found mapping:%s ==> %s' % (k, v))       # 日志记录找到映射关系
                mappings[k] = v                                         # 创建一条映射
                if v.primary_key:                                       # 如果是主键
                    if primaryKey:                                      # 如果之前已存在主键
                        raise Exception('Duplicate primary key for field: %s' % k)  # 多个主键报错
                    primaryKey = k                                      # 设置主键名称为当前字段名
                else:
                    fields.append(k)                                    # 否则放入字段列表中
        if not primaryKey:                                              # 如果不存在主键
            raise Exception('Primary key not found.')                   # 抛出找不到主键错误
        for k in mappings.keys():                                       # 移除原类中所定义的字段
            attrs.pop(k)
        escaped_fields = list(map(lambda f:'`%s`' % f, fields))         # 生成列字符串
        attrs['__mappings__'] = mappings                                # 保存属性和列的映射关系
        attrs['__table__'] = tableName                                  # 保存表名
        attrs['__primary_key__'] = primaryKey                           # 保存主键属性名
        attrs['__fields__'] = fields                                    # 保存除主键以外的属性名
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey,# 生成查询语句
                                                             ', '.join(escaped_fields),
                                                             tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName,   # 生成插入语句
                                                                           ', '.join(escaped_fields),
                                                                           primaryKey,
                                                                           create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName,           # 生产更新语句
                                                                   ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields))
                                                                   ,primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName,             # 生产删除语句
                                                                 primaryKey)
        return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass):
    """数据模型类

    继承字典类型
    """
    def __init__(self, **kw):
        """初始化

        :param kw:接收字典类型参数
        """
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        """获取属性

        :param key:属性对应的key
        :return: 属性值
        """
        try:
            return self[key]
        except KeyError:    # 如果无法找到则抛出错误
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        """设置属性值

        :param key:属性对应的key
        :param value: 属性设定的值
        :return:
        """
        self[key] = value

    def getValue(self, key):
        """获取属性

        :param key:属性的Key
        :return: 属性的值
        """
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        """获取属性的值或默认值

        :param key:属性的key
        :return:属性的值
        """
        value = getattr(self, key, None)    # 获取属性的值如果不存在则返回None
        if value is None:                   # 如果值为空
            field = self.__mappings__[key]  # 从映射关系获取对应字段
            if field.default is not None:   # 如果字段默认值不为空
                value = field.default() if callable(field.default) else field.default   # 如果字段默认值获取为可调用方法则调用方法否则调用属性
                logging.debug('using default value for %s: %s' % (key, str(value)))     # 将该属性设置为默认值的信息写入日志
                setattr(self, key, value)                                               # 设置该属性为默认值
        return value                                                                    # 返回属性值

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        """查找所有记录
        SQL SELECT 语句参考
        [http://blog.csdn.net/litong09282039/article/details/46330069]

        :param where:SQL where部分
        :param args:值部分
        :param kw:orderBy/limit/
        :return:查询结果通过本类类型队列的方式返回
        """
        sql = [cls.__select__]              # 获取查询语句,并存入队列
        if where:                           # 如果存在where部分
            sql.append('where')             # 先把where加字段加进去
            sql.append(where)               # 这里的字符串对应的是字段
        if args is None:                    # 参数值如果为空
            args = []                       # 设置参数值为空队列
        orderBy = kw.get('orderBy', None)   # 获取orderBy如果不存在设置为None
        if orderBy:                         # 如果存在orderBy
            sql.append('order by')          # 加入order by字符串
            sql.append(orderBy)             # 这里也是字段字符串，用于排序
        limit = kw.get('limit', None)       # 获取limit如果不存在设置为None
        if limit is not None:               # 如果在字典中存在limit
            sql.append('limit')             # 加入limit字符串
            if isinstance(limit, int):      # 如果该元素为整形
                sql.append('?')             # 在SQL语句后添加一个'?'
                args.append(limit)          # 将获取的limit值加入参数队列
            elif isinstance(limit, tuple) and len(limit) == 2:  # 如果limit是元组类型并且长度为2
                sql.append('?, ?')          # 在SQL语句后添加'?, ?'
                args.extend(limit)          # 在参数队列中插入一个limit元组对象
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))    # 否则报limit值错误
        rs = await select(' '.join(sql), args)  # 传入参数并执行select查询
        return [cls(**r) for r in rs]       # 返回结果并将查询结果存入当前类类型的队列

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        """查找记录集数量

        :param selectField:查找字段
        :param where:where语句
        :param args:值
        :return:记录数量
        """
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]  # 生成查询语句
        if where:
            sql.append('where')     # 如果存在where部分
            sql.append(where)       # 这里的字符串对应的是字段
        rs = await select(' '.join(sql), args, 1)   # 查询
        if len(rs) == 0:            # 如果记录数量为0返回None
            return None
        return rs[0]['_num_']       # 返回记录数量？不太明白为什么要用这样方式

    @classmethod
    async def find(cls, pk):
        """查找

        :param pk:查找信息(字典)
        :return:查找记录
        """
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)   # 生成查询语句
        if len(rs) == 0:        # 如果返回记录条数为0则返回None
            return None
        return cls(**rs[0])     # 返回类类型数据集

    async def save(self):
        """保存

        :return:
        """
        args = list(map(self.getValueOrDefault, self.__fields__))   # 生成字段队列
        args.append(self.getValueOrDefault(self.__primary_key__))   # 加上主键
        rows = await execute(self.__insert__, args)                 # 插入一条记录
        if rows != 1:                                               # 如果返回值不为1则报错
            logging.warning('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        """更新记录

        :return:
        """
        args = list(map(self.getValue, self.__fields__))    # 生成字段队列
        args.append(self.getValue(self.__primary_key__))    # 加上主键
        rows = await execute(self.__update__, args)         # 执行更新操作
        if rows != 1:                                       # 如果返回值不为1则报错
            logging.warning('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        """删除该记录

        :return:
        """
        args = [self.getValue(self.__primary_key__)]    # 获取主键
        rows = await execute(self.__delete__, args)     # 执行删除操作
        if rows != 1:                                   # 如果返回值不为1则报错
            logging.warning('failed to remove by primary key: affected rows: %s' % rows)