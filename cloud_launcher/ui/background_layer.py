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

"""主窗口最底层背景层。

v1.2.4.1 口径（修正 v1.2.4.0 的全屏柔化做法）：
- 本层只负责把外部壁纸以**清晰**等比 cover 铺满整窗；卡片 / 侧栏等玻璃片内部的局部磨砂
  由各自 paintEvent 完成（见 ``frosted_backdrop.paint_frosted_panel``），本层不再做全屏
  降采样柔化、也不叠整窗中性磨砂罩——卡片之外露出的壁纸保持清晰。
- 未检测到外部壁纸（目录缺失 / 文件损坏 / 被删除）时，静默回退蓝白两段默认渐变。

全程 try/except 不弹窗、不崩溃；不挂 QGraphicsBlurEffect、不引入第三方模糊库。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from .. import constants as C
from .appearance import appearance
from .frosted_backdrop import backdrop, cover_rect


class BackgroundLayer(QWidget):
    """铺满整窗的最底层背景控件；鼠标事件全部穿透，不拦截上层交互。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self._source: QPixmap | None = None
        self._brightness: float = 0.0

    # ---------- 壁纸注入 ----------
    def set_wallpaper(self, pixmap: QPixmap | None, brightness: float = 0.0) -> None:
        self._source = pixmap if (pixmap is not None and not pixmap.isNull()) else None
        self._brightness = max(0.0, min(1.0, float(brightness))) if self._source else 0.0
        # 同步给共享 backdrop，供卡片 / 侧栏截取自身后方小块做局部磨砂；窗口尺寸缓存由
        # 主窗口 resizeEvent 调用 backdrop.render_window 重建。
        backdrop.set_source(self._source, self._brightness)
        self.update()

    @property
    def brightness(self) -> float:
        return self._brightness

    # ---------- 绘制 ----------
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 重写约定)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if self._source is not None:
            # 清晰 cover 铺满：等比放大、居中裁切，不做降采样柔化。
            target = cover_rect(self.width(), self.height(),
                                self._source.width(), self._source.height())
            painter.drawPixmap(target, self._source, QRectF(self._source.rect()))
        else:
            self._paint_default_gradient(painter)

        # v1.3.9.0：整窗背景七色染色（无染色时返回 None，不画）。
        tint = appearance.bg_tint_rgba()
        if tint is not None:
            painter.fillRect(self.rect(), QColor(*tint))

        painter.end()

    def _paint_default_gradient(self, painter: QPainter) -> None:
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(C.COLOR_BG_TOP))
        gradient.setColorAt(1.0, QColor(C.COLOR_BG_BOTTOM))
        painter.fillRect(self.rect(), QBrush(gradient))
