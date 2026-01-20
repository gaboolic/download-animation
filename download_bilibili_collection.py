#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bilibili合集下载脚本
功能：
1. 下载bilibili合集页面
2. 分析页面，提取每个视频的URL
3. 下载每个视频
"""

import re
import requests
import os
import json
import time
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

class BilibiliCollectionDownloader:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def download_page(self, url, output_file=None):
        """下载网页源代码"""
        try:
            print(f"正在下载页面: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            if output_file is None:
                output_file = "bilibili_collection_page.html"
            
            output_path = os.path.join(os.path.dirname(__file__), output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"页面已保存到: {output_path}")
            print(f"文件大小: {len(response.text)} 字符")
            return output_path, response.text
        except Exception as e:
            print(f"下载页面失败: {e}")
            return None, None
    
    def extract_collection_id(self, url):
        """从URL中提取合集ID"""
        # URL格式: https://space.bilibili.com/4520265/lists/3308869?type=season
        match = re.search(r'/lists/(\d+)', url)
        if match:
            return match.group(1)
        return None
    
    def extract_bvid_from_url(self, url):
        """从URL中提取BV号"""
        # URL格式: https://www.bilibili.com/video/BV1zEaLzMEck
        match = re.search(r'/video/(BV[a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        # 也支持av号
        match = re.search(r'/video/av(\d+)', url)
        if match:
            return f"av{match.group(1)}"
        return None
    
    def get_collection_info_from_video_page(self, video_url):
        """从视频页面获取合集信息"""
        try:
            print(f"正在获取视频页面信息: {video_url}")
            response = self.session.get(video_url, timeout=30)
            response.raise_for_status()
            html_content = response.text
            
            # 方法1: 从window.__INITIAL_STATE__中提取
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'window\.__playinfo__\s*=\s*({.+?});',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html_content, re.DOTALL)
                if match:
                    try:
                        data_str = match.group(1)
                        data = json.loads(data_str)
                        
                        # 查找合集信息
                        collection_info = self._extract_collection_from_json(data)
                        if collection_info:
                            return collection_info
                    except:
                        continue
            
            # 方法2: 从HTML中直接搜索合集链接
            # 合集链接格式: /space.bilibili.com/数字/lists/数字
            collection_pattern = r'/space\.bilibili\.com/(\d+)/lists/(\d+)'
            match = re.search(collection_pattern, html_content)
            if match:
                mid = match.group(1)
                season_id = match.group(2)
                return {
                    'mid': mid,
                    'season_id': season_id,
                    'collection_url': f"https://space.bilibili.com/{mid}/lists/{season_id}?type=season"
                }
            
            # 方法3: 从视频API获取合集信息
            bvid = self.extract_bvid_from_url(video_url)
            if bvid and bvid.startswith('BV'):
                # 调用视频信息API
                api_url = "https://api.bilibili.com/x/web-interface/view"
                params = {'bvid': bvid}
                response = self.session.get(api_url, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == 0 and 'data' in data:
                        video_data = data['data']
                        # 查找合集信息
                        if 'ugc_season' in video_data:
                            ugc_season = video_data['ugc_season']
                            if 'id' in ugc_season and 'mid' in video_data.get('owner', {}):
                                return {
                                    'mid': str(video_data['owner']['mid']),
                                    'season_id': str(ugc_season['id']),
                                    'collection_url': f"https://space.bilibili.com/{video_data['owner']['mid']}/lists/{ugc_season['id']}?type=season"
                                }
            
            return None
        except Exception as e:
            print(f"获取视频页面信息失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_collection_from_json(self, data, path=""):
        """递归从JSON数据中提取合集信息"""
        if isinstance(data, dict):
            # 检查是否包含合集信息
            if 'ugc_season' in data:
                ugc_season = data['ugc_season']
                if isinstance(ugc_season, dict) and 'id' in ugc_season:
                    mid = None
                    # 尝试从不同路径获取mid
                    if 'owner' in data:
                        mid = data['owner'].get('mid')
                    elif 'mid' in data:
                        mid = data['mid']
                    
                    if mid:
                        return {
                            'mid': str(mid),
                            'season_id': str(ugc_season['id']),
                            'collection_url': f"https://space.bilibili.com/{mid}/lists/{ugc_season['id']}?type=season"
                        }
            
            # 递归搜索
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    result = self._extract_collection_from_json(value, f"{path}.{key}")
                    if result:
                        return result
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    result = self._extract_collection_from_json(item, f"{path}[{i}]")
                    if result:
                        return result
        
        return None
    
    def extract_video_urls_from_html(self, html_content):
        """从HTML中提取视频URL"""
        video_urls = []
        
        # 方法1: 从JavaScript变量中提取
        # bilibili通常会在window.__INITIAL_STATE__或类似变量中存储数据
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.__playinfo__\s*=\s*({.+?});',
            r'"videoData"\s*:\s*({.+?})',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html_content, re.DOTALL)
            for match in matches:
                try:
                    data_str = match.group(1)
                    data = json.loads(data_str)
                    # 递归搜索视频URL
                    urls = self._extract_urls_from_json(data)
                    video_urls.extend(urls)
                except:
                    pass
        
        # 方法2: 直接搜索bilibili视频URL模式
        # https://www.bilibili.com/video/BVxxxxx
        bv_pattern = r'https?://www\.bilibili\.com/video/(BV[a-zA-Z0-9]+)'
        bv_matches = re.findall(bv_pattern, html_content)
        for bv_id in bv_matches:
            url = f"https://www.bilibili.com/video/{bv_id}"
            if url not in video_urls:
                video_urls.append(url)
        
        # 方法3: 搜索av号
        av_pattern = r'https?://www\.bilibili\.com/video/av(\d+)'
        av_matches = re.findall(av_pattern, html_content)
        for av_id in av_matches:
            url = f"https://www.bilibili.com/video/av{av_id}"
            if url not in video_urls:
                video_urls.append(url)
        
        return list(set(video_urls))  # 去重
    
    def _extract_urls_from_json(self, data, urls=None):
        """递归从JSON数据中提取URL"""
        if urls is None:
            urls = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['bvid', 'aid', 'video_url', 'url', 'link']:
                    if isinstance(value, str):
                        if 'bilibili.com/video' in value or value.startswith('BV') or value.startswith('av'):
                            if value.startswith('BV') or value.startswith('av'):
                                if value.startswith('BV'):
                                    url = f"https://www.bilibili.com/video/{value}"
                                else:
                                    url = f"https://www.bilibili.com/video/{value}"
                            else:
                                url = value
                            if url not in urls:
                                urls.append(url)
                elif isinstance(value, (dict, list)):
                    self._extract_urls_from_json(value, urls)
        elif isinstance(data, list):
            for item in data:
                self._extract_urls_from_json(item, urls)
        
        return urls
    
    def get_collection_info_from_api(self, collection_id, mid=None):
        """通过API获取合集信息"""
        # bilibili合集API - 尝试多个可能的API端点
        api_urls = [
            "https://api.bilibili.com/x/polymer/web-space/seasons_archives_list",
            "https://api.bilibili.com/x/space/seasons_archives",
            "https://api.bilibili.com/x/space/channel/video",
        ]
        
        for api_url in api_urls:
            params = {
                'mid': mid or '',
                'season_id': collection_id,
                'sort_reverse': 'false',
                'page_num': 1,
                'page_size': 100
            }
            
            try:
                response = self.session.get(api_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data.get('code') == 0:
                    return data
            except Exception as e:
                continue
        
        return None
    
    def get_video_pages(self, bvid):
        """获取视频的所有分P信息"""
        try:
            api_url = "https://api.bilibili.com/x/web-interface/view"
            params = {'bvid': bvid}
            response = self.session.get(api_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0 and 'data' in data:
                    video_data = data['data']
                    pages = video_data.get('pages', [])
                    if len(pages) > 1:
                        # 有多个分P，返回所有分P信息
                        return pages
                    else:
                        # 只有一个分P或没有分P信息
                        return None
        except Exception as e:
            # 如果获取失败，返回None，使用原始URL
            # 静默失败，不影响主流程
            pass
        return None
    
    def extract_video_urls_from_api(self, collection_id, mid=None):
        """从API获取视频列表，并展开多P视频的所有分集"""
        video_urls = []
        video_info_list = []  # 存储视频详细信息
        
        # 使用合集API
        api_url = "https://api.bilibili.com/x/polymer/web-space/seasons_archives_list"
        page = 1
        page_size = 50
        
        while True:
            params = {
                'mid': mid or '',
                'season_id': collection_id,
                'sort_reverse': 'false',
                'page_num': page,
                'page_size': page_size
            }
            
            try:
                response = self.session.get(api_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                print(f"  API响应 (第{page}页): code={data.get('code')}, message={data.get('message', '')}")
                
                if data.get('code') == 0 and 'data' in data:
                    data_obj = data['data']
                    
                    # 尝试不同的数据结构
                    archives = []
                    if 'archives' in data_obj:
                        archives = data_obj['archives']
                    elif 'list' in data_obj:
                        archives = data_obj['list']
                    elif 'vlist' in data_obj:
                        archives = data_obj['vlist']
                    
                    if not archives:
                        # 如果没有archives，尝试直接使用data
                        if isinstance(data_obj, list):
                            archives = data_obj
                        else:
                            break
                    
                    print(f"  第{page}页: 获取到 {len(archives)} 个视频")
                    
                    for archive in archives:
                        bvid = archive.get('bvid', '')
                        aid = archive.get('aid', '')
                        title = archive.get('title', '未知标题')
                        
                        if bvid:
                            # 检查是否有多个分P
                            pages = self.get_video_pages(bvid)
                            
                            if pages and len(pages) > 1:
                                # 有多个分P，展开每个分P
                                print(f"    展开多P视频: {title} (共{len(pages)}集)")
                                for page_info in pages:
                                    page_num = page_info.get('page', 1)
                                    page_title = page_info.get('part', title)
                                    # 构建带分P参数的URL
                                    url = f"https://www.bilibili.com/video/{bvid}?p={page_num}"
                                    video_urls.append(url)
                                    video_info_list.append({
                                        'url': url,
                                        'title': f"{title} - {page_title}",
                                        'bvid': bvid,
                                        'aid': aid,
                                        'page': page_num
                                    })
                            else:
                                # 单P视频或无法获取分P信息
                                url = f"https://www.bilibili.com/video/{bvid}"
                                video_urls.append(url)
                                video_info_list.append({
                                    'url': url,
                                    'title': title,
                                    'bvid': bvid,
                                    'aid': aid
                                })
                            
                            # 添加小延迟，避免请求过快
                            time.sleep(0.1)
                        elif aid:
                            # 对于av号，暂时不展开分P（av号已废弃，新视频都用BV号）
                            url = f"https://www.bilibili.com/video/av{aid}"
                            video_urls.append(url)
                            video_info_list.append({
                                'url': url,
                                'title': title,
                                'bvid': '',
                                'aid': aid
                            })
                    
                    # 获取总数，可能在data_obj或data中
                    total = data_obj.get('total', data.get('data', {}).get('total', 0))
                    if total == 0:
                        total = data.get('total', 0)
                    
                    print(f"  当前总数: {len(video_urls)} 个视频/分集, API返回总数: {total}")
                    
                    # 如果当前页返回的视频数少于page_size，说明已经是最后一页
                    # 或者已经获取的数量达到或超过总数
                    if len(archives) < page_size:
                        print(f"  已获取所有页面（当前页视频数 {len(archives)} < 每页大小 {page_size}）")
                        break
                    
                    if total > 0 and len(video_urls) >= total:
                        # 注意：这里total是视频数，不是分集数，所以可能不准确
                        # 但至少可以作为一个参考
                        print(f"  已获取所有视频（{len(video_urls)} >= {total}）")
                        break
                    
                    page += 1
                else:
                    error_msg = data.get('message', '未知错误')
                    print(f"  API返回错误: code={data.get('code')}, message={error_msg}")
                    break
            except Exception as e:
                print(f"  获取第{page}页失败: {e}")
                import traceback
                traceback.print_exc()
                break
        
        return video_urls, video_info_list
    
    def check_video_downloaded(self, video_url, output_dir, video_title=None):
        """检查视频是否已经下载（通过检查mp4文件是否存在）"""
        try:
            import subprocess
            import json
            
            # 从URL中提取BV号（最准确的标识）
            bvid = self.extract_bvid_from_url(video_url)
            
            # 首先，快速检查目录中是否已有mp4文件
            existing_files = []
            if os.path.exists(output_dir):
                existing_files = [f for f in os.listdir(output_dir) 
                                if os.path.isfile(os.path.join(output_dir, f)) 
                                and f.endswith(('.mp4', '.mkv', '.webm', '.flv'))]
                
                # 如果目录为空，直接返回False
                if not existing_files:
                    return False, None
                
                # 优先使用BV号精确匹配（最准确）
                if bvid:
                    bvid_files = [f for f in existing_files if bvid in f]
                    if bvid_files:
                        # 对于多分集视频，需要检查所有分集是否都存在
                        # 先获取视频信息，看有多少个分集
                        try:
                            result = subprocess.run(['python', '-m', 'yt_dlp', '--version'], 
                                                  capture_output=True, timeout=5)
                            if result.returncode != 0:
                                result = subprocess.run(['yt-dlp', '--version'], 
                                                      capture_output=True, timeout=5)
                                if result.returncode != 0:
                                    # yt-dlp不可用，使用简单匹配
                                    return True, os.path.join(output_dir, bvid_files[0])
                                use_python_module = False
                            else:
                                use_python_module = True
                            
                            # 获取视频信息，检查分集数量
                            if use_python_module:
                                cmd = ['python', '-m', 'yt_dlp', '--dump-json', '--no-warnings', '--quiet', video_url]
                            else:
                                cmd = ['yt-dlp', '--dump-json', '--no-warnings', '--quiet', video_url]
                            
                            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                                  universal_newlines=True, timeout=30)
                            
                            if result.returncode == 0 and result.stdout:
                                try:
                                    video_info = json.loads(result.stdout)
                                    # 检查是否有多个分集（entries）
                                    entries = video_info.get('entries', [])
                                    if entries:
                                        # 多分集视频，需要检查所有分集
                                        expected_count = len(entries)
                                        # 统计目录中该BV号对应的文件数（排除中间文件如.f100026.mp4等）
                                        bvid_complete_files = [f for f in bvid_files 
                                                              if not re.search(r'\.f\d+\.(mp4|m4a)$', f) 
                                                              and not f.endswith('.m4a')]
                                        if len(bvid_complete_files) >= expected_count:
                                            return True, os.path.join(output_dir, bvid_complete_files[0])
                                        else:
                                            # 分集不完整，需要重新下载
                                            print(f"    检测到分集不完整: 期望 {expected_count} 个，实际 {len(bvid_complete_files)} 个")
                                            return False, None
                                except (json.JSONDecodeError, KeyError):
                                    # JSON解析失败，继续检查文件名模式
                                    pass
                                
                                # 即使yt-dlp没有返回entries或解析失败，也要检查文件名模式
                                episode_pattern = re.compile(r'p(\d+)', re.IGNORECASE)
                                episode_numbers = set()
                                bvid_complete_files = [f for f in bvid_files 
                                                      if not re.search(r'\.f\d+\.(mp4|m4a)$', f) 
                                                      and not f.endswith('.m4a')]
                                
                                for filename in bvid_complete_files:
                                    match = episode_pattern.search(filename)
                                    if match:
                                        episode_numbers.add(int(match.group(1)))
                                
                                if episode_numbers:
                                    # 有分集标识，检查是否连续（从1开始）
                                    max_episode = max(episode_numbers)
                                    expected_episodes = set(range(1, max_episode + 1))
                                    if episode_numbers == expected_episodes:
                                        # 分集完整
                                        return True, os.path.join(output_dir, bvid_complete_files[0])
                                    else:
                                        # 分集不完整，需要重新下载
                                        missing = expected_episodes - episode_numbers
                                        print(f"    检测到分集不完整，缺少: {sorted(missing)}")
                                        return False, None
                                else:
                                    # 没有分集标识，可能是单集视频，有文件就认为已下载
                                    return True, os.path.join(output_dir, bvid_files[0])
                            else:
                                # yt-dlp返回错误或没有输出，尝试通过文件名模式检查
                                episode_pattern = re.compile(r'p(\d+)', re.IGNORECASE)
                                episode_numbers = set()
                                bvid_complete_files = [f for f in bvid_files 
                                                      if not re.search(r'\.f\d+\.(mp4|m4a)$', f) 
                                                      and not f.endswith('.m4a')]
                                
                                for filename in bvid_complete_files:
                                    match = episode_pattern.search(filename)
                                    if match:
                                        episode_numbers.add(int(match.group(1)))
                                
                                if episode_numbers:
                                    max_episode = max(episode_numbers)
                                    expected_episodes = set(range(1, max_episode + 1))
                                    if episode_numbers == expected_episodes:
                                        return True, os.path.join(output_dir, bvid_complete_files[0])
                                    else:
                                        missing = expected_episodes - episode_numbers
                                        print(f"    检测到分集不完整，缺少: {sorted(missing)}")
                                        return False, None
                                else:
                                    # 没有分集标识，可能是单集视频，有文件就认为已下载
                                    return True, os.path.join(output_dir, bvid_files[0])
                        except Exception as e:
                            # 如果获取信息失败，尝试通过文件名模式推断分集数量
                            # 检查文件名中是否有分集标识（如 p01, p02等）
                            episode_pattern = re.compile(r'p(\d+)', re.IGNORECASE)
                            episode_numbers = set()
                            # 排除中间文件，只检查完整的视频文件
                            bvid_complete_files = [f for f in bvid_files 
                                                  if not re.search(r'\.f\d+\.(mp4|m4a)$', f) 
                                                  and not f.endswith('.m4a')]
                            
                            for filename in bvid_complete_files:
                                match = episode_pattern.search(filename)
                                if match:
                                    episode_numbers.add(int(match.group(1)))
                            
                            if episode_numbers:
                                # 有分集标识，检查是否连续（从1开始）
                                max_episode = max(episode_numbers)
                                expected_episodes = set(range(1, max_episode + 1))
                                if episode_numbers == expected_episodes:
                                    # 分集完整
                                    return True, os.path.join(output_dir, bvid_complete_files[0])
                                else:
                                    # 分集不完整，需要重新下载
                                    missing = expected_episodes - episode_numbers
                                    print(f"    检测到分集不完整，缺少: {sorted(missing)}")
                                    return False, None
                            else:
                                # 没有分集标识，可能是单集视频，有文件就认为已下载
                                return True, os.path.join(output_dir, bvid_files[0])
                
                # 如果没有BV号或BV号匹配失败，使用标题匹配（备用方法）
                # 但即使通过标题匹配找到文件，也要检查分集是否完整
                if video_title and len(video_title) > 5:
                    title_key = video_title[:25].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '').replace(' ', '')
                    matched_files = []
                    for filename in existing_files:
                        filename_key = filename[:50].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '').replace(' ', '')
                        # 如果标题的关键部分在文件名中，收集匹配的文件
                        if title_key.lower() in filename_key.lower():
                            matched_files.append(filename)
                    
                    if matched_files:
                        # 检查这些匹配的文件是否有分集标识
                        episode_pattern = re.compile(r'p(\d+)', re.IGNORECASE)
                        episode_numbers = set()
                        complete_files = [f for f in matched_files 
                                        if not re.search(r'\.f\d+\.(mp4|m4a)$', f) 
                                        and not f.endswith('.m4a')]
                        
                        for filename in complete_files:
                            match = episode_pattern.search(filename)
                            if match:
                                episode_numbers.add(int(match.group(1)))
                        
                        if episode_numbers:
                            # 有分集标识，检查是否连续（从1开始）
                            max_episode = max(episode_numbers)
                            expected_episodes = set(range(1, max_episode + 1))
                            if episode_numbers == expected_episodes:
                                # 分集完整
                                return True, os.path.join(output_dir, complete_files[0])
                            else:
                                # 分集不完整，需要重新下载
                                missing = expected_episodes - episode_numbers
                                print(f"    检测到分集不完整，缺少: {sorted(missing)}")
                                return False, None
                        else:
                            # 没有分集标识，可能是单集视频，有文件就认为已下载
                            return True, os.path.join(output_dir, matched_files[0])
            
            # 检查yt-dlp是否可用
            try:
                result = subprocess.run(['python', '-m', 'yt_dlp', '--version'], 
                                      capture_output=True, 
                                      timeout=5)
                if result.returncode != 0:
                    result = subprocess.run(['yt-dlp', '--version'], 
                                          capture_output=True, 
                                          timeout=5)
                    if result.returncode != 0:
                        # 如果yt-dlp不可用，但目录中有文件，使用简单的文件名匹配
                        # 但即使通过标题匹配找到文件，也要检查分集是否完整
                        if video_title and os.path.exists(output_dir):
                            title_key = video_title[:20].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '')
                            matched_files = []
                            for filename in existing_files:
                                filename_key = filename[:40].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '')
                                if title_key.lower() in filename_key.lower():
                                    matched_files.append(filename)
                            
                            if matched_files:
                                # 检查分集是否完整
                                episode_pattern = re.compile(r'p(\d+)', re.IGNORECASE)
                                episode_numbers = set()
                                complete_files = [f for f in matched_files 
                                                if not re.search(r'\.f\d+\.(mp4|m4a)$', f) 
                                                and not f.endswith('.m4a')]
                                
                                for filename in complete_files:
                                    match = episode_pattern.search(filename)
                                    if match:
                                        episode_numbers.add(int(match.group(1)))
                                
                                if episode_numbers:
                                    max_episode = max(episode_numbers)
                                    expected_episodes = set(range(1, max_episode + 1))
                                    if episode_numbers == expected_episodes:
                                        return True, os.path.join(output_dir, complete_files[0])
                                    else:
                                        missing = expected_episodes - episode_numbers
                                        print(f"    检测到分集不完整，缺少: {sorted(missing)}")
                                        return False, None
                                else:
                                    return True, os.path.join(output_dir, matched_files[0])
                        return False, None
                    use_python_module = False
                else:
                    use_python_module = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # 如果yt-dlp不可用，但目录中有文件，使用简单的文件名匹配
                # 但即使通过标题匹配找到文件，也要检查分集是否完整
                if video_title and os.path.exists(output_dir):
                    title_key = video_title[:20].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '')
                    matched_files = []
                    for filename in existing_files:
                        filename_key = filename[:40].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '')
                        if title_key.lower() in filename_key.lower():
                            matched_files.append(filename)
                    
                    if matched_files:
                        # 检查分集是否完整
                        episode_pattern = re.compile(r'p(\d+)', re.IGNORECASE)
                        episode_numbers = set()
                        complete_files = [f for f in matched_files 
                                        if not re.search(r'\.f\d+\.(mp4|m4a)$', f) 
                                        and not f.endswith('.m4a')]
                        
                        for filename in complete_files:
                            match = episode_pattern.search(filename)
                            if match:
                                episode_numbers.add(int(match.group(1)))
                        
                        if episode_numbers:
                            max_episode = max(episode_numbers)
                            expected_episodes = set(range(1, max_episode + 1))
                            if episode_numbers == expected_episodes:
                                return True, os.path.join(output_dir, complete_files[0])
                            else:
                                missing = expected_episodes - episode_numbers
                                print(f"    检测到分集不完整，缺少: {sorted(missing)}")
                                return False, None
                        else:
                            return True, os.path.join(output_dir, matched_files[0])
                return False, None
            
            # 获取视频信息（不下载）
            if use_python_module:
                cmd = [
                    'python', '-m', 'yt_dlp',
                    '--dump-json',
                    '--no-warnings',
                    '--quiet',
                    video_url
                ]
            else:
                cmd = [
                    'yt-dlp',
                    '--dump-json',
                    '--no-warnings',
                    '--quiet',
                    video_url
                ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=30
            )
            
            stdout, stderr = result.stdout, result.stderr
            process_returncode = result.returncode
            
            if process_returncode == 0 and stdout:
                try:
                    video_info = json.loads(stdout)
                    title = video_info.get('title', video_title or '')
                    ext = video_info.get('ext', 'mp4')
                    video_bvid = video_info.get('id', '')  # 获取视频ID
                    
                    # 从URL中提取bvid作为备用
                    if not video_bvid:
                        bvid_match = re.search(r'BV[a-zA-Z0-9]+', video_url)
                        if bvid_match:
                            video_bvid = bvid_match.group(0)
                    
                    # 检查是否有多个分集（entries）
                    entries = video_info.get('entries', [])
                    if entries:
                        # 多分集视频，需要检查所有分集是否都存在
                        expected_count = len(entries)
                        if os.path.exists(output_dir):
                            # 统计目录中该BV号对应的完整文件数（排除中间文件）
                            bvid_files = [f for f in os.listdir(output_dir) 
                                        if os.path.isfile(os.path.join(output_dir, f))
                                        and video_bvid in f
                                        and f.endswith(('.mp4', '.mkv', '.webm', '.flv'))
                                        and not re.search(r'\.f\d+\.(mp4|m4a)$', f)
                                        and not f.endswith('.m4a')]
                            
                            if len(bvid_files) >= expected_count:
                                return True, os.path.join(output_dir, bvid_files[0])
                            else:
                                # 分集不完整，需要重新下载
                                return False, None
                    else:
                        # 单集视频，使用BV号精确匹配
                        if video_bvid and os.path.exists(output_dir):
                            for filename in os.listdir(output_dir):
                                file_path = os.path.join(output_dir, filename)
                                if os.path.isfile(file_path) and filename.endswith(('.mp4', '.m4a', '.webm', '.mkv', '.flv')):
                                    # 通过视频ID匹配（最准确）
                                    if video_bvid in filename and not re.search(r'\.f\d+\.(mp4|m4a)$', filename):
                                        return True, file_path
                        
                        # 如果BV号匹配失败，尝试标题匹配
                        safe_title = title
                        invalid_chars = '<>:"/\\|?*'
                        for char in invalid_chars:
                            safe_title = safe_title.replace(char, '_')
                        
                        expected_filename = f"{safe_title}.{ext}"
                        expected_path = os.path.join(output_dir, expected_filename)
                        
                        # 检查文件是否存在
                        if os.path.exists(expected_path) and os.path.getsize(expected_path) > 0:
                            return True, expected_path
                        
                        # 通过标题匹配（备用方法），但也要检查分集是否完整
                        if title and len(title) > 5 and os.path.exists(output_dir):
                            title_key = title[:25].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '').replace(' ', '')
                            matched_files = []
                            for filename in os.listdir(output_dir):
                                file_path = os.path.join(output_dir, filename)
                                if os.path.isfile(file_path) and filename.endswith(('.mp4', '.m4a', '.webm', '.mkv', '.flv')):
                                    filename_key = filename[:50].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '').replace(' ', '')
                                    if title_key.lower() in filename_key.lower():
                                        matched_files.append(filename)
                            
                            if matched_files:
                                # 检查分集是否完整
                                episode_pattern = re.compile(r'p(\d+)', re.IGNORECASE)
                                episode_numbers = set()
                                complete_files = [f for f in matched_files 
                                                if not re.search(r'\.f\d+\.(mp4|m4a)$', f) 
                                                and not f.endswith('.m4a')]
                                
                                for filename in complete_files:
                                    match = episode_pattern.search(filename)
                                    if match:
                                        episode_numbers.add(int(match.group(1)))
                                
                                if episode_numbers:
                                    max_episode = max(episode_numbers)
                                    expected_episodes = set(range(1, max_episode + 1))
                                    if episode_numbers == expected_episodes:
                                        return True, os.path.join(output_dir, complete_files[0])
                                    else:
                                        missing = expected_episodes - episode_numbers
                                        print(f"    检测到分集不完整，缺少: {sorted(missing)}")
                                        return False, None
                                else:
                                    return True, os.path.join(output_dir, matched_files[0])
                except (json.JSONDecodeError, KeyError) as e:
                    # 如果解析失败，尝试使用简单的文件名匹配，但也要检查分集是否完整
                    if video_title and os.path.exists(output_dir):
                        title_key = video_title[:20].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '')
                        matched_files = []
                        for filename in existing_files:
                            filename_key = filename[:40].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '')
                            if title_key.lower() in filename_key.lower():
                                matched_files.append(filename)
                        
                        if matched_files:
                            # 检查分集是否完整
                            episode_pattern = re.compile(r'p(\d+)', re.IGNORECASE)
                            episode_numbers = set()
                            complete_files = [f for f in matched_files 
                                            if not re.search(r'\.f\d+\.(mp4|m4a)$', f) 
                                            and not f.endswith('.m4a')]
                            
                            for filename in complete_files:
                                match = episode_pattern.search(filename)
                                if match:
                                    episode_numbers.add(int(match.group(1)))
                            
                            if episode_numbers:
                                max_episode = max(episode_numbers)
                                expected_episodes = set(range(1, max_episode + 1))
                                if episode_numbers == expected_episodes:
                                    return True, os.path.join(output_dir, complete_files[0])
                                else:
                                    missing = expected_episodes - episode_numbers
                                    print(f"    检测到分集不完整，缺少: {sorted(missing)}")
                                    return False, None
                            else:
                                return True, os.path.join(output_dir, matched_files[0])
                    pass
            
            return False, None
        except Exception as e:
            # 如果检查失败，尝试使用简单的文件名匹配
            if video_title and os.path.exists(output_dir):
                try:
                    fallback_files = [f for f in os.listdir(output_dir) 
                                    if os.path.isfile(os.path.join(output_dir, f)) 
                                    and f.endswith(('.mp4', '.mkv', '.webm', '.flv'))]
                    title_key = video_title[:20].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '')
                    for filename in fallback_files:
                        filename_key = filename[:40].replace(' ', '').replace('_', '').replace('-', '').replace('【', '').replace('】', '')
                        if title_key.lower() in filename_key.lower():
                            return True, os.path.join(output_dir, filename)
                except:
                    pass
            return False, None
    
    def merge_video_audio_files(self, output_dir):
        """合并目录中分开的视频和音频文件"""
        try:
            import subprocess
            
            if not os.path.exists(output_dir):
                return False
            
            # 查找所有mp4和m4a文件
            mp4_files = {}
            m4a_files = {}
            
            for filename in os.listdir(output_dir):
                file_path = os.path.join(output_dir, filename)
                if not os.path.isfile(file_path):
                    continue
                
                # 提取基础文件名（去掉扩展名和可能的流标识符）
                # 例如: "视频名.f100026.mp4" -> "视频名"
                base_name = filename
                # 移除扩展名
                if filename.endswith('.mp4'):
                    base_name = filename[:-4]
                    # 移除可能的流标识符（如 .f100026）
                    base_name = re.sub(r'\.f\d+$', '', base_name)
                    mp4_files[base_name] = file_path
                elif filename.endswith('.m4a'):
                    base_name = filename[:-4]
                    base_name = re.sub(r'\.f\d+$', '', base_name)
                    m4a_files[base_name] = file_path
            
            # 找到匹配的视频和音频文件对
            matched_pairs = []
            for base_name in mp4_files:
                if base_name in m4a_files:
                    matched_pairs.append({
                        'base_name': base_name,
                        'video': mp4_files[base_name],
                        'audio': m4a_files[base_name]
                    })
            
            if not matched_pairs:
                print("  未找到需要合并的视频和音频文件对")
                return False
            
            print(f"  找到 {len(matched_pairs)} 个需要合并的文件对:")
            for pair in matched_pairs:
                print(f"    - {pair['base_name']}")
            
            # 检查ffmpeg是否可用
            ffmpeg_available = False
            try:
                result = subprocess.run(['ffmpeg', '-version'], 
                                      capture_output=True, 
                                      timeout=5)
                if result.returncode == 0:
                    ffmpeg_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            if not ffmpeg_available:
                print("\n  错误: 未找到 ffmpeg，无法合并视频和音频文件")
                print("  请安装 ffmpeg:")
                print("    Windows: 下载 https://www.gyan.dev/ffmpeg/builds/ 或使用 chocolatey: choco install ffmpeg")
                print("    或使用 winget: winget install ffmpeg")
                print("    安装后请重启终端或重新运行脚本")
                return False
            
            merged_count = 0
            
            # 合并每个文件对
            for pair in matched_pairs:
                base_name = pair['base_name']
                video_path = pair['video']
                audio_path = pair['audio']
                
                # 生成合并后的文件名
                output_filename = f"{base_name}.mp4"
                output_path = os.path.join(output_dir, output_filename)
                
                # 如果合并后的文件已存在，跳过
                if os.path.exists(output_path):
                    print(f"  跳过 {base_name} (已存在合并后的文件)")
                    continue
                
                # 获取文件大小信息
                try:
                    video_size = os.path.getsize(video_path)
                    audio_size = os.path.getsize(audio_path)
                    total_size_mb = (video_size + audio_size) / (1024 * 1024)
                    print(f"  正在合并: {base_name}")
                    print(f"    视频文件: {video_size / (1024*1024):.2f} MB, 音频文件: {audio_size / (1024*1024):.2f} MB")
                except Exception as e:
                    print(f"  正在合并: {base_name}")
                    total_size_mb = 0
                
                # 根据文件大小动态计算超时时间
                # 每MB给2秒，最少300秒，最多3600秒（1小时）
                if total_size_mb > 0:
                    timeout_seconds = max(300, min(3600, int(total_size_mb * 2)))
                else:
                    timeout_seconds = 1800  # 默认30分钟
                
                print(f"    预计耗时: 最多 {timeout_seconds // 60} 分钟")
                
                # 使用ffmpeg合并
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-i', audio_path,
                    '-c:v', 'copy',  # 视频流直接复制，不重新编码
                    '-c:a', 'aac',   # 音频编码为aac
                    '-y',            # 覆盖输出文件
                    '-loglevel', 'error',  # 只显示错误信息
                    output_path
                ]
                
                try:
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=timeout_seconds
                    )
                    
                    if result.returncode == 0 and os.path.exists(output_path):
                        # 检查输出文件大小，确保合并成功
                        output_size = os.path.getsize(output_path)
                        video_size = os.path.getsize(video_path)
                        if output_size > video_size:  # 合并后的文件应该比单独的视频文件大
                            # 合并成功，删除原始文件
                            try:
                                os.remove(video_path)
                                os.remove(audio_path)
                                print(f"    [成功] 已合并并删除原始文件")
                                merged_count += 1
                            except Exception as e:
                                print(f"    [警告] 合并成功但删除原始文件失败: {e}")
                        else:
                            print(f"    [失败] 合并后的文件大小异常")
                            try:
                                os.remove(output_path)
                            except:
                                pass
                    else:
                        error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else '未知错误'
                        print(f"    [失败] 合并失败: {error_msg[:100]}")
                        if os.path.exists(output_path):
                            try:
                                os.remove(output_path)
                            except:
                                pass
                except subprocess.TimeoutExpired:
                    print(f"    [超时] 合并操作超时（{timeout_seconds // 60} 分钟）")
                    print(f"    提示: 文件较大，合并需要更长时间。您可以:")
                    print(f"      1. 手动运行以下命令合并:")
                    print(f"         ffmpeg -i \"{video_path}\" -i \"{audio_path}\" -c:v copy -c:a aac -y \"{output_path}\"")
                    print(f"      2. 或者重新运行脚本，脚本会跳过已存在的文件并继续处理其他文件")
                except Exception as e:
                    print(f"    [错误] 合并过程出错: {e}")
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except:
                            pass
            
            if merged_count > 0:
                print(f"\n  共成功合并了 {merged_count} 个视频文件")
            else:
                print(f"\n  没有成功合并任何文件")
            
            return merged_count > 0
        except Exception as e:
            print(f"  合并文件时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def download_video_with_ytdlp(self, video_url, output_dir, index=None):
        """使用yt-dlp下载视频（推荐方法）"""
        try:
            import subprocess
            # 尝试使用 python -m yt_dlp，这样更可靠
            result = subprocess.run(['python', '-m', 'yt_dlp', '--version'], 
                                  capture_output=True, 
                                  timeout=5)
            if result.returncode != 0:
                # 如果python -m失败，尝试直接调用yt-dlp
                result = subprocess.run(['yt-dlp', '--version'], 
                                      capture_output=True, 
                                      timeout=5)
                if result.returncode != 0:
                    return False
                use_python_module = False
            else:
                use_python_module = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("  yt-dlp未安装，请先安装: pip install yt-dlp")
            return False
        
        try:
            # 构建输出文件名
            if index is not None:
                output_template = os.path.join(output_dir, f"%(title)s.%(ext)s")
            else:
                output_template = os.path.join(output_dir, f"%(title)s.%(ext)s")
            
            # 添加合并选项：自动合并视频和音频为mp4格式
            # 如果视频和音频分开，yt-dlp会自动下载并合并
            if use_python_module:
                cmd = [
                    'python', '-m', 'yt_dlp',
                    '-o', output_template,
                    '--merge-output-format', 'mp4',  # 合并为mp4格式
                    '--no-warnings',
                    '--quiet',
                    video_url
                ]
            else:
                cmd = [
                    'yt-dlp',
                    '-o', output_template,
                    '--merge-output-format', 'mp4',  # 合并为mp4格式
                    '--no-warnings',
                    '--quiet',
                    video_url
                ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                return True
            else:
                print(f"  yt-dlp错误: {stderr[:200]}")
                return False
        except Exception as e:
            print(f"  yt-dlp执行失败: {e}")
            return False
    
    def download_collection(self, collection_url, output_dir="downloads"):
        """主函数：下载合集"""
        print(f"开始处理URL: {collection_url}")
        print("=" * 60)
        
        # 0. 判断是单个视频URL还是合集URL
        original_url = collection_url
        bvid = self.extract_bvid_from_url(collection_url)
        collection_id = self.extract_collection_id(collection_url)
        mid = None
        html_content = None
        
        if bvid and not collection_id:
            # 这是单个视频URL，需要先获取合集信息
            print("\n[0/5] 检测到单个视频URL，正在获取合集信息...")
            collection_info = self.get_collection_info_from_video_page(collection_url)
            if collection_info:
                mid = collection_info.get('mid')
                collection_id = collection_info.get('season_id')
                collection_url = collection_info.get('collection_url', collection_url)
                print(f"  找到合集信息:")
                print(f"  用户ID: {mid}")
                print(f"  合集ID: {collection_id}")
                print(f"  合集URL: {collection_url}")
            else:
                print("  无法从视频页面获取合集信息")
                print("  提示: 该视频可能不属于任何合集，或需要登录才能查看")
                return
        else:
            # 这是合集URL
            print("\n[1/5] 下载合集页面...")
            page_path, html_content = self.download_page(collection_url)
            if not html_content:
                print("无法下载页面")
                return
            
            # 提取合集ID
            print("\n[2/5] 提取合集信息...")
            if collection_id:
                print(f"合集ID: {collection_id}")
            
            # 从URL中提取mid（用户ID）
            mid_match = re.search(r'/space\.bilibili\.com/(\d+)', collection_url)
            mid = mid_match.group(1) if mid_match else None
            if mid:
                print(f"用户ID: {mid}")
        
        # 3. 获取视频URL列表
        is_single_video = bvid and not self.extract_collection_id(original_url)
        print("\n[3/5] 获取视频列表...")
        video_urls = []
        video_info_list = []
        
        # 方法1: 尝试从API获取
        if collection_id:
            print("  尝试通过API获取视频列表...")
            api_urls, api_info = self.extract_video_urls_from_api(collection_id, mid)
            if api_urls:
                video_urls = api_urls
                video_info_list = api_info
                print(f"  从API获取到 {len(video_urls)} 个视频")
        
        # 方法2: 从HTML中提取（仅当有HTML内容时）
        if not video_urls and html_content:
            print("  从HTML中提取视频URL...")
            html_urls = self.extract_video_urls_from_html(html_content)
            if html_urls:
                video_urls = html_urls
                print(f"  从HTML提取到 {len(video_urls)} 个视频")
        
        if not video_urls:
            print("  无法获取视频列表")
            print("  提示: bilibili合集数据可能需要登录或使用其他API")
            print("  已保存页面HTML，请手动检查: bilibili_collection_page.html")
            return
        
        # 显示视频列表
        print(f"\n找到 {len(video_urls)} 个视频:")
        for i, info in enumerate(video_info_list if video_info_list else [{'url': url, 'title': ''} for url in video_urls], 1):
            title = info.get('title', '')
            url = info.get('url', video_urls[i-1] if i <= len(video_urls) else '')
            if title:
                print(f"  {i}. {title}")
                print(f"     {url}")
            else:
                print(f"  {i}. {url}")
        
        # 4. 创建输出目录
        safe_dir_name = f"bilibili_collection_{collection_id or 'unknown'}"
        output_path = os.path.join(output_dir, safe_dir_name)
        os.makedirs(output_path, exist_ok=True)
        
        # 5. 下载视频
        print(f"\n[4/5] 开始下载视频到: {output_path}")
        print("=" * 60)
        
        success_count = 0
        fail_count = 0
        
        for i, video_url in enumerate(video_urls, 1):
            video_info = video_info_list[i-1] if i <= len(video_info_list) else {}
            title = video_info.get('title', '')
            
            if title:
                print(f"\n[{i}/{len(video_urls)}] {title}")
            else:
                print(f"\n[{i}/{len(video_urls)}] 处理视频")
            print(f"  URL: {video_url}")
            
            # 检查是否已经下载
            is_downloaded, existing_file = self.check_video_downloaded(video_url, output_path, video_title=title)
            if is_downloaded:
                print(f"  [跳过] 文件已存在: {os.path.basename(existing_file)}")
                success_count += 1
                continue
            
            if self.download_video_with_ytdlp(video_url, output_path, index=i):
                print(f"  [成功] 下载成功")
                success_count += 1
            else:
                print(f"  [失败] 下载失败")
                fail_count += 1
            
            # 避免请求过快
            time.sleep(2)
        
        # 6. 合并分开的视频和音频文件
        print(f"\n[5/5] 检查并合并分开的视频和音频文件...")
        self.merge_video_audio_files(output_path)
        
        print(f"\n{'='*60}")
        print(f"下载完成!")
        print(f"成功: {success_count}, 失败: {fail_count}")
        print(f"输出目录: {output_path}")
        print(f"{'='*60}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python download_bilibili_collection.py <bilibili合集URL> [输出目录]")
        print("\n示例:")
        print("  python download_bilibili_collection.py https://space.bilibili.com/4520265/lists/3308869?type=season")
        sys.exit(1)
    
    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "downloads"
    
    downloader = BilibiliCollectionDownloader()
    downloader.download_collection(url, output_dir)


if __name__ == "__main__":
    main()
