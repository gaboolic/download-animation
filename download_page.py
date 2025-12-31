import requests
import os
from datetime import datetime

def download_page(url, output_file=None):
    """
    下载指定URL的网页源代码
    
    Args:
        url: 要下载的网页URL
        output_file: 输出文件名，如果为None则自动生成
    """
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 发送HTTP GET请求
        print(f"正在下载: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        # 检查响应状态码
        response.raise_for_status()
        
        # 如果没有指定输出文件名，则自动生成
        if output_file is None:
            # 从URL中提取文件名，或使用时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"page_source_{timestamp}.html"
        
        # 确保输出文件路径在项目文件夹中
        output_path = os.path.join(os.path.dirname(__file__), output_file)
        
        # 保存网页源代码
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"下载成功！文件已保存到: {output_path}")
        print(f"文件大小: {len(response.text)} 字符")
        
        return output_path
        
    except requests.exceptions.RequestException as e:
        print(f"下载失败: {e}")
        return None

if __name__ == "__main__":
    # 目标URL
    url = "https://tv.cctv.com/2025/12/06/VIDE2bG5I0c3AD1EQvX1pxjF251206.shtml?spm=C55899450127.PmnAq0JRAvBL.0.0"
    
    # 下载网页源代码
    download_page(url, output_file="cctv_page_source.html")

