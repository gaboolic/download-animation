#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CCTV动画剧集m3u8下载脚本
功能：
1. 输入CCTV视频页面URL
2. 解析页面获取itemid1（视频ID）
3. 调用API获取专辑信息和剧集列表
4. 对每个剧集URL，获取m3u8链接
5. 下载每个剧集的m3u8文件到本地
"""

import re
import requests
import os
import json
import time
import random
import subprocess
from urllib.parse import urlparse, parse_qs, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

class CCTVDownloader:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://tv.cctv.com/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def extract_itemid_from_url(self, url):
        """从URL中提取视频ID (itemid1)"""
        # URL格式: https://tv.cctv.com/2025/12/06/VIDE2bG5I0c3AD1EQvX1pxjF251206.shtml
        match = re.search(r'VIDE([A-Za-z0-9]+)', url)
        if match:
            return 'VIDE' + match.group(1)
        return None
    
    def extract_itemid_from_html(self, html_content):
        """从HTML中提取itemid1"""
        # 从meta标签中提取
        match = re.search(r'<meta\s+name="contentid"\s+content="([^"]+)"', html_content)
        if match:
            return match.group(1)
        
        # 从JavaScript变量中提取
        match = re.search(r'var\s+itemid1\s*=\s*"([^"]+)"', html_content)
        if match:
            return match.group(1)
        
        return None
    
    def extract_guid_from_html(self, html_content):
        """从HTML中提取guid（视频GUID，用于获取m3u8）"""
        # 从JavaScript变量中提取guid
        match = re.search(r'var\s+guid\s*=\s*"([^"]+)"', html_content)
        if match:
            return match.group(1)
        return None
    
    def get_page_html(self, url):
        """获取页面HTML"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"获取页面失败: {e}")
            return None
    
    def get_album_info(self, itemid1):
        """获取专辑信息"""
        url = f"https://api.cntv.cn/NewVideoset/getVideoAlbumInfoByVideoId?id={itemid1}&serviceId=tvcctv"
        
        try:
            # 使用JSONP方式调用
            response = self.session.get(url, params={'cb': 'callback'}, timeout=30)
            response.raise_for_status()
            
            # 解析JSONP响应
            content = response.text
            # 移除JSONP包装
            if content.startswith('callback(') and content.endswith(');'):
                json_str = content[9:-2]
                data = json.loads(json_str)
                return data
            else:
                # 尝试直接解析JSON
                data = json.loads(content)
                return data
        except Exception as e:
            print(f"获取专辑信息失败: {e}")
            return None
    
    def get_episode_list(self, album_id, data_order=None):
        """获取剧集列表"""
        # 根据index_dhp.js的逻辑，从当前集数往前36集
        if data_order is None:
            order_param = ""
        else:
            order_param = f"&order={max(0, data_order - 36)}"
        
        url = f"https://api.cntv.cn/NewVideo/getVideoStreamByAlbumId?id={album_id}&mode=1&sort=asc&n=100&serviceId=tvcctv{order_param}"
        
        try:
            response = self.session.get(url, params={'cb': 'callback1'}, timeout=30)
            response.raise_for_status()
            
            content = response.text
            # 移除JSONP包装
            if 'callback1(' in content:
                json_str = re.search(r'callback1\((.*)\);?$', content, re.DOTALL)
                if json_str:
                    data = json.loads(json_str.group(1))
                    return data
            else:
                data = json.loads(content)
                return data
        except Exception as e:
            print(f"获取剧集列表失败: {e}")
            return None
    
    def get_video_info(self, guid):
        """获取视频播放信息，提取m3u8链接"""
        
        # 构建API参数
        # 根据实际API，需要这些参数：pid, client, im, tsp, vn, vc, uid, wlan
        pid = guid
        client = "flash"
        im = "0"
        tsp = str(int(time.time()))  # 时间戳
        vn = "2049"  # 版本号
        uid = ''.join(random.choices('0123456789ABCDEF', k=32))  # 随机32位十六进制
        
        # vc参数可能需要计算，先使用示例值
        vc = ''.join(random.choices('0123456789ABCDEF', k=32))
        wlan = ""
        
        # 构建API URL
        api_url = f"https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do"
        params = {
            'pid': pid,
            'client': client,
            'im': im,
            'tsp': tsp,
            'vn': vn,
            'vc': vc,
            'uid': uid,
            'wlan': wlan
        }
        
        try:
            response = self.session.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 直接从hls_url字段提取
            if 'hls_url' in data and data['hls_url']:
                return data['hls_url']
            
            # 如果hls_url为空，尝试从manifest中获取
            if 'manifest' in data:
                manifest = data['manifest']
                # 优先使用hls_enc_url或hls_h5e_url
                if 'hls_enc_url' in manifest and manifest['hls_enc_url']:
                    return manifest['hls_enc_url']
                if 'hls_h5e_url' in manifest and manifest['hls_h5e_url']:
                    return manifest['hls_h5e_url']
                if 'hls_enc2_url' in manifest and manifest['hls_enc2_url']:
                    return manifest['hls_enc2_url']
            
            return None
        except Exception as e:
            print(f"  获取视频信息API错误: {e}")
            return None
    
    def extract_m3u8_from_data(self, data):
        """从API响应数据中提取m3u8链接（备用方法）"""
        if not isinstance(data, dict):
            return None
        
        # 优先从hls_url字段提取
        if 'hls_url' in data and data['hls_url']:
            return data['hls_url']
        
        # 从manifest中提取
        if 'manifest' in data:
            manifest = data['manifest']
            if 'hls_enc_url' in manifest and manifest['hls_enc_url']:
                return manifest['hls_enc_url']
            if 'hls_h5e_url' in manifest and manifest['hls_h5e_url']:
                return manifest['hls_h5e_url']
            if 'hls_enc2_url' in manifest and manifest['hls_enc2_url']:
                return manifest['hls_enc2_url']
        
        # 递归搜索m3u8链接（备用）
        def find_m3u8(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and '.m3u8' in value:
                        return value
                    result = find_m3u8(value)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = find_m3u8(item)
                    if result:
                        return result
            return None
        
        return find_m3u8(data)
    
    def get_m3u8_from_page(self, episode_url):
        """从剧集页面获取m3u8链接"""
        html = self.get_page_html(episode_url)
        if not html:
            return None
        
        # 提取guid（视频GUID，用于获取m3u8）
        guid = self.extract_guid_from_html(html)
        if not guid:
            print(f"  无法从页面提取guid")
            return None
        
        print(f"  提取到guid: {guid}")
        
        # 通过API获取m3u8链接
        return self.get_video_info(guid)
    
    def download_m3u8(self, m3u8_url, output_path):
        """下载m3u8文件"""
        try:
            response = self.session.get(m3u8_url, timeout=30)
            response.raise_for_status()
            
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            print(f"下载m3u8失败: {e}")
            return False
    
    def parse_m3u8(self, m3u8_content, base_url):
        """解析m3u8内容，获取所有ts片段URL"""
        ts_urls = []
        lines = m3u8_content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            # 如果是URL
            if line.endswith('.m3u8') or line.endswith('.ts'):
                # 处理相对URL
                if line.startswith('/'):
                    # 从base_url提取域名
                    parsed = urlparse(base_url)
                    ts_url = f"{parsed.scheme}://{parsed.netloc}{line}"
                elif line.startswith('http'):
                    ts_url = line
                else:
                    # 相对路径
                    ts_url = urljoin(base_url, line)
                ts_urls.append(ts_url)
        
        return ts_urls
    
    def get_final_m3u8(self, m3u8_url):
        """获取最终的m3u8文件（处理主播放列表）"""
        try:
            response = self.session.get(m3u8_url, timeout=30)
            response.raise_for_status()
            content = response.text
            
            # 如果是主播放列表（包含子m3u8）
            lines = content.strip().split('\n')
            for i, line in enumerate(lines):
                if line.startswith('#EXT-X-STREAM-INF'):
                    # 下一行应该是子m3u8的URL
                    if i + 1 < len(lines):
                        sub_m3u8 = lines[i + 1].strip()
                        if not sub_m3u8 or sub_m3u8.startswith('#'):
                            continue
                        if sub_m3u8.startswith('/'):
                            parsed = urlparse(m3u8_url)
                            sub_m3u8_url = f"{parsed.scheme}://{parsed.netloc}{sub_m3u8}"
                        elif sub_m3u8.startswith('http'):
                            sub_m3u8_url = sub_m3u8
                        else:
                            sub_m3u8_url = urljoin(m3u8_url, sub_m3u8)
                        
                        # 递归获取子m3u8
                        result = self.get_final_m3u8(sub_m3u8_url)
                        if result[0]:  # 如果成功获取
                            return result
            
            # 如果没有子m3u8，返回当前内容
            return content, m3u8_url
        except Exception as e:
            print(f"  获取最终m3u8失败: {e}")
            return None, None
    
    def download_with_ffmpeg(self, m3u8_url, output_path):
        """使用ffmpeg下载并转换为mp4"""
        try:
            # 检查ffmpeg是否可用
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, 
                                  timeout=5)
            if result.returncode != 0:
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        
        try:
            # 使用ffmpeg下载
            cmd = [
                'ffmpeg',
                '-i', m3u8_url,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                '-y',  # 覆盖已存在的文件
                output_path
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # 等待完成
            stdout, stderr = process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path):
                return True
            else:
                print(f"  ffmpeg错误: {stderr[:200]}")
                return False
        except Exception as e:
            print(f"  ffmpeg执行失败: {e}")
            return False
    
    def download_single_ts(self, ts_url, ts_index, total, temp_dir):
        """下载单个ts片段"""
        try:
            response = self.session.get(ts_url, timeout=30)
            response.raise_for_status()
            
            ts_file = os.path.join(temp_dir, f"segment_{ts_index:05d}.ts")
            with open(ts_file, 'wb') as f:
                f.write(response.content)
            
            return ts_file, ts_index, None
        except Exception as e:
            return None, ts_index, str(e)
    
    def download_ts_segments(self, ts_urls, temp_dir, max_workers=8):
        """多线程并行下载所有ts片段"""
        downloaded_files = {}
        failed_count = 0
        lock = Lock()
        completed = 0
        
        def update_progress():
            nonlocal completed
            with lock:
                completed += 1
                print(f"    下载进度: {completed}/{len(ts_urls)}", end='\r')
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有下载任务
            futures = {
                executor.submit(self.download_single_ts, ts_url, i+1, len(ts_urls), temp_dir): (i+1, ts_url)
                for i, ts_url in enumerate(ts_urls)
            }
            
            # 收集结果
            for future in as_completed(futures):
                ts_file, ts_index, error = future.result()
                update_progress()
                
                if ts_file:
                    downloaded_files[ts_index] = ts_file
                else:
                    failed_count += 1
                    if error:
                        print(f"\n    片段 {ts_index} 下载失败: {error}")
        
        # 按索引排序
        sorted_files = [downloaded_files[i] for i in sorted(downloaded_files.keys())]
        
        print(f"\n    共下载 {len(sorted_files)}/{len(ts_urls)} 个片段", end='')
        if failed_count > 0:
            print(f" (失败: {failed_count})")
        else:
            print()
        
        return sorted_files
    
    def merge_ts_to_mp4(self, ts_files, output_path):
        """合并ts文件为mp4"""
        try:
            # 使用ffmpeg合并（如果可用）
            try:
                result = subprocess.run(['ffmpeg', '-version'], 
                                      capture_output=True, 
                                      timeout=5)
                if result.returncode == 0:
                    # 创建文件列表
                    list_file = output_path.replace('.mp4', '_list.txt')
                    with open(list_file, 'w', encoding='utf-8') as f:
                        for ts_file in ts_files:
                            f.write(f"file '{os.path.abspath(ts_file)}'\n")
                    
                    cmd = [
                        'ffmpeg',
                        '-f', 'concat',
                        '-safe', '0',
                        '-i', list_file,
                        '-c', 'copy',
                        '-y',
                        output_path
                    ]
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    process.communicate()
                    
                    # 清理临时文件
                    try:
                        os.remove(list_file)
                    except:
                        pass
                    
                    if process.returncode == 0 and os.path.exists(output_path):
                        return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            # 如果没有ffmpeg，直接合并二进制文件
            print("    使用二进制方式合并...")
            with open(output_path, 'wb') as outfile:
                for ts_file in ts_files:
                    if os.path.exists(ts_file):
                        with open(ts_file, 'rb') as infile:
                            outfile.write(infile.read())
            
            return True
        except Exception as e:
            print(f"  合并失败: {e}")
            return False
    
    def download_m3u8_to_mp4(self, m3u8_url, output_path, max_workers=8):
        """下载m3u8并转换为mp4"""
        # 检查文件是否已存在
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            print(f"  ⏭ 文件已存在，跳过: {output_path} ({file_size:.2f} MB)")
            return True
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 方法1: 尝试使用ffmpeg直接下载（最快）
        print("  尝试使用ffmpeg下载...")
        if self.download_with_ffmpeg(m3u8_url, output_path):
            print(f"  ✓ ffmpeg下载成功")
            return True
        
        # 方法2: 多线程下载ts片段并合并
        print("  使用多线程下载方式...")
        ts_files = []
        temp_dir = None
        try:
            # 获取最终的m3u8内容
            m3u8_content, final_m3u8_url = self.get_final_m3u8(m3u8_url)
            if not m3u8_content:
                return False
            
            # 解析m3u8获取ts片段列表
            ts_urls = self.parse_m3u8(m3u8_content, final_m3u8_url)
            if not ts_urls:
                print("  无法解析ts片段列表")
                return False
            
            print(f"  找到 {len(ts_urls)} 个ts片段，使用 {max_workers} 个线程并行下载")
            
            # 创建临时目录
            temp_dir = os.path.join(os.path.dirname(output_path), '.temp_ts')
            os.makedirs(temp_dir, exist_ok=True)
            
            # 多线程下载所有ts片段
            ts_files = self.download_ts_segments(ts_urls, temp_dir, max_workers)
            
            if not ts_files:
                print("  没有成功下载任何片段")
                return False
            
            # 合并为mp4
            print("  正在合并为mp4...")
            if self.merge_ts_to_mp4(ts_files, output_path):
                print(f"  ✓ 合并成功")
                return True
            else:
                return False
        except Exception as e:
            print(f"  下载转换失败: {e}")
            return False
        finally:
            # 清理临时文件
            try:
                if ts_files:
                    for ts_file in ts_files:
                        if os.path.exists(ts_file):
                            os.remove(ts_file)
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        os.rmdir(temp_dir)
                    except:
                        pass  # 目录可能不为空，忽略错误
            except Exception as e:
                pass  # 忽略清理错误
    
    def download_episodes(self, start_url, output_dir="downloads"):
        """主函数：下载所有剧集的m3u8"""
        print(f"开始处理URL: {start_url}")
        
        # 1. 获取页面HTML
        print("\n[1/5] 获取页面HTML...")
        html = self.get_page_html(start_url)
        if not html:
            print("无法获取页面HTML")
            return
        
        # 2. 提取视频ID
        print("\n[2/5] 提取视频ID...")
        itemid1 = self.extract_itemid_from_url(start_url) or self.extract_itemid_from_html(html)
        if not itemid1:
            print("无法提取视频ID")
            return
        print(f"视频ID: {itemid1}")
        
        # 3. 获取专辑信息
        print("\n[3/5] 获取专辑信息...")
        album_info = self.get_album_info(itemid1)
        if not album_info or 'data' not in album_info:
            print("无法获取专辑信息")
            return
        
        album_data = album_info['data']
        album_id = album_data.get('id')
        album_title = album_data.get('title', '未知专辑')
        data_order = album_data.get('order', 0)
        
        print(f"专辑ID: {album_id}")
        print(f"专辑标题: {album_title}")
        print(f"当前集数: {data_order}")
        
        # 4. 获取剧集列表
        print("\n[4/5] 获取剧集列表...")
        episode_list_data = self.get_episode_list(album_id, data_order)
        if not episode_list_data or 'data' not in episode_list_data:
            print("无法获取剧集列表")
            return
        
        episodes = episode_list_data['data'].get('list', [])
        print(f"找到 {len(episodes)} 个剧集")
        
        if not episodes:
            print("剧集列表为空")
            return
        
        # 5. 创建输出目录
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', album_title)
        episode_dir = os.path.join(output_dir, safe_title)
        os.makedirs(episode_dir, exist_ok=True)
        
        # 6. 下载每个剧集并转换为mp4
        print("\n[5/5] 开始下载并转换为mp4文件...")
        success_count = 0
        fail_count = 0
        
        for i, episode in enumerate(episodes, 1):
            episode_id = episode.get('id', '')
            episode_title = episode.get('title', f'第{i}集')
            episode_url = episode.get('url', '')
            
            print(f"\n[{i}/{len(episodes)}] 处理: {episode_title}")
            print(f"  URL: {episode_url}")
            
            if not episode_url:
                print("  ✗ 缺少剧集URL")
                fail_count += 1
                continue
            
            # 获取m3u8链接
            print("  正在获取m3u8链接...")
            m3u8_url = self.get_m3u8_from_page(episode_url)
            
            if not m3u8_url:
                print("  ✗ 无法获取m3u8链接")
                fail_count += 1
                continue
            
            print(f"  m3u8链接: {m3u8_url}")
            
            # 保存为mp4文件
            safe_episode_title = re.sub(r'[<>:"/\\|?*]', '_', episode_title)
            mp4_filename = f"{i:03d}_{safe_episode_title}.mp4"
            mp4_path = os.path.join(episode_dir, mp4_filename)
            
            # 检查文件是否已存在
            if os.path.exists(mp4_path):
                file_size = os.path.getsize(mp4_path) / (1024 * 1024)  # MB
                print(f"  ⏭ 文件已存在，跳过下载 ({file_size:.2f} MB)")
                success_count += 1
            elif self.download_m3u8_to_mp4(m3u8_url, mp4_path, max_workers=8):
                if os.path.exists(mp4_path):
                    file_size = os.path.getsize(mp4_path) / (1024 * 1024)  # MB
                    print(f"  ✓ 已保存: {mp4_path} ({file_size:.2f} MB)")
                success_count += 1
            else:
                fail_count += 1
            
            # 避免请求过快
            time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"下载完成!")
        print(f"成功: {success_count}, 失败: {fail_count}")
        print(f"输出目录: {episode_dir}")
        print(f"{'='*60}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python download_episodes_m3u8.py <CCTV视频页面URL> [输出目录]")
        print("\n示例:")
        print("  python download_episodes_m3u8.py https://tv.cctv.com/2025/12/06/VIDE2bG5I0c3AD1EQvX1pxjF251206.shtml")
        sys.exit(1)
    
    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "downloads"
    
    downloader = CCTVDownloader()
    downloader.download_episodes(url, output_dir)


if __name__ == "__main__":
    main()

