#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
author : North Star
date   : 2020年07月01日20:26:00
role   : 链接及分组管理

status = '0'    正常
status = '10'   逻辑删除
status = '20'   禁用
"""

import json
import shortuuid
import base64
from websdk.jwt_token import gen_md5
from websdk.tools import check_password
from libs.base_handler import BaseHandler
from websdk.db_context import DBContext
from models.admin import Links, LinksGroup, model_to_dict
from websdk.consts import const
from websdk.cache_context import cache_conn


class LinkHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=30, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        link_list = []
        with DBContext('r') as session:
            if key and value:
                if key == "group_name":
                    gidlist = session.query(LinksGroup.id).filter(getattr(LinksGroup, key).ilike("%{}%".format(value))).subquery()
                    count = session.query(Links).filter(Links.links_group.in_(gidlist)).count()
                    link_info = session.query(Links).filter(Links.links_group.in_(gidlist)).order_by(Links.links_group).offset(limit_start).limit(int(limit))
                else:
                    count = session.query(Links).filter(getattr(Links, key).ilike("%{}%".format(value))).count()
                    link_info = session.query(Links).filter(getattr(Links, key).ilike("%{}%".format(value))).order_by(Links.links_group).offset(limit_start).limit(int(limit))
            else:
                count = session.query(Links).count()
                link_info = session.query(Links).order_by(Links.links_group).offset(
                    limit_start).limit(int(limit))

            all_link = session.query(Links).order_by(Links.links_group).all()
            if int(limit) > 200:
                link_info = all_link

        for msg in link_info:
            data_dict = model_to_dict(msg)
            link_list.append(data_dict)

        redis_conn = cache_conn()
        redis_conn.delete('LINKS_INFO') ### 清空集合数据
        with redis_conn.pipeline(transaction=False) as p:
            for msg in all_link:
                data_dict = model_to_dict(msg)
                #p.hmset(nickname_key, {"tel": data_dict["tel"], "email": data_dict["email"]})
                p.sadd('LINKS_INFO', json.dumps(data_dict))
            p.execute()
        self.write(dict(code=0, msg='获取链接成功', count=count, data=link_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        linkname = data.get('links_name', None)
        linkurl = data.get('links_url', None)
        linkgroup = data.get('links_group', None)
        linkremarks = data.get('links_remarks', None)
        linkuser = data.get('links_user', None)
        linkpwd = data.get('links_password', None)
        if not linkname or not linkurl or not linkgroup:
            return self.write(dict(code=-1, msg='参数不能为空'))

        with DBContext('r') as session:
            link_info1 = session.query(Links).filter(Links.links_url == linkurl).first()
        if link_info1:
            return self.write(dict(code=-2, msg='链接已存在'))

        with DBContext('w', None, True) as session:
            session.add(Links(links_name=linkname, links_url=linkurl, links_group=linkgroup, links_remarks=linkremarks, links_user=linkuser, links_password=linkpwd))

        self.write(dict(code=0, msg='添加成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        link_id = data.get('link_id', None)
        id_list = data.get('id_list', None)

        if link_id:
            with DBContext('w', None, True) as session:
                session.query(Links).filter(Links.id == link_id).delete(synchronize_session=False)
            return self.write(dict(code=0, msg='删除成功'))
        if id_list:
            with DBContext('w', None, True) as se:
                se.query(Links).filter(Links.id.in_(id_list)).delete(synchronize_session=False)
            return self.write(dict(code=0, msg='批量删除成功'))

        self.write(dict(code=-1, msg='参数不能为空'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        linkname = data.get('links_name', None)
        linkurl = data.get('links_url', None)
        linkgroup = data.get('links_group', None)
        linkremarks = data.get('links_remarks', None)
        linkuser = data.get('links_user', None)
        linkpwd = data.get('links_password', None)
        link_id = data.get('id', None)
        if not linkname or not linkurl or not linkgroup or not link_id:
            return self.write(dict(code=-1, msg='参数不能为空'))

        udict = {
            "links_name": linkname,
            "links_url": linkurl,
            "links_group": linkgroup,
            "links_remarks": linkremarks,
            "links_user": linkuser,
            "links_password": linkpwd
            }

        try:
            with DBContext('w', None, True) as session:
                session.query(Links).filter(Links.id == link_id).update(udict)
        except Exception as e:
            return self.write(dict(code=-2, msg='修改失败，请检查数据是否合法或者重复'))

        self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用    占位"""
        pass


class LinkGroupHander(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        group_list = []

        if key and value:
            with DBContext('r') as session:
                count = session.query(LinksGroup).filter(getattr(LinksGroup, key).ilike("%{}%".format(value))).count()
                group_info = session.query(LinksGroup).filter(getattr(LinksGroup, key).ilike("%{}%".format(value))).all()
        else:
            with DBContext('r') as session:
                count = session.query(LinksGroup).count()
                group_info = session.query(LinksGroup).all()

        for msg in group_info:
            data_dict = model_to_dict(msg)
            group_list.append(data_dict)

        return self.write(dict(code=0, msg='获取链接分组成功', count=count, data=group_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        groupname = data.get("group_name", None)
        groupremarks = data.get("group_remarks", None)

        if not groupname:
            return self.write(dict(code=-1, msg="参数不能为空"))
        
        with DBContext('r') as session:
            group_info = session.query(LinksGroup).filter(LinksGroup.group_name == groupname).first()

        if group_info:
            return self.write(dict(code=-2, msg="分组已存在"))

        with DBContext('w', None, True) as session:
            session.add(LinksGroup(group_name=groupname, group_remarks=groupremarks))
        self.write(dict(code=0, msg="添加成功"))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        groupid = data.get("group_id", None)
        idlist = data.get("id_list", None)

        if groupid:
            with DBContext('r') as session:
                link_info = session.query(Links).filter(Links.links_group == groupid).first()

            if link_info:
                return self.write(dict(code=-2, msg="当前组存在链接,不可删除."))

            with DBContext('w', None, True) as session:
                session.query(LinksGroup).filter(LinksGroup.id == groupid).delete(synchronize_session=False)
                
            return self.write(dict(code=0, msg="删除成功"))
        if idlist:
            with DBContext("r") as se:
                link_info = se.query(Links).filter(Links.links_group.in_(idlist)).first()
            
            if link_info:
                return self.write(dict(code=-2, msg="您选择的分组存在链接,不可删除."))

            with DBContext('w', None, True) as se:
                se.query(LinksGroup).filter(LinksGroup.id.in_(idlist)).delete(synchronize_session=False)
            
            return self.write(dict(code=0, msg="删除成功"))

        self.write(dict(code=-1, msg="请检查参数"))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        groupname = data.get("group_name", None)
        groupremarks = data.get("group_remarks", None)
        groupid = data.get("id", None)
        
        if not groupname or not groupremarks or not groupid:
            return self.write(dict(code=-1, msg="参数不能为空"))

        udict = {
            "group_name":groupname,
            "group_remarks":groupremarks
            }

        try:
            with DBContext('w', None, True) as session:
                session.query(LinksGroup).filter(LinksGroup.id == groupid).update(udict)
        except Exception as e:
            return self.write(dict(code=-2, msg='修改失败，请检查数据是否合法或者重复'))

        self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        """禁用、启用    占位"""
        pass

links_urls = [
    (r"/v2/links/", LinkHandler),
    (r"/v2/links/groups/", LinkGroupHander),
]

if __name__ == "__main__":
    pass
