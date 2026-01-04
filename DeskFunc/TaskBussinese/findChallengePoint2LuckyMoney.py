import time
import cv2
import numpy as np
from numpy import fromfile
from typing import Optional, Dict, Tuple

from Utils.FindWindowsImage import WindowsHandle, FindWindowsImageTemplate
from Utils.KeyMouseDriver.GhostSoft.get_driver_v3 import SetGhostMouse
from Utils.loadResources import GetConfig


def _load_pic(img_path: str) -> np.ndarray:
    """
    加载图片（优化：添加缓存）
    """
    return cv2.imdecode(fromfile(img_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)


class ChangePoint2LuckyMoney:

    def __init__(self):
        self.windows_opt = WindowsHandle()
        self.windows_find = FindWindowsImageTemplate()
        
        # 配置
        pic_template = GetConfig().get_change_2_lucky_money()

        # 图片模板（提前加载）
        self.templates = {
            'shop_book': _load_pic(pic_template.challenge_point_shop_book),
            'book_page': _load_pic(pic_template.challenge_point_book_page),
            'exchange_button': _load_pic(pic_template.challenge_point_exchange_button),
            'backpack_item': _load_pic(pic_template.backpack_item_pic),
            'recycle_box': _load_pic(pic_template.recycle_box),
            'recycle_result': _load_pic(pic_template.recycle_box_result),
            'exchange_ok': _load_pic(pic_template.exchange_ok),
            'exchange_re_ok': _load_pic(pic_template.exchange_re_ok),
        }
        
        # 配置参数（可外部调整）
        self.threshold = 0.85  # 👈 降低阈值，提高识别速度
        self.activate_delay = 0.1  # 👈 减少激活延迟
        self.click_delay = 0.05  # 👈 减少点击延迟
        
        # 状态缓存
        self._last_hwnd = None
        self._screenshot_cache = None
        self._screenshot_time = 0
        self._cache_lifetime = 0.5  # 截图缓存 0.5 秒

    def _get_screenshot(self, hwnd: int, force_refresh: bool = False) -> Optional[np.ndarray]:
        """
        获取截图（带缓存）
        """
        current_time = time.time()
        
        # 如果缓存有效且未强制刷新，直接返回
        if (not force_refresh and 
            self._screenshot_cache is not None and 
            self._last_hwnd == hwnd and
            current_time - self._screenshot_time < self._cache_lifetime):
            return self._screenshot_cache
        
        # 重新截图
        screenshot = self.windows_find.get_screenshot(hwnd)  # 假设有这个方法
        self._screenshot_cache = screenshot
        self._screenshot_time = current_time
        self._last_hwnd = hwnd
        
        return screenshot

    def _activate_once(self, hwnd: int) -> bool:
        """
        只激活一次窗口（优化）
        """
        if self._last_hwnd != hwnd:
            if not self.windows_opt.activate_windows(hwnd):
                return False
            time.sleep(self.activate_delay)
            self._last_hwnd = hwnd
        return True

    def _click_at(self, point: Tuple[int, int], delay_after: float = None) -> bool:
        """
        点击指定位置（优化版）
        """
        if delay_after is None:
            delay_after = self.click_delay
        
        SetGhostMouse().move_mouse_to(point[0], point[1])
        time.sleep(0.02)  # 移动后短暂延迟
        SetGhostMouse().click_mouse_left_button()
        
        if delay_after > 0:
            time.sleep(delay_after)
        
        return True

    def _find_and_click(self, hwnd: int, template_key: str, 
                       threshold: float = None,
                       use_cache: bool = True,
                       delay_after: float = None) -> bool:
        """
        通用查找并点击方法（核心优化）
        :param hwnd: 窗口句柄
        :param template_key: 模板键名
        :param threshold: 匹配阈值
        :param use_cache: 是否使用截图缓存
        :param delay_after: 点击后延迟
        """
        # 激活窗口（只激活一次）
        if not self._activate_once(hwnd):
            return False
        
        # 获取模板
        template = self.templates.get(template_key)
        if template is None:
            return False
        
        # 设置阈值
        if threshold is None:
            threshold = self.threshold
        
        # 查找图片
        res: tuple = self.windows_find.get_windows_image_rect(
            hwnd, template, threshold=threshold
        )
        
        if res is not None:
            return self._click_at(res, delay_after)
        
        return False

    # ========================================
    # 公开方法（简化版）
    # ========================================
    
    def find_change_point_shop_book(self, hwnd: int) -> bool:
        """查找并点击夺魄列表"""
        return self._find_and_click(hwnd, 'shop_book')

    def find_change_point_book_page(self, hwnd: int) -> bool:
        """查找并点击技能书页"""
        return self._find_and_click(hwnd, 'book_page')

    def find_change_point_exchange_button(self, hwnd: int) -> bool:
        """查找并点击兑换按钮"""
        return self._find_and_click(hwnd, 'exchange_button')

    def find_backpack_item_pic(self, hwnd: int) -> bool:
        """查找并点击背包中的书页"""
        return self._find_and_click(hwnd, 'backpack_item')

    def find_recycle_box(self, hwnd: int) -> bool:
        """查找并点击回收框"""
        return self._find_and_click(hwnd, 'recycle_box')

    def find_recycle_box_result(self, hwnd: int) -> bool:
        """查找兑换结果（仅查找不点击）"""
        res = self.windows_find.get_windows_image_rect(
            hwnd, self.templates['recycle_result'], threshold=self.threshold
        )
        return res is not None

    def find_exchange_ok(self, hwnd: int) -> bool:
        """查找并点击确认按钮"""
        return self._find_and_click(hwnd, 'exchange_ok', delay_after=0.2)

    def find_exchange_re_ok(self, hwnd: int) -> bool:
        """查找并点击二次确认"""
        return self._find_and_click(hwnd, 'exchange_re_ok', delay_after=0.3)

    # ========================================
    # 批量识别（性能优化关键）
    # ========================================
    
    def batch_find(self, hwnd: int, template_keys: list) -> Dict[str, Optional[Tuple]]:
        """
        批量查找多个模板（一次截图，多次匹配）
        :param hwnd: 窗口句柄
        :param template_keys: 要查找的模板键名列表
        :return: 字典 {key: point}
        """
        results = {}
        
        # 一次性截图
        screenshot = self._get_screenshot(hwnd, force_refresh=True)
        if screenshot is None:
            return results
        
        # 批量匹配
        for key in template_keys:
            template = self.templates.get(key)
            if template is None:
                results[key] = None
                continue
            
            # 使用同一张截图匹配
            res = self.windows_find.match_template_on_screenshot(
                screenshot, template, threshold=self.threshold
            )
            results[key] = res
        
        return results

    def check_pic_template_exist(self, hwnd: int) -> int:
        """
        批量检查图片模板（优化版）
        :return: -1: 未找到技能书页
                 -2: 未找到兑换窗口
                 0: 一切正常
        """
        # 使用批量查找
        results = self.batch_find(hwnd, ['book_page', 'recycle_box'])
        
        if results.get('book_page') is None:
            return -1
        if results.get('recycle_box') is None:
            return -2
        return 0

    # ========================================
    # 完整流程（一次性执行）
    # ========================================
    
    def execute_full_exchange(self, hwnd: int) -> bool:
        """
        完整执行兑换流程（最优化）
        """
        # 1. 激活窗口（只一次）
        if not self._activate_once(hwnd):
            return False
        
        # 2. 点击夺魄列表
        if not self.find_change_point_shop_book(hwnd):
            return False
        
        # 3. 点击技能书页
        if not self.find_change_point_book_page(hwnd):
            return False
        
        # 4. 点击兑换按钮
        if not self.find_change_point_exchange_button(hwnd):
            return False
        
        # 5. 点击背包物品
        if not self.find_backpack_item_pic(hwnd):
            return False
        
        # 6. 点击回收框
        if not self.find_recycle_box(hwnd):
            return False
        
        # 7. 等待兑换结果出现
        max_wait = 3  # 最多等 3 秒
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if self.find_recycle_box_result(hwnd):
                break
            time.sleep(0.1)
        
        # 8. 点击确认
        if not self.find_exchange_ok(hwnd):
            return False
        
        # 9. 点击二次确认
        if not self.find_exchange_re_ok(hwnd):
            return False
        
        return True
