import win32gui
import win32ui
import win32con
import win32api
import numpy as np
import pyautogui
import keyboard
import time
import cv2
from test import image_processor
import ctypes
from datetime import datetime

# 放在所有程式邏輯執行之前
try:
    # 這是 Windows 8.1 之後最推薦的做法
    ctypes.windll.shcore.SetProcessDpiAwareness(1) 
except Exception:
    # 如果上面的失敗（舊版 Windows），使用這個備案
    ctypes.windll.user32.SetProcessDPIAware()

class GameAutomator:
    def __init__(self, appName, tm_targets):
        self.appName = appName
        self.ip = image_processor()
        
        self.enable_spinning = False  # 控制旋轉寶石偵測
        self.enable_static = False    # 控制固定模板偵測
        self.enable_restart = False   # 控制重啟按鈕偵測
        self.is_running = True        # 控制整個程式結束

        # --- 預處理 Template Matching (固定位置物品) ---
        # tm_targets 格式: {'name': 'path'}
        self.templates = {}
        for name, path in tm_targets.items():
            tpl = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if tpl is not None:
                # 儲存圖片及其尺寸，方便計算中心點
                h, w = tpl.shape[:2]
                self.templates[name] = {'img': tpl, 'w': w, 'h': h}
       
        keyboard.add_hotkey('f1', self.toggle_spinning)
        keyboard.add_hotkey('f2', self.toggle_static)
        keyboard.add_hotkey('f3', self.toggle_restart)
        keyboard.add_hotkey('esc', self.stop_all)
        
        print("--- 自動化腳本已啟動 ---")
        print("[F1] 切換旋轉寶石偵測 | [F2] 切換固定物件偵測 | [F3] 切換重啟按鈕偵測 | [ESC] 結束退出")
    
    def toggle_spinning(self):
        self.enable_spinning = not self.enable_spinning
        print(f">> 旋轉寶石偵測: {'開啟' if self.enable_spinning else '關閉'}")

    def toggle_static(self):
        self.enable_static = not self.enable_static
        print(f">> 固定物件偵測: {'開啟' if self.enable_static else '關閉'}")
        
    def toggle_restart(self):
        self.enable_restart = not self.enable_restart
        print(f">> 重啟按鈕偵測: {'開啟' if self.enable_restart else '關閉'}")

    def stop_all(self):
        self.is_running = False
        print("正在停止程式...")
        
    def click_target(self, x, y, window_rect):
        """
        將相對窗口座標轉換為螢幕絕對座標並點擊
        window_rect: (left, top, right, bot)
        """
        left, top, _, _ = window_rect
        screen_x = left + x
        screen_y = top + y
        
        # 移動並點擊 (可以加入 duration 模擬真人)
        pyautogui.moveTo(screen_x, screen_y, duration=0.1)
        pyautogui.click(screen_x, screen_y)
        # 點擊後稍微延遲，避免連點
        time.sleep(0.5)
        
    def post_click(self, x, y):
        """
        後台點擊：不移動實體滑鼠，直接對視窗發送點擊訊息
        x, y 為相對視窗客戶區的座標
        """
        hwnd = win32gui.FindWindow(None, self.appName)
        if not hwnd: return

        # 將座標打包成 Windows 訊息需要的格式 (LPARAM)
        # y 放在高 16 位元，x 放在低 16 位元
        lparam = win32api.MAKELONG(x, y)
        
        # 發送滑鼠左鍵按下與放開訊息
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.05) # 模擬按下的微小延遲
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

        print(f"[後台點擊] 座標: ({x}, {y})")
                
    def get_screenshot_opencv(self, appName):
        hwnd = win32gui.FindWindow(None, appName)
        if not hwnd: return None, None
        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bot = rect
        left, top, right, bot = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bot - top
        wDC = win32gui.GetWindowDC(hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, width, height)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0, 0), (width, height), dcObj, (0, 0), win32con.SRCCOPY)
        signedIntsArray = dataBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (height, width, 4)
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())
        return img, rect

    def detect(self):
        while self.is_running:
            now = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            frame, rect = self.get_screenshot_opencv(self.appName)
            if frame is None: 
                print(f"找不到窗口: {self.appName}")
                time.sleep(1)
                continue
            
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)

            # 1. 偵測旋轉寶石
            if self.enable_spinning:
                result = self.ip.parallel_matching(gray_frame)
                if result[0] > 0.8:
                    conf, pos, angle = result
                    print(f"[{now}] [+] 擊中 浮動寶石! 相似度: {conf:.2f}")
                    self.post_click(pos[0], pos[1])

            # 2. 偵測固定位置物件
            if self.enable_static:
                fixed_gem = self.templates.get("fixed_gem")
                if fixed_gem is not None:
                    res = cv2.matchTemplate(gray_frame, fixed_gem['img'], cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                    
                    if max_val > 0.8:
                        # 計算中心點：左上座標 + 模板寬高的一半
                        center_x = max_loc[0] + fixed_gem['w'] // 2
                        center_y = max_loc[1] + fixed_gem['h'] // 2
                        
                        print(f"[{now}] [+] 擊中 廣告寶石! 相似度: {max_val:.2f}")
                        self.post_click(center_x, center_y)
                        
            if self.enable_restart:
                restart_tpl = self.templates.get("restart_btn")
                if restart_tpl:
                    res = cv2.matchTemplate(gray_frame, restart_tpl['img'], cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                    
                    if max_val > 0.8:
                        center_x = max_loc[0] + restart_tpl['w'] // 2
                        center_y = max_loc[1] + restart_tpl['h'] // 2
                        
                        print(f"[{now}] [+] 擊中 重啟按鈕! 相似度: {max_val:.2f}")
                        self.post_click(center_x, center_y)
            time.sleep(0.1)  # 控制偵測頻率，避免過度佔用 CPU
                        
# 使用範例
if __name__ == "__main__":
    targets = {
        "fixed_gem": "templates/ad-dm-template.png",
        "restart_btn": "templates/gm-restart-template.png"
    }
    bot = GameAutomator("夜神模擬器", targets)
    bot.detect()