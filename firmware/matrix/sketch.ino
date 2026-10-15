/*
 * 点阵控制台 - MCU 侧
 *
 * 接收 Python 传来的 104 个像素值（13列 x 8行，按行排列），画到点阵上。
 * 用官方 matrix.draw() 接口，每个像素 0-7 级灰度。
 */

#include <Arduino_LED_Matrix.h>
#include <Arduino_RouterBridge.h>

Arduino_LED_Matrix matrix;

// 104 个像素，每行 13 个，共 8 行
static uint8_t pixels[104];

void setup() {
  matrix.begin();
  matrix.setGrayscaleBits(3);   // 3 位 = 8 级灰度
  matrix.clear();

  Bridge.begin();
  Bridge.provide("set_pixels", set_pixels);
}

// Python 传进来一个字符串，104 个字符，每个字符是 '0'-'7'
// 例如 "0000000000000" + ... 共 104 个
void set_pixels(String data) {
  if (data.length() < 104) {
    return;
  }

  for (int i = 0; i < 104; i++) {
    char c = data.charAt(i);
    if (c >= '0' && c <= '7') {
      pixels[i] = c - '0';
    } else {
      pixels[i] = 0;
    }
  }

  matrix.draw(pixels);
}

void loop() {
  // 由 Bridge 回调驱动
}
