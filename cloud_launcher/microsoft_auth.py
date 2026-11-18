# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Cloudy Launcher (CLY) / 云朵启动器
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

"""微软（正版）账号认证：v1 Live-Connect 设备码 + Xbox Live → XSTS → Minecraft 链路。

流程（与 wiki.vg《Microsoft Authentication Scheme》及 mcapi-auth ``login_device_code_v1``
一致；端点 / 客户端 ID / 超时全部外置到 ``constants``，HTTP 封装统一收敛，错误信息统一
翻译为中文；不照搬旧版多账号配置与 Tkinter 界面代码）：

1. ``POST`` v1 Live-Connect ``oauth20_connect.srf``：申请设备码，返回 ``device_code`` /
   ``user_code``（8 位）/ ``verification_uri`` / 轮询间隔；v1 申请体额外带
   ``response_type=device_code``；
2. 浏览器打开 ``verification_uri``、用户输入 ``user_code`` 完成授权；本模块在后台
   ``poll_token`` 循环轮询 ``oauth20_token.srf``，v1 的 ``grant_type`` 为短名
   ``device_code``；授权未完成时按协议继续等待，收到 ``slow_down`` 自动拉长间隔，到点
   超时、可被外部 ``threading.Event`` 取消；
3. 拿到微软 ``access_token``（v1 为不透明 RPS ticket，换取 Xbox Live 时不加 ``d=``
   前缀）后依次换取 Xbox Live 令牌 → XSTS 令牌 → Minecraft 服务令牌，再 ``GET`` 玩家
   档案（昵称、无横杠 UUID、正版皮肤 URL 与模型类型）；
4. ``refresh`` 用离线刷新令牌静默续期微软令牌；``refresh_profile`` 在其之上重走
   Xbox → XSTS → Minecraft → 档案，供程序启动时用本地保存的刷新令牌静默恢复正版会话；
   短期访问令牌不落盘，仅 ``refresh_token`` 与公开身份由 ``AccountStore`` 持久化。

整条链路只使用 Python 标准库（``urllib`` / ``json`` / ``time`` / ``hashlib`` /
``uuid`` / ``threading``），不引入任何第三方 HTTP 库。
"""
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from . import constants as C


class AuthError(Exception):
    """认证链路可向用户展示的中文错误。"""


# Xbox 服务错误码（XErr）→ 面向中文用户的可读说明。
_XSTS_MESSAGES = {
    "2148916233": "该微软账号尚未开通 Xbox Live 服务。请先到 xbox.com 用此账号登录一次完成注册，再回来登录。",
    "2148916235": "Xbox Live 需要成年账号。请使用已开通的成年账号，或在 xbox.com 完成账号升级。",
    "2148916236": "该账号需要完成成年验证（地区限制），请先在 Xbox 账号设置中完成验证。",
    "2148916237": "该账号需要完成成年验证（韩国地区要求），请先在 Xbox 账号设置中完成验证。",
    "2148916238": "该账号是未成年人，需要家长在 account.microsoft.com/family 中同意后才能使用。",
}


def offline_uuid(name: str) -> str:
    """离线账号 UUID：MD5("OfflinePlayer:" + name)，版本位 / 变体位按 v3 修正。

    当前个人页仅展示正版账号 UUID；本函数保留备用，与官方离线账号规则保持一致。
    """
    digest = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(digest)))


class MicrosoftAuth:
    """设备码流程的微软正版登录器（纯标准库、无客户端密钥的公共桌面客户端）。"""

    def __init__(self, client_id: str | None = None,
                 timeout: float | None = None) -> None:
        client_id = (client_id or "").strip() or C.MS_PUBLIC_CLIENT_ID
        self.client_id = client_id
        # 单次 HTTP 超时可按调用场景区分：设备码交互登录用默认 60s，启动静默恢复用更短的
        # RESTORE_HTTP_TIMEOUT，保证关闭窗口时等待线程收尾的时间有确定上界、不会带着运行中
        # 的 QThread 被析构而触发 0xC0000409。
        self._http_timeout = timeout if timeout is not None else C.AUTH_HTTP_TIMEOUT

    # ---- 1. 申请设备码 ----
    def request_device_code(self) -> dict:
        """向 v1 Live-Connect 端点申请设备码与授权网址，返回 device_code / user_code / verification_uri / interval。"""
        form = {
            "client_id": self.client_id,
            "scope": C.MS_OAUTH_SCOPE,
            # v1 设备码申请体要求显式声明 response_type=device_code（v2 不需要）
            "response_type": "device_code",
        }
        resp = self._request(C.MS_DEVICE_CODE_URL, form=form)
        for key in ("device_code", "user_code", "verification_uri"):
            if key not in resp:
                raise AuthError("设备码响应缺少必要字段，登录未能发起。")
        resp.setdefault("interval", C.AUTH_POLL_INTERVAL)
        return resp

    # ---- 2. 轮询授权换微软令牌 ----
    def poll_token(self, device_code: str, cancel=None) -> dict:
        """轮询微软令牌端点直到授权完成、超时或被取消。

        ``cancel`` 为 ``threading.Event``：外部置位即中断并抛「已取消登录」。
        返回 ``access_token / refresh_token / expires_in``。
        """
        interval = C.AUTH_POLL_INTERVAL
        deadline = time.time() + C.AUTH_POLL_TIMEOUT
        while True:
            if cancel is not None and cancel.is_set():
                raise AuthError("已取消登录")
            if time.time() > deadline:
                raise AuthError("登录等待超时，请在 10 分钟内完成浏览器授权后重试。")
            try:
                resp = self._request(
                    C.MS_TOKEN_URL,
                    form={
                        # v1 Live-Connect 用短名 grant_type=device_code；v2 才用 URN
                        "grant_type": "device_code",
                        "client_id": self.client_id,
                        "device_code": device_code,
                    },
                )
            except AuthError as exc:
                text = str(exc)
                # 用户尚未在浏览器完成授权：继续等待（v1 / v2 两种错误文案都覆盖）
                if ("authorization_pending" in text or "AADSTS70016" in text
                        or "not yet been authorized" in text):
                    time.sleep(interval)
                    continue
                # 轮询过快被限流：按协议把间隔拉长后继续等待
                if "slow_down" in text:
                    interval = max(interval, 5)
                    time.sleep(interval)
                    continue
                # 设备码已过期（v1 / v2 文案）：不再空转到总超时，直接提示重新发起
                if "expired_token" in text or "expired_grant" in text:
                    raise AuthError("设备码已过期，请重新点击「正版」发起登录。")
                # 用户在浏览器取消 / 拒绝授权：直接终止轮询并给出明确中文提示
                if ("authorization_declined" in text or "access_denied" in text
                        or "declined" in text.lower()):
                    raise AuthError("你已在浏览器中取消或拒绝授权，本次登录未完成。")
                raise
            for key in ("access_token", "refresh_token", "expires_in"):
                if key not in resp:
                    raise AuthError("令牌响应缺少必要字段，登录失败。")
            return resp

    # ---- 3. 换 Xbox / XSTS / Minecraft 令牌并拉取档案 ----
    def fetch_profile(self, msa_access_token: str, refresh_token: str = "") -> dict:
        """从微软访问令牌走完 Xbox Live → XSTS → Minecraft 链路，返回玩家档案字典。"""
        # Xbox Live 认证：必须带 x-xbl-contract-version 头与 JSON 请求体。
        # v1 RPS ticket 是不透明令牌，直接原样放入；v2 JWT 才需要 "d=" 前缀（由常量开关决定）。
        rps_ticket = ("d=" + msa_access_token) if C.MS_XBL_USE_D_PREFIX else msa_access_token
        xbl = self._request_json(
            C.MS_XBL_AUTH_URL,
            body={
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": rps_ticket,
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT",
            },
            headers={"x-xbl-contract-version": "1"},
        )
        xbl_token = xbl.get("Token")
        if not xbl_token:
            raise AuthError("Xbox Live 认证失败：未返回令牌。")
        uhs = self._display_uhs(xbl)

        # XSTS 授权：失败多为 Xbox 账号未开通 / 隐私或成年限制，按错误码翻译中文
        try:
            xsts = self._request_json(
                C.MS_XSTS_URL,
                body={
                    "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
                    "RelyingParty": "rp://api.minecraftservices.com/",
                    "TokenType": "JWT",
                },
                headers={"x-xbl-contract-version": "1"},
            )
        except AuthError as exc:
            raise AuthError(self._translate_xsts(str(exc)))
        xsts_token = xsts.get("Token")
        if not xsts_token:
            raise AuthError(self._translate_xsts("XSTS 未返回令牌"))
        uhs2 = self._display_uhs(xsts)
        if uhs and uhs2 and uhs != uhs2:
            raise AuthError("Xbox 身份标识不一致，授权失败。")

        # Minecraft 服务登录
        try:
            mc = self._request_json(
                C.MS_MC_LOGIN_URL,
                body={"identityToken": f"XBL3.0 x={uhs2};{xsts_token}"},
            )
        except AuthError as exc:
            if "forbidden" in str(exc).lower() or "403" in str(exc):
                raise AuthError("该微软账号没有购买 Minecraft（Java 版）。请使用已购买正版游戏的账号登录。")
            raise
        mc_access_token = mc.get("access_token")
        if not mc_access_token:
            raise AuthError("Minecraft 服务登录失败：未返回访问令牌。")

        # 玩家档案：404 / NOT_FOUND 表示该账号没有 Minecraft 档案（未购买 Java 版）
        try:
            profile = self._request(
                C.MS_MC_PROFILE_URL, method="GET", bearer=mc_access_token
            )
        except AuthError:
            raise AuthError("该微软账号没有 Minecraft 档案（未购买 Java 版正版游戏）。")

        if "id" not in profile or "name" not in profile:
            raise AuthError("玩家档案信息不完整，登录失败。")

        skin_url, slim = self._extract_skin(profile)
        expires_in = int(mc.get("expires_in", 86400))
        return {
            "name": profile["name"],
            "uuid": profile["id"],  # 无横杠 UUID
            "mc_access_token": mc_access_token,
            "expires_at": time.time() + expires_in - C.MC_TOKEN_EXPIRE_MARGIN,
            "refresh_token": refresh_token or "",
            "skin_url": skin_url,
            "slim": slim,
        }

    # ---- 4. 静默续期：刷新令牌换新微软令牌，再重走 Xbox / MC 链路恢复档案 ----
    def refresh(self, refresh_token: str) -> dict | None:
        """用离线刷新令牌换取新的微软访问令牌；失败返回 None，由调用方决定回退。"""
        if not refresh_token:
            return None
        try:
            return self._request(
                C.MS_TOKEN_URL,
                form={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "refresh_token": refresh_token,
                    "scope": C.MS_OAUTH_SCOPE,
                },
            )
        except AuthError:
            return None

    def refresh_profile(self, refresh_token: str) -> dict | None:
        """用本地保存的刷新令牌静默恢复正版会话，返回完整玩家档案；失败返回 None。

        流程：``refresh_token`` 换新微软访问令牌 → ``fetch_profile`` 重走 Xbox Live →
        XSTS → Minecraft 登录 → 玩家档案；返回档案内含轮换后的新 ``refresh_token``，
        由调用方回写本地账号文件。令牌过期、被吊销、未购买游戏、网络失败等任何一步
        出错都返回 ``None``，由调用方清除本地凭据并回退离线，不在此弹窗报错。
        """
        if not refresh_token:
            return None
        try:
            token = self.refresh(refresh_token)
            if not token:
                return None
            msa_access = token.get("access_token")
            if not msa_access:
                return None
            # 刷新响应可能轮换出新的 refresh_token；沿用新令牌，缺失时回退旧令牌。
            new_refresh = token.get("refresh_token") or refresh_token
            return self.fetch_profile(msa_access, new_refresh)
        except AuthError:
            return None
        except Exception:
            return None

    # ---- 内部工具 ----
    @staticmethod
    def _display_uhs(payload: dict) -> str:
        claims = payload.get("DisplayClaims", {}) or {}
        xui = claims.get("xui") or [{}]
        return str(xui[0].get("uhs", ""))

    @staticmethod
    def _extract_skin(profile: dict) -> tuple[str | None, bool]:
        """从档案 skins 列表取主皮肤 URL 与模型类型（SLIM = 细臂，CLASSIC = 标准臂）。"""
        skins = profile.get("skins") or []
        if not skins:
            return None, False
        main = skins[0]
        url = main.get("url") or None
        slim = str(main.get("variant", "")).upper() == "SLIM"
        return url, slim

    @staticmethod
    def _translate_xsts(text: str) -> str:
        for code, message in _XSTS_MESSAGES.items():
            if code in text:
                return message
        return "Xbox 授权失败：" + text

    def _request(
        self,
        url: str,
        *,
        form: dict | None = None,
        method: str = "POST",
        bearer: str | None = None,
        headers: dict | None = None,
    ) -> dict:
        """表单编码请求（微软 AAD 端点要求 application/x-www-form-urlencoded）。"""
        return self._send(url, method=method, form=form, bearer=bearer, headers=headers)

    def _request_json(
        self,
        url: str,
        *,
        body: dict,
        headers: dict | None = None,
        bearer: str | None = None,
        method: str = "POST",
    ) -> dict:
        """JSON 请求体（Xbox / XSTS / Minecraft 端点要求 application/json）。"""
        return self._send(url, method=method, json_body=body, bearer=bearer, headers=headers)

    def _send(
        self,
        url: str,
        *,
        method: str = "POST",
        form: dict | None = None,
        json_body: dict | None = None,
        bearer: str | None = None,
        headers: dict | None = None,
    ) -> dict:
        user_agent = f"{C.APP_UA_NAME}/{C.APP_VERSION} (Windows; urllib)"
        request_headers = {"Accept": "application/json", "User-Agent": user_agent}
        if bearer:
            request_headers["Authorization"] = "Bearer " + bearer
        if headers:
            request_headers.update(headers)

        data = None
        if method != "GET":
            if json_body is not None:
                data = json.dumps(json_body).encode("utf-8")
                request_headers["Content-Type"] = "application/json"
            else:
                data = urllib.parse.urlencode(form or {}).encode("utf-8")
                request_headers["Content-Type"] = "application/x-www-form-urlencoded"

        request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self._http_timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", "ignore")
            except Exception:
                pass
            raise AuthError(self._error_message(exc.code, body_text))
        except urllib.error.URLError as exc:
            raise AuthError(f"网络连接失败：{exc.reason}")
        except Exception as exc:  # 超时、DNS、SSL 等统一兜底
            raise AuthError(f"请求失败：{exc}")

        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            raise AuthError("服务器响应解析失败，请稍后重试。")

        if isinstance(payload, dict) and payload.get("error"):
            error = str(payload["error"])
            description = payload.get("error_description") or ""
            raise AuthError(f"{error}: {description}".rstrip(": "))
        return payload

    @staticmethod
    def _error_message(status: int, body_text: str) -> str:
        """把 HTTP 错误体中的 error / error_description / XErr 提取为可读中文前缀的消息。

        Xbox / XSTS 错误体用 ``XErr`` 数字码标识具体限制（未开通、未成年、地区限制等），
        需要把该码一并保留进消息，供 ``_translate_xsts`` 按码翻译为中文说明。
        """
        if body_text:
            try:
                err = json.loads(body_text)
                if isinstance(err, dict):
                    parts = []
                    if err.get("error_description"):
                        parts.append(str(err["error_description"]))
                    if err.get("error"):
                        parts.append(str(err["error"]))
                    if err.get("XErr") is not None:
                        parts.append(str(err["XErr"]))
                    message = " / ".join(parts) or body_text
                    return f"HTTP {status}：{message}"
            except Exception:
                pass
            return f"HTTP {status}：{body_text}"
        return f"HTTP {status}：服务器请求失败"
