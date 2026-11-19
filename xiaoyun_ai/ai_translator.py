# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Xiaoyun AI / 小云 AI
# Copyright (C) 2026 小鱼
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""本地翻译：HTTP completion 调用、输出清洗与术语保护。

通过常驻 llama-server 的 ``/completion`` 接口单条翻译（纯标准库 urllib），
固定停止序列防止补全模式续写模板；对返回内容剥离思考链与多余符号。受保护的
专有名词在 prompt 中强调保留，并对已知小模型错译做有限纠正。
"""
import json
import re
import urllib.error
import urllib.request

import ai_constants as C


class TranslateError(RuntimeError):
    """翻译请求失败或返回空结果。"""


# 已知小模型错译 → 正确写法（仅对明确无歧义的术语做纠正）。
_KNOWN_FIX = {
    "布料": "Fabric",
    "布料 API": "Fabric API",
    "硝酸钠": "Sodium",
}

# 译文校验：必须含 CJK；不得有三叠乱码（如“牙牙牙”）；不得残留连续英文单词链。
_CJK_RE = re.compile(r"[一-鿿]")
_TRIPLE_RE = re.compile(r"(.)\1\1")
_EN_CHAIN_RE = re.compile(r"[A-Za-z]{2,}(?:\s+[A-Za-z]{2,})+")


def is_valid_output(out: str) -> bool:
    """判断译文是否为可信中文：含 CJK、无三叠乱码、无成串未翻译英文。"""
    if not out:
        return False
    if not _CJK_RE.search(out):
        return False
    if _TRIPLE_RE.search(out):
        return False
    if _EN_CHAIN_RE.search(out):
        return False
    return True


def clean_output(content: str) -> str:
    """剥离思考链与多余符号，返回干净译文。"""
    s = content or ""
    if "</think>" in s:
        s = s.split("</think>", 1)[1]
    s = re.sub(r"<think>.*", "", s, flags=re.S)
    s = s.strip()
    # 去掉模型包裹译文的成对引号
    if len(s) >= 2 and s[0] in "“\"'" and s[-1] in "”\"'":
        s = s[1:-1].strip()
    return s


def apply_fixes(text: str) -> str:
    """对已知明确错译做替换；其余保持模型输出，避免激进改写。"""
    out = text
    for bad, good in _KNOWN_FIX.items():
        out = out.replace(bad, good)
    return out


class Translator:
    """对单个常驻 llama-server 发起翻译。"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _build_prompt(self, text: str) -> str:
        return (
            "You are a professional Minecraft game translator. Translate English "
            "Minecraft mod text into natural Simplified Chinese. Keep mod/API "
            "proper nouns in English when appropriate. Output only the translation.\n"
            + C.FEW_SHOT_EXAMPLES + f"EN: {text}\nZH:"
        )

    def _request(self, text: str, temp: float, timeout: float) -> str:
        body = json.dumps({
            "prompt": self._build_prompt(text),
            "n_predict": C.DEFAULT_N_PREDICT,
            "temperature": temp,
            "samplers": ["temp"],
            "stop": C.STOP_SEQUENCES,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/completion", data=body,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, OSError) as e:
            raise TranslateError(f"翻译请求失败：{e}") from e
        return apply_fixes(clean_output(data.get("content", "")))

    def translate_one(self, text: str, timeout: float = 60.0) -> str:
        """翻译单条；正常温度 + 低温各试一次，均未通过校验则抛错（上层保留英文）。"""
        last = ""
        for temp in (C.DEFAULT_TEMP, C.DEFAULT_RETRY_TEMP):
            last = self._request(text, temp, timeout)
            if is_valid_output(last):
                return last
        raise TranslateError(
            f"模型译文未通过校验，保留英文原文。原文：{text}；候选：{last}")

    def translate_mapping(self, entries: dict, on_progress=None,
                          should_cancel=None) -> tuple[dict, dict]:
        """批量翻译 key→英文；返回(成功 key→中文, 失败/取消 key→英文原文)。

        on_progress(done, total, key) 回调进度；should_cancel() 为 True 时停止，
        未处理的条目原样放入失败字典，保证不丢条目。
        """
        translated: dict = {}
        leftover: dict = {}
        total = len(entries)
        for i, (key, en) in enumerate(entries.items(), 1):
            if should_cancel is not None and should_cancel():
                leftover.update(dict(list(entries.items())[i - 1:]))
                break
            try:
                translated[key] = self.translate_one(en)
            except TranslateError:
                # 单条失败不中断整体，保留英文原文并在结果中体现。
                leftover[key] = en
            if on_progress is not None:
                on_progress(i, total, key)
        return translated, leftover
