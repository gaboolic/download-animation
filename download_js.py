import requests
import os

def download_js_file(url, output_file=None):
    """
    下载JavaScript文件
    
    Args:
        url: 要下载的JS文件URL（可以是协议相对URL，会自动添加https://）
        output_file: 输出文件名，如果为None则从URL中提取
    """
    try:
        # 处理协议相对URL
        if url.startswith('//'):
            url = 'https:' + url
        
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://tv.cctv.com/'
        }
        
        # 发送HTTP GET请求
        print(f"正在下载: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        # 检查响应状态码
        response.raise_for_status()
        
        # 如果没有指定输出文件名，则从URL中提取
        if output_file is None:
            # 从URL中提取文件名
            filename = url.split('/')[-1]
            # 如果URL中有查询参数，需要去掉
            if '?' in filename:
                filename = filename.split('?')[0]
            output_file = filename
        
        # 确保输出文件路径在项目文件夹中
        output_path = os.path.join(os.path.dirname(__file__), output_file)
        
        # 保存文件（使用二进制模式，但JS文件通常是文本）
        # 先尝试用UTF-8编码保存
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
        except UnicodeEncodeError:
            # 如果UTF-8失败，使用二进制模式
            with open(output_path, 'wb') as f:
                f.write(response.content)
        
        print(f"下载成功！文件已保存到: {output_path}")
        print(f"文件大小: {len(response.content)} 字节")
        
        return output_path
        
    except requests.exceptions.RequestException as e:
        print(f"下载失败: {e}")
        return None
    except Exception as e:
        print(f"保存文件时出错: {e}")
        return None

if __name__ == "__main__":
    # 从HTML中提取的JavaScript文件URL
    js_urls = [
        ("//r.img.cctvpic.com/photoAlbum/templet/common/DEPA1666850857533581/tv_jlp_tb.videcreat.js", "tv_jlp_tb.videcreat.js"),
        ("//r.img.cctvpic.com/photoAlbum/templet/common/DEPA1666850857533581/ptjszx_player.js", "ptjszx_player.js")
    ]
    
    # 下载所有JavaScript文件
    for js_url, output_file in js_urls:
        download_js_file(js_url, output_file=output_file)
        print()  # 空行分隔

