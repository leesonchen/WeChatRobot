#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from configuration import Config

import openai
import time
import logging
import re

class ChatGPT():

    def __init__(self, key: str, api: str, proxy: str, prompt: str) -> None:
        openai.api_key = key
        # 自己搭建或第三方代理的接口
        openai.api_base = api
        if proxy:
            openai.proxy = {"http": proxy, "https": proxy}
        self.conversation_list = {}
        self.system_content_msg = {"role": "system", "content": prompt}
        self.LOG = logging.getLogger("Chat")
        self.LOG.info("ChatGPT inited")
        self.answer_too_fast = False
        self.last_time = datetime.now()
        self.minimal_time = Config().CHATGPT.get("minimal")
        if self.minimal_time is None:
            self.minimal_time = 5
        elif self.minimal_time > 60:
            self.minimal_time = 60

    def get_answer(self, question: str, wxid: str):
        # wxid或者roomid,个人时为微信id，群消息时为群id
        self.updateMessage(wxid, question, "user")

        if self.answer_too_fast:
            if (datetime.now() - self.last_time).total_seconds() < 30:
                return "问得太频繁了，让我歇一歇~~"
            self.answer_too_fast = False

        # 如果内容包含#CMD#命令#param#，则执行命令
        if "#CMD#" in question:
            cmds = re.findall(r"#CMD#(.+)#(.*)#", question)
            if cmds:
                self.LOG.info(f"命令：{cmds[0][0]}, {cmds[0][1]}")

                # 处理"设置时延"命令，如果参数大于60则设为60
                if cmds[0][0] == "设置时延":
                    self.minimal_time = int(cmds[0][1])
                    if self.minimal_time > 60:
                        self.minimal_time = 60
                    return (f"已设置时延为{self.minimal_time}秒", True)
            return ("命令格式不正确", False)

        try:
            time_start = datetime.now()  # 记录开始时间

            self.LOG.info(self.conversation_list[wxid])

            ret = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=self.conversation_list[wxid],
                temperature=0.2
            )
            time_end = datetime.now()  # 记录结束时间
            sleepTime = self.minimal_time - (time_end - time_start).total_seconds()
            if sleepTime > 0:
                time.sleep(sleepTime)
                print(f"等待{round(sleepTime, 2)}s")

            # self.LOG.info(f"openai ret={ret}")

            rsp = ret["choices"][0]["message"]["content"]
            rsp = rsp[2:] if rsp.startswith("\n\n") else rsp
            rsp = rsp.replace("\n\n", "\n")
            self.updateMessage(wxid, rsp, "assistant")
            return (rsp, True)
        except openai.error.AuthenticationError as e3:
            rsp = "机器人临时检修，请稍后访问！"
            self.LOG.error("OpenAI API 认证失败，请检查 API 密钥是否正确：" + str(e0))
        except openai.error.APIConnectionError as e2:
            rsp = "机器人临时检修，请稍后访问！"
            self.LOG.error("无法连接到 OpenAI API，请检查网络连接：" + str(e0))
        except openai.error.APIError as e1:
            rsp = "机器人临时检修，请稍后访问！"
            self.LOG.error("OpenAI API 返回了错误：" + str(e0))
        except Exception as e0:
            # 如果错误包含“rate limit”字符串，说明超过了每分钟3次的限制
            if str(e0).find("rate limit") != -1:
                rsp = "问得太频繁了，让我歇一歇~~"
                self.answerTooFast = True
                self.last_time = datetime.now()
            else:
                rsp = "机器人临时检修，请稍后访问！"
                self.LOG.error("发生未知错误：" + str(e0))
        return (rsp, False)

    def updateMessage(self, wxid: str, question: str, role: str) -> None:
        now_time = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        time_mk = "当需要回答时间时请直接参考回复:"
        # 初始化聊天记录,组装系统信息
        if wxid not in self.conversation_list.keys():
            question_ = [
                self.system_content_msg,
                {"role": "system", "content": "" + time_mk + now_time}
            ]
            self.conversation_list[wxid] = question_

        # 当前问题
        content_question_ = {"role": role, "content": question}
        self.conversation_list[wxid].append(content_question_)

        for cont in self.conversation_list[wxid]:
            if cont["role"] != "system":
                continue
            if cont["content"].startswith(time_mk):
                cont["content"] = time_mk + now_time

        # 只存储10条记录，超过滚动清除
        i = len(self.conversation_list[wxid])
        if i > 10:
            print("滚动清除微信记录：" + wxid)
            # 删除多余的记录，倒着删，且跳过第一个的系统消息
            del self.conversation_list[wxid][1]


if __name__ == "__main__":
    config = Config().CHATGPT
    if not config:
        exit(0)

    key = config.get("key")
    api = config.get("api")
    proxy = config.get("proxy")
    prompt = config.get("prompt")

    chat = ChatGPT(key, api, proxy, prompt)

    while True:
        q = input(">>> ")
        try:
            time_start = datetime.now()  # 记录开始时间
            print(chat.get_answer(q, "wxid"))
            time_end = datetime.now()  # 记录结束时间

            print(f"{round((time_end - time_start).total_seconds(), 2)}s")  # 计算的时间差为程序的执行时间，单位为秒/s
        except Exception as e:
            print(e)
