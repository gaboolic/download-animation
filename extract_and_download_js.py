import re
import requests
import os
from urllib.parse import urljoin, urlparse

def extract_js_urls_from_html(html_file):
    """
    从HTML文件中提取所有JavaScript文件的URL
    
    Args:
        html_file: HTML文件路径
        
    Returns:
        list: JavaScript文件URL列表
    """
    js_urls = []
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配所有script标签中的src属性
    # 匹配模式: <script ... src="..." ...>
    pattern = r'<script[^>]*src=["\']([^"\']+\.js[^"\']*)["\'][^>]*>'
    matches = re.findall(pattern, content, re.IGNORECASE)
    
    for match in matches:
        # 清理URL（去除查询参数中的.js，但保留文件扩展名）
        url = match.split('?')[0]  # 保留查询参数，但确保.js在文件名中
        if url.endswith('.js') or '.js?' in match:
            # 如果URL是协议相对URL（以//开头），添加https://
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                # 相对路径，需要添加域名
                url = 'https://tv.cctv.com' + url
            elif not url.startswith('http'):
                # 其他相对路径
                url = 'https://tv.cctv.com/' + url.lstrip('/')
            
            if url not in js_urls:
                js_urls.append(url)
    
    return js_urls

def download_js_file(url, output_dir="js_files"):
    """
    下载JavaScript文件
    
    Args:
        url: 要下载的JS文件URL
        output_dir: 输出目录
    """
    try:
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://tv.cctv.com/'
        }
        
        # 发送HTTP GET请求
        print(f"正在下载: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        # 检查响应状态码
        response.raise_for_status()
        
        # 从URL中提取文件名
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename or not filename.endswith('.js'):
            # 如果无法从URL提取文件名，使用URL的路径部分
            path_parts = [p for p in parsed_url.path.split('/') if p]
            if path_parts:
                filename = path_parts[-1]
            else:
                filename = f"script_{hash(url) % 10000}.js"
        
        # 确保文件名以.js结尾
        if not filename.endswith('.js'):
            filename += '.js'
        
        # 保存文件路径
        output_path = os.path.join(output_dir, filename)
        
        # 如果文件已存在，添加序号
        counter = 1
        original_path = output_path
        while os.path.exists(output_path):
            name, ext = os.path.splitext(original_path)
            output_path = f"{name}_{counter}{ext}"
            counter += 1
        
        # 保存文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
        except UnicodeEncodeError:
            # 如果UTF-8失败，使用二进制模式
            with open(output_path, 'wb') as f:
                f.write(response.content)
        
        print(f"  ✓ 保存到: {output_path} ({len(response.content)} 字节)")
        return output_path
        
    except requests.exceptions.RequestException as e:
        print(f"  ✗ 下载失败: {e}")
        return None
    except Exception as e:
        print(f"  ✗ 保存文件时出错: {e}")
        return None

def main():
    html_file = "cctv_page_source.html"
    
    if not os.path.exists(html_file):
        print(f"错误: 找不到文件 {html_file}")
        return
    
    print("=" * 60)
    print("从HTML中提取JavaScript文件URL...")
    print("=" * 60)
    
    # 提取所有JavaScript URL
    js_urls = extract_js_urls_from_html(html_file)
    
    print(f"\n找到 {len(js_urls)} 个JavaScript文件:\n")
    for i, url in enumerate(js_urls, 1):
        print(f"{i}. {url}")
    
    print("\n" + "=" * 60)
    print("开始下载JavaScript文件...")
    print("=" * 60 + "\n")
    
    # 下载所有文件
    success_count = 0
    fail_count = 0
    
    for url in js_urls:
        result = download_js_file(url)
        if result:
            success_count += 1
        else:
            fail_count += 1
        print()  # 空行分隔
    
    print("=" * 60)
    print(f"下载完成! 成功: {success_count}, 失败: {fail_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()

