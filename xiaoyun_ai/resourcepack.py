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

"""汉化资源包生成：写 pack.mcmeta 与各 namespace 的 zh_cn.json，并可打包 zip。

资源包目录结构遵循 Minecraft 约定（``assets/<namespace>/lang/zh_cn.json``），
游戏内「资源包」启用后即可让对应 mod 的物品/菜单显示简体中文。每个语言文件由
「已有中文 + 本次 AI 译文」合并而成，不覆盖 mod 原有中文。
"""
import json
import os
import shutil
import zipfile

import ai_constants as C
from jar_scanner import LangTask


def _pack_mcmeta() -> dict:
    desc = f"{C.AI_DISPLAY_NAME} 汉化资源包（{C.TRANSLATION_DISCLAIMER}）"
    return {
        "pack": {
            "pack_format": C.DEFAULT_PACK_FORMAT,
            "supported_formats": {
                "min_inclusive": C.PACK_FORMAT_MIN,
                "max_inclusive": C.PACK_FORMAT_MAX,
            },
            "description": desc,
        }
    }


def build_pack(output_dir: str,
               items: list[tuple[LangTask, dict]]) -> str:
    """根据(任务, 新译文)列表生成资源包目录，返回该目录路径。

    同一 namespace 多个 jar 的条目合并写入同一个 zh_cn.json。
    """
    os.makedirs(output_dir, exist_ok=True)
    # namespace -> 完整中文映射（已有中文 + 新译文）
    merged: dict[str, dict] = {}
    for task, new_zh in items:
        bucket = merged.setdefault(task.namespace, {})
        bucket.update(task.existing_zh)
        bucket.update(new_zh)
    for ns, mapping in merged.items():
        lang_dir = os.path.join(output_dir, "assets", ns, "lang")
        os.makedirs(lang_dir, exist_ok=True)
        with open(os.path.join(lang_dir, C.LANG_ZH), "w",
                  encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2,
                      sort_keys=True)
    with open(os.path.join(output_dir, "pack.mcmeta"), "w",
              encoding="utf-8") as f:
        json.dump(_pack_mcmeta(), f, ensure_ascii=False, indent=2)
    return output_dir


def zip_pack(pack_dir: str, zip_path: str) -> str:
    """把资源包目录打包为 zip（游戏可直接作为资源包导入），返回 zip 路径。"""
    if os.path.exists(zip_path):
        os.remove(zip_path)
    base = os.path.dirname(os.path.abspath(pack_dir))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _dirs, files in os.walk(pack_dir):
            for fn in files:
                full = os.path.join(dirpath, fn)
                arc = os.path.relpath(full, base)
                zf.write(full, arc)
    return zip_path
