import cv2
import pickle
import numpy as np
from concurrent.futures import ThreadPoolExecutor

class image_processor:
    def __init__(self, processed_templates_pkl_path='processed_templates.pkl'):
        self.processed_templates_pkl_path = processed_templates_pkl_path
        self.templates_list = self.load_processed_templates()
    
    def load_processed_templates(self):
        try:
            with open(self.processed_templates_pkl_path, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return []

    def precompute_templates(self, template_path, angle_step=5):
        """
        預先處理模板圖，生成不同旋轉角度的版本並儲存到硬碟
        """
        template = cv2.imread(template_path, 0)
        h, w = template.shape
        center = (w // 2, h // 2)
        templates_data = []

        for angle in range(0, 360, angle_step):
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            # 建議使用 INTER_CUBIC 保持小圖 (24x24) 的邊緣銳利度
            rotated = cv2.warpAffine(template, matrix, (w, h), flags=cv2.INTER_CUBIC)
            templates_data.append({
                'angle': angle,
                'data': rotated
            })
        
        # 儲存到硬碟
        with open('processed_templates.pkl', 'wb') as f:
            pickle.dump(templates_data, f)
        return templates_data

    def match_single_template(self, args):
        """單個模板的匹配任務"""
        source_img, tpl_info = args
        res = cv2.matchTemplate(source_img, tpl_info['data'], cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        return (max_val, max_loc, tpl_info['angle'])

    def parallel_matching(self, source_img, max_workers=8):
        """
        使用多線程對預處理的模板進行匹配，找出最佳匹配結果
        """
        # 封裝參數
        tasks = [(source_img, tpl) for tpl in self.templates_list]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 並行執行
            results = list(executor.map(self.match_single_template, tasks))
        
        # 找出置信度最高者
        best_match = max(results, key=lambda x: x[0])
        return best_match # (score, location, angle)
    
    def draw_result(self, source_img, best_match, template_size=(24, 24)):
        """
        在原圖上繪製匹配到的最佳位置
        :param source_img: 原始影像 (1280x720)
        :param best_match: parallel_matching 返回的結果 (score, location, angle)
        :param template_size: 模板尺寸 (width, height)
        """
        # 建立副本以避免修改原圖
        output_img = source_img.copy()
        if len(output_img.shape) == 2:  # 如果是灰階圖則轉回 BGR 顯示
            output_img = cv2.cvtColor(output_img, cv2.COLOR_GRAY2BGR)

        score, top_left, angle = best_match
        tw, th = template_size
        
        # 計算右下角座標
        bottom_right = (top_left[0] + tw, top_left[1] + th)

        # 繪製矩形框 (綠色, 線寬 2)
        cv2.rectangle(output_img, top_left, bottom_right, (0, 255, 0), 2)

        # 在框上方標註角度與置信度
        label = f"Score: {score:.2f} | Angle: {angle}deg"
        cv2.putText(output_img, label, (top_left[0], top_left[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

        return output_img
    
    def draw_rotated_result(self, source_img, best_match, template_size=(24, 24)):
        """
        在原圖上繪製匹配到的最佳位置和旋轉角度的邊框
        """
        output_img = source_img.copy()
        if len(output_img.shape) == 2:
            output_img = cv2.cvtColor(output_img, cv2.COLOR_GRAY2BGR)

        score, top_left, angle = best_match
        tw, th = template_size
        
        # 1. 定義原始矩形的四個頂點 (相對於 top_left)
        # 注意：這裡假設旋轉中心是模板中心
        rect = ((top_left[0] + tw/2, top_left[1] + th/2), (tw, th), -angle)
        
        # 2. 取得旋轉矩形的四個頂點座標
        box = cv2.boxPoints(rect)
        box = np.int0(box) # 轉換為整數

        # 3. 繪製旋轉邊框
        cv2.drawContours(output_img, [box], 0, (0, 0, 255), 2)
        
        return output_img
    
    def get_result(self, source_img, *args, **kwargs):
        best_match = self.parallel_matching(source_img, *args, **kwargs)
        result_viz = self.draw_rotated_result(source_img, best_match, *args, **kwargs)
        return best_match, result_viz

if __name__ == "__main__":
    pr = image_processor()
    # 製作並儲存預處理模板
    # pr.precompute_templates('templates/float-dm-template.png', angle_step=1)

    # 繪製並顯示
    frame = cv2.imread('test-1.png', 0)
    result = pr.parallel_matching(frame, max_workers=8)
    print(f"最佳匹配置信度: {result[0]:.2f}, 位置: {result[1]}, 角度: {result[2]}")
        
    result_viz = pr.draw_result(frame, result, template_size=(24, 24))

    cv2.imshow("Detection Result", result_viz)
    cv2.waitKey(0)
    cv2.destroyAllWindows()