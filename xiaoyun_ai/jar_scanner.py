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

"""mod jar 语言文件扫描（纯标准库 zipfile/json）。

枚举目录下所有 jar，定位 ``assets/<namespace>/lang/en_us.json`` 与同目录
``zh_cn.json``；按条目级对比：已有中文的 key 直接保留、不翻译，只收集缺失中文
的英文条目。整个文件都已有中文时该文件不产生待翻译任务。
"""
from dataclasses import dataclass, field
import json
import os
import zipfile

import ai_constants as C


@dataclass
class LangTask:
    """单个 jar 内某个 namespace 的语言文件翻译任务。"""
    jar_path: str
    namespace: str
    en_member: str
    zh_member: str
    # 待翻译：本地化 key -> 英文原文（仅中文缺失的条目）
    to_translate: dict = field(default_factory=dict)
    # 已有中文：本地化 key -> 中文（保留并并入最终 zh_cn）
    existing_zh: dict = field(default_factory=dict)

    @property
    def total_count(self) -> int:
        return len(self.to_translate) + len(self.existing_zh)


def _is_lang_member(name: str) -> tuple[bool, str, str]:
    """判断 jar 内条目是否为语言文件；返回(是否, namespace, 文件名)。"""
    parts = name.replace("\\", "/").split("/")
    if len(parts) < 4 or parts[0] != "assets" or parts[-2] != "lang":
        return False, "", ""
    fname = parts[-1].lower()
    if fname not in (C.LANG_EN, C.LANG_ZH):
        return False, "", ""
    return True, parts[1], fname


def _read_json_member(zf: zipfile.ZipFile, member: str) -> dict | None:
    """读取并解析 jar 内 JSON；失败返回 None。"""
    try:
        with zf.open(member) as f:
            data = json.loads(f.read().decode("utf-8-sig"))
        return data if isinstance(data, dict) else None
    except (KeyError, ValueError, OSError):
        return None


def scan_jar(jar_path: str) -> list[LangTask]:
    """扫描单个 jar，返回其中所有待翻译的语言任务（可能含多个 namespace）。"""
    tasks: list[LangTask] = []
    try:
        zf = zipfile.ZipFile(jar_path)
    except (zipfile.BadZipFile, OSError):
        return tasks
    # 按 (namespace, 目录) 归集 en/zh 成员路径。
    en_members: dict[str, str] = {}
    zh_members: dict[str, str] = {}
    with zf:
        for info in zf.infolist():
            ok, ns, fname = _is_lang_member(info.filename)
            if not ok:
                continue
            if fname == C.LANG_EN:
                en_members.setdefault(ns, info.filename)
            else:
                zh_members.setdefault(ns, info.filename)
        for ns, en_member in en_members.items():
            en = _read_json_member(zf, en_member)
            if not en:
                continue
            zh_member = zh_members.get(ns, "")
            zh = _read_json_member(zf, zh_member) if zh_member else {}
            zh = zh or {}
            existing = {k: v for k, v in zh.items() if k in en}
            missing = {k: v for k, v in en.items()
                       if k not in existing and isinstance(v, str) and v.strip()}
            if not missing:
                # 英文条目全部已有中文，整文件跳过。
                continue
            zh_target = zh_member or en_member.replace(C.LANG_EN, C.LANG_ZH)
            tasks.append(LangTask(
                jar_path=jar_path, namespace=ns,
                en_member=en_member, zh_member=zh_target,
                to_translate=missing, existing_zh=existing,
            ))
    return tasks


def scan_dir(root: str, progress=None, should_cancel=None) -> list[LangTask]:
    """递归扫描目录下所有 jar；progress(done, total, path) 用于进度回调。

    should_cancel() 返回 True 时提前结束并返回已扫描到的任务。
    """
    jars = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith(".jar"):
                jars.append(os.path.join(dirpath, fn))
    total = len(jars)
    result: list[LangTask] = []
    for i, jar in enumerate(jars, 1):
        if should_cancel is not None and should_cancel():
            break
        result.extend(scan_jar(jar))
        if progress is not None:
            progress(i, total, jar)
    return result


def count_pending(tasks: list[LangTask]) -> int:
    """统计待翻译条目总数。"""
    return sum(len(t.to_translate) for t in tasks)
