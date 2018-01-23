#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Models for user, blog, comment.
'''

__author__ = 'Michael Liao'

import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    """生成ID

    :return:ID
    """
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'     # 表名

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')      # ID主键
    email = StringField(ddl='varchar(50)')                                      # 邮件
    passwd = StringField(ddl='varchar(50)')                                     # 密码
    admin = BooleanField()                                                      # 是否是管理员
    name = StringField(ddl='varchar(50)')                                       # 姓名
    image = StringField(ddl='varchar(500)')                                     # 头像
    created_at = FloatField(default=time.time)                                  # 创建时间

class Blog(Model):
    __table__ = 'blogs'     # 表名

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')      # ID主键
    user_id = StringField(ddl='varchar(50)')                                    # 用户ID
    user_name = StringField(ddl='varchar(50)')                                  # 用户姓名
    user_image = StringField(ddl='varchar(500)')                                # 用户图像
    name = StringField(ddl='varchar(50)')                                       # 日志标题
    summary = StringField(ddl='varchar(200)')                                   # 简介
    content = TextField()                                                       # 内容
    created_at = FloatField(default=time.time)                                  # 创建时间

class Comment(Model):
    __table__ = 'comments'  # 表名

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')      # ID主键
    blog_id = StringField(ddl='varchar(50)')                                    # 日志ID
    user_id = StringField(ddl='varchar(50)')                                    # 用户ID
    user_name = StringField(ddl='varchar(50)')                                  # 用户名
    user_image = StringField(ddl='varchar(500)')                                # 用户图像
    content = TextField()                                                       # 内容
    created_at = FloatField(default=time.time)                                  # 创建时间