"""
点阵控制台 - Python 侧

职责：
  1. 跑一个网页服务器（端口 7000）
  2. 接收网页发来的像素数据
  3. 通过 Bridge 转发给 MCU，画到点阵上
"""

from arduino.app_utils import App, Bridge
from arduino.app_bricks.web_ui import WebUI

ui = WebUI()

# 保存当前画面，新客户端连上时同步过去
current_pixels = "0" * 104


def on_pixels(sid, data):
    """网页点了格子，把整幅画面发给 MCU。"""
    global current_pixels

    pixels = data.get("pixels") if isinstance(data, dict) else data
    if not isinstance(pixels, str) or len(pixels) != 104:
        return

    current_pixels = pixels

    # 调 MCU 的函数，画到点阵上
    Bridge.call("set_pixels", pixels)


def on_get_state(sid, data):
    """客户端连上时，把当前画面同步给它。"""
    return {"pixels": current_pixels}


ui.on_message("set_pixels", on_pixels)
ui.on_message("get_state", on_get_state)

App.run()
