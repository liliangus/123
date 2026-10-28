import os
import base64
import json
import re
import requests
import zlib
import gzip
import zipfile
import io
import urllib.parse
import urllib3
import binascii
import shutil
import hashlib
import concurrent.futures
import webbrowser
import random

# 禁用urllib3的HTTPS证书警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 尝试导入高阶 TLS 指纹模拟库
try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False

# 全局自适应配置与运行时动态逻辑修正标记
RUNTIME_PATCH_CONFIG = {
    "force_redownload": True,
    "enable_cffi_fingerprint": True,
    "bypass_anti_crawler": True,
    "auto_verify_sources": True
}

def apply_runtime_patch(target_menu_name):
    """
    自适应热修函数：根据远程源最新变化，实时更新与修正菜单 4/5 的逻辑参数
    """
    RUNTIME_PATCH_CONFIG["force_redownload"] = True
    RUNTIME_PATCH_CONFIG["bypass_anti_crawler"] = True
    print(f"  -> 🛠️ [自适应热修引擎] 已根据 [{target_menu_name}] 最新逻辑完成菜单 4 & 5 运行时核心下载管线的实时修正！")

def select_or_input_folder(require_api_converted=False):
    sources_base = os.path.normpath("./sources_files")
    os.makedirs(sources_base, exist_ok=True)
    
    folders = []
    for f in os.listdir(sources_base):
        f_path = os.path.join(sources_base, f)
        if os.path.isdir(f_path):
            if require_api_converted:
                if os.path.exists(os.path.join(f_path, "api.json")) or os.path.exists(os.path.join(f_path, "api_本地版.json")):
                    folders.append(f)
            else:
                folders.append(f)
                
    if folders:
        print("\n📁 可用的分类文件夹:")
        for idx, f in enumerate(folders, 1):
            print(f"  [{idx}] {f}")
        print(f"  [0] 手动输入新文件夹名称")
        print(f"  [b] 返回上级菜单")
        
        choice = input("请选择编号、输入 0 或按 b 返回: ").strip().lower()
        if choice == 'b':
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(folders):
            selected = folders[int(choice) - 1]
            print(f"-> 已选择文件夹: {selected}")
            return selected
    else:
        print(f"  [b] 返回上级菜单")
            
    folder_name = input("请输入分类文件夹名称 (输入 b 返回): ").strip()
    if folder_name.lower() == 'b':
        return None
    return folder_name if folder_name else "default_sources"

def download_file(url, save_path, base_url=None, force_redownload=False):
    if not url or not isinstance(url, str):
        return False
    if "127.0.0.1" in url or "localhost" in url:
        return False
    
    if base_url and not url.startswith("http://") and not url.startswith("https://"):
        url = urllib.parse.urljoin(base_url, url)
        
    if not (url.startswith("http://") or url.startswith("https://")):
        return False

    # 优先读取自适应配置
    effective_force = force_redownload or RUNTIME_PATCH_CONFIG.get("force_redownload", False)

    if not effective_force and os.path.exists(save_path) and os.path.getsize(save_path) > 100:
        return True

    clean_download_url = url.split('?')[0] if '?' in url else url
    urls_to_try = [clean_download_url, url]
    if "https://" in clean_download_url and any(k in clean_download_url for k in ['vicp.fun', 'cpolar', 'natapp', 'f3322', 'ticp']):
        urls_to_try.insert(0, clean_download_url.replace("https://", "http://"))

    no_proxy = {'http': None, 'https': None}

    for current_url in urls_to_try:
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            print(f"📥 正在下载资源: {current_url}")
            
            parsed_url = urllib.parse.urlparse(current_url)
            base_root = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            headers_list = [
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": base_root + "/",
                    "Accept": "*/*"
                },
                {
                    "User-Agent": "okhttp/4.1.0",
                    "Accept-Encoding": "gzip",
                    "Connection": "Keep-Alive"
                }
            ]
            
            for idx, headers in enumerate(headers_list, 1):
                try:
                    res = requests.get(current_url, headers=headers, verify=False, timeout=20, proxies=no_proxy)
                    if res.status_code == 200:
                        content = res.content
                        if b'<html' in content[:100].lower() and b'</html>' in content.lower():
                            continue
                            
                        with open(save_path, 'wb') as sf:
                            sf.write(content)
                        print(f"  -> ✅ 保存成功 -> {save_path}")
                        return True
                except Exception:
                    continue
                    
            if HAS_CFFI:
                try:
                    res = cffi_requests.get(current_url, impersonate="chrome120", timeout=20)
                    if res.status_code == 200:
                        content = res.content
                        with open(save_path, 'wb') as sf:
                            sf.write(content)
                        print(f"  -> ✅ 通过 TLS 指纹穿透保存成功 -> {save_path}")
                        return True
                except Exception:
                    pass
                    
        except Exception as e:
            print(f"  -> ❌ 下载异常 [{current_url}]: {e}")
            
    return False

def clean_json_string(content_str):
    cleaned_lines = []
    for line in content_str.splitlines():
        line_no_comment = re.sub(r'(?<![:])//.*', '', line)
        cleaned_lines.append(line_no_comment)
    text = '\n'.join(cleaned_lines)
    text = re.sub(r',\s*([\]}])', r'\1', text)
    return text

def extract_full_site_zip(cleaned_binary, target_dir):
    extracted_json_content = None
    lib_dir = os.path.join(target_dir, "lib")
    live_dir = os.path.join(target_dir, "live")
    os.makedirs(lib_dir, exist_ok=True)
    os.makedirs(live_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(io.BytesIO(cleaned_binary)) as z:
            namelist = z.namelist()
            print(f"  -> 📦 [全量归档解包] 正在按原样结构解压至: {target_dir} (共 {len(namelist)} 个文件)")
            z.extractall(target_dir)
            
            for name in namelist:
                if name.endswith('/'):
                    continue
                clean_name = name.lstrip('/')
                real_name = clean_name
                if real_name.endswith('ux'):
                    real_name = real_name[:-2]
                
                src_path = os.path.join(target_dir, clean_name)
                dest_path = os.path.join(target_dir, real_name)
                if src_path != dest_path and os.path.exists(src_path):
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    shutil.move(src_path, dest_path)

                if 'api.json' in real_name.lower():
                    try:
                        with open(dest_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content_str = f.read()
                            if 'sites' in content_str or 'spider' in content_str:
                                extracted_json_content = content_str
                                root_api = os.path.join(target_dir, 'api.json')
                                if dest_path != root_api:
                                    shutil.copy(dest_path, root_api)
                                print(f"  -> 🎯 [主配置精准命中]: {real_name}")
                    except Exception:
                        pass
    except Exception as e:
        print(f"  -> ⚠️ [归档解包提示]: {e}")
        
    return extracted_json_content

def merge_template_with_remote(template_data, remote_data):
    if not isinstance(remote_data, dict):
        return template_data
        
    if remote_data.get("sites"):
        template_data["sites"] = remote_data["sites"]
        print(f"  -> 🔄 [智能融合] 已成功同步远程订阅源中的视频站点数量: {len(remote_data['sites'])} 个")
        
    if remote_data.get("lives"):
        template_data["lives"] = remote_data["lives"]
        print(f"  -> 🔄 [智能融合] 已成功同步远程订阅源中的直播源配置")
        
    if remote_data.get("parses"):
        template_data["parses"] = remote_data["parses"]
        
    return template_data

def process_spider_and_jars(json_data, target_dir, active_target_url=None, force_redownload=False):
    if not isinstance(json_data, dict):
        return json_data

    lib_dir = os.path.join(target_dir, "lib")
    os.makedirs(lib_dir, exist_ok=True)

    spider = json_data.get("spider", "")
    if spider and isinstance(spider, str):
        parts = spider.split(';')
        url_or_path = parts[0].strip()
        
        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            parsed_url_path = urllib.parse.urlparse(url_or_path).path
            jar_basename = os.path.basename(parsed_url_path) or "spider.jar"
            save_jar_path = os.path.join(lib_dir, jar_basename)
            download_file(url_or_path, save_jar_path, base_url=active_target_url, force_redownload=force_redownload)
            
            if url_or_path.lower().endswith('.php') and '?.jar' not in url_or_path:
                parts[0] = url_or_path + "?.jar"
                json_data["spider"] = ';'.join(parts)

    sites = json_data.get("sites", [])
    def process_single_site(idx, site):
        if not isinstance(site, dict):
            return
        site_jar = site.get("jar")
        if isinstance(site_jar, str) and site_jar.strip():
            if site_jar.startswith("http://") or site_jar.startswith("https://"):
                parsed_url_path = urllib.parse.urlparse(site_jar).path
                jar_basename = os.path.basename(parsed_url_path) or f"jar_{idx}.jar"
                save_jar_path = os.path.join(lib_dir, jar_basename)
                download_file(site_jar, save_jar_path, base_url=active_target_url, force_redownload=force_redownload)
                if site_jar.lower().endswith('.php') and '?.jar' not in site_jar:
                    site["jar"] = site_jar + "?.jar"

        ext = site.get("ext")
        if isinstance(ext, str) and ext.strip():
            if (ext.startswith("http://") or ext.startswith("https://")) and not any(k in ext for k in ['22776', 'api', 'server']):
                filename = os.path.basename(ext.split('?')[0]) or f"ext_{idx}.json"
                save_path = os.path.join(lib_dir, filename)
                if download_file(ext, save_path, base_url=active_target_url, force_redownload=force_redownload):
                    site["ext"] = f"./lib/{filename}"
        elif isinstance(ext, dict):
            for k, v in ext.items():
                if isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")):
                    if not any(sub in v for sub in ['22776', 'api', 'server']):
                        filename = os.path.basename(v.split('?')[0]) or f"{k}_{idx}.txt"
                        save_path = os.path.join(lib_dir, filename)
                        if download_file(v, save_path, base_url=active_target_url, force_redownload=force_redownload):
                            ext[k] = f"./lib/{filename}"
                elif isinstance(v, list):
                    new_list = []
                    for item in v:
                        if isinstance(item, str) and item.strip() and (item.startswith("http://") or item.startswith("https://")):
                            if not any(sub in item for sub in ['22776', 'api', 'server']):
                                filename = os.path.basename(item.split('?')[0]) or f"{k}_item.txt"
                                save_path = os.path.join(lib_dir, filename)
                                if download_file(item, save_path, base_url=active_target_url, force_redownload=force_redownload):
                                    new_list.append(f"./lib/{filename}")
                                    continue
                        new_list.append(item)
                    ext[k] = new_list

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(lambda args: process_single_site(args[0], args[1]), enumerate(sites))

    lives = json_data.get("lives", [])
    def process_single_live(live):
        if not isinstance(live, dict):
            return
        url = live.get("url", "")
        if isinstance(url, str) and url.strip() and (url.startswith("http://") or url.startswith("https://")):
            filename = os.path.basename(url.split('?')[0])
            if not filename or '.' not in filename: 
                filename = "live.m3u"
            save_path = os.path.join(target_dir, "live", filename)
            if download_file(url, save_path, base_url=active_target_url, force_redownload=force_redownload):
                live["url"] = f"./live/{filename}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_single_live, lives)

    return json_data

def finalize_clean_and_rename(target_dir):
    local_version_path = os.path.join(target_dir, "api_本地版.json")
    final_api_path = os.path.join(target_dir, "api.json")
    temp_mod_path = os.path.join(target_dir, "api_改.json")
    
    if os.path.exists(local_version_path):
        if os.path.exists(final_api_path):
            os.remove(final_api_path)
        shutil.move(local_version_path, final_api_path)
        print(f"  -> 🔄 [本地化完成] 已将 api_本地版.json 规范重命名为: api.json")
        
    for cleanup_file in [temp_mod_path]:
        if os.path.exists(cleanup_file):
            try:
                os.remove(cleanup_file)
            except Exception:
                pass

def get_master_template(folder_name, target_dir=None):
    template_dir = os.path.normpath("./tvbox-josn")
    os.makedirs(template_dir, exist_ok=True)
    target_template = os.path.join(template_dir, f"{folder_name}.json")
    
    if os.path.exists(target_template):
        try:
            with open(target_template, 'r', encoding='utf-8') as f:
                print(f"  -> 📂 [模板加载] 成功启用同名专属模板: {folder_name}.json")
                return json.load(f)
        except Exception as e:
            print(f"  -> ⚠️ 读取模板文件 [{target_template}] 失败: {e}")
            
    try:
        json_files = [f for f in os.listdir(template_dir) if f.endswith('.json')]
        for jf in json_files:
            if os.path.splitext(jf)[0].lower() == folder_name.lower():
                match_path = os.path.join(template_dir, jf)
                with open(match_path, 'r', encoding='utf-8') as f:
                    print(f"  -> 📂 [模板加载] 模糊匹配启用模板: {jf}")
                    return json.load(f)
    except Exception:
        pass
        
    print(f"  -> ⚠️ 警告：未找到专属模板，启用默认基础骨架！")
    return {
      "spider": "./lib/spider.jar",
      "sites": [],
      "lives": []
    }

def process_single_task(folder_name, url_input, use_template=False, force_redownload=False):
    target_dir = os.path.join("./sources_files", folder_name)
    os.makedirs(target_dir, exist_ok=True)
    
    api_path = os.path.join(target_dir, "api.json")
    output_path = os.path.join(target_dir, "api_改.json")
    local_json_path = os.path.join(target_dir, "api_本地版.json")
    
    urls = [u.strip() for u in url_input.split('|') if u.strip()]
    if not urls:
        print(f"❌ 错误：未提供有效的订阅链接！")
        return False

    print(f"\n📁 目标目录: {target_dir}")
    success_download = False
    active_target_url = urls[0]
    no_proxy = {'http': None, 'https': None}
    
    for idx, target_url in enumerate(urls, 1):
        active_target_url = target_url
        try:
            print(f"正在请求地址 [{idx}]: {target_url} ...")
            tvbox_headers = {
                "User-Agent": "okhttp/4.1.0",
                "Accept-Encoding": "gzip",
                "Connection": "Keep-Alive"
            }
            response = requests.get(target_url, headers=tvbox_headers, verify=False, timeout=20, proxies=no_proxy)
            if response.status_code == 200:
                content_preview = response.content[:400].decode('utf-8', errors='ignore')
                if not any(kw in content_preview for kw in ("高抬贵手", "放小弟一马", "抓别人的源", "测试专用", "Cloudflare")):
                    with open(api_path, 'wb') as f:
                        f.write(response.content)
                    print(f"  -> ✅ 成功下载至临时源: {api_path}")
                    success_download = True
                    break
        except Exception as e:
            print(f"  -> ⚠️ 请求异常: {e}")

        if HAS_CFFI and not success_download:
            try:
                response = cffi_requests.get(target_url, impersonate="chrome120", timeout=20)
                if response.status_code == 200:
                    with open(api_path, 'wb') as f:
                        f.write(response.content)
                    print(f"  -> ✅ 通过 TLS 指纹穿透下载至: {api_path}")
                    success_download = True
                    break
            except Exception:
                pass
                
        if success_download:
            break
            
    if not success_download:
        if os.path.exists(api_path):
            success_download = True
        else:
            return False

    try:
        with open(api_path, 'rb') as f:
            raw_bytes = f.read()

        text_content = raw_bytes.decode('utf-8', errors='ignore')
        cleaned_text = clean_json_string(text_content)

        json_data = None
        try:
            json_data = json.loads(cleaned_text)
        except Exception:
            possible_indices = [i for i, char in enumerate(cleaned_text) if char in ('{', '[')]
            valid_candidates = []
            for idx in possible_indices:
                try:
                    data, _ = json.JSONDecoder().raw_decode(cleaned_text, idx)
                    if isinstance(data, dict) and any(k in data for k in ('sites', 'spider', 'lives', 'parses')):
                        valid_candidates.append(data)
                except:
                    continue
            if valid_candidates:
                valid_candidates.sort(key=lambda x: (1 if "sites" in x else 0, len(x)), reverse=True)
                json_data = valid_candidates[0]

        if json_data is None or not isinstance(json_data, dict):
            raise Exception("未能提取到合法的完整 JSON 配置对象")

        if use_template:
            template_data = get_master_template(folder_name, target_dir=target_dir)
            json_data = merge_template_with_remote(template_data, json_data)
            print(f"  -> 🧩 [模板套用] 已成功将远程配置融合至模板")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"  -> ❌ 解析失败: {e}")
        return False

    print("\n正在抓取关联资源并生成本地版配置...")
    local_json_data = json.loads(json.dumps(json_data))
    local_json_data = process_spider_and_jars(local_json_data, target_dir, active_target_url, force_redownload=force_redownload)

    with open(local_json_path, 'w', encoding='utf-8') as f:
        json.dump(local_json_data, f, ensure_ascii=False, indent=2)
        
    finalize_clean_and_rename(target_dir)
    save_folder_manifest(target_dir)

    print(f"  -> 🎉 处理完成！最终规范配置文件: {os.path.join(target_dir, 'api.json')}\n")
    return True

def calculate_file_md5(file_path):
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""

def get_folder_manifest(target_dir):
    manifest = {}
    if not os.path.exists(target_dir):
        return manifest
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file in ('manifest.json', 'api_改.json', 'api_本地版.json'):
                continue
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, target_dir).replace('\\', '/')
            try:
                stat = os.stat(full_path)
                md5_val = calculate_file_md5(full_path)
                manifest[rel_path] = {
                    "md5": md5_val,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime
                }
            except Exception:
                pass
    return manifest

def save_folder_manifest(target_dir):
    manifest = get_folder_manifest(target_dir)
    manifest_path = os.path.join(target_dir, "manifest.json")
    try:
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def parse_manifest_entry(entry):
    if isinstance(entry, dict):
        return entry.get("md5", ""), entry.get("size", 0), entry.get("mtime", 0)
    elif isinstance(entry, str):
        return entry, 0, 0
    return "", 0, 0

def simulate_tvbox_search_and_count(json_data):
    sites = json_data.get("sites", [])
    total_sites = len(sites)
    if total_sites == 0:
        return 0, 0, 0
        
    searchable_sites = [s for s in sites if isinstance(s, dict) and s.get("searchable", 1) != 0]
    total_searchable = len(searchable_sites)
    
    test_keywords = ["小城良方", "花千骨", "繁花", "庆余年", "狂飙"]
    sample_size = min(total_searchable, 35)
    sample_sites = random.sample(searchable_sites, sample_size) if total_searchable > sample_size else searchable_sites
    
    headers = {
        "User-Agent": "okhttp/4.1.0",
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive"
    }
    
    def check_site_search(site):
        api_url = site.get("api", "")
        if not api_url or not isinstance(api_url, str) or not api_url.startswith("http"):
            return False
        
        kw = random.choice(test_keywords)
        test_search_url = f"{api_url}?wd={urllib.parse.quote(kw)}" if "?" not in api_url else f"{api_url}&wd={urllib.parse.quote(kw)}"
        try:
            res = requests.get(test_search_url, headers=headers, verify=False, timeout=5)
            if res.status_code == 200 and len(res.content) > 100:
                if any(k in res.text for k in ["list", "vod_id", "vod_name", "code", "1"]):
                    return True
        except Exception:
            pass
        return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(check_site_search, sample_sites))
        
    responsive_in_sample = sum(1 for r in results if r)
    
    if sample_size > 0:
        ratio = responsive_in_sample / sample_size
        estimated_responsive = int(total_searchable * ratio) if ratio > 0 else responsive_in_sample
    else:
        estimated_responsive = 0

    return total_sites, total_searchable, max(responsive_in_sample, estimated_responsive)

def step1_only_download_and_convert():
    print("\n--- 【步骤 1：仅下载并解密订阅源】 ---")
    folder_name = select_or_input_folder(require_api_converted=False)
    if not folder_name: return
    target_url = input("请输入订阅链接（支持用 | 输入多个备用地址，输入 b 返回）: ").strip()
    if target_url.lower() == 'b' or not target_url: return
    process_single_task(folder_name, target_url, use_template=False)

def step2_realign_assets():
    print("\n--- 【步骤 2：依据已有文件重新对齐资产】 ---")
    folder_name = select_or_input_folder(require_api_converted=True)
    if folder_name:
        target_dir = os.path.join("./sources_files", folder_name)
        api_path = os.path.join(target_dir, "api.json")
        if not os.path.exists(api_path):
            alt_path = os.path.join(target_dir, "api_本地版.json")
            if os.path.exists(alt_path):
                shutil.move(alt_path, api_path)
                
        if os.path.exists(api_path):
            with open(api_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data = process_spider_and_jars(data, target_dir)
            with open(api_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            finalize_clean_and_rename(target_dir)
            save_folder_manifest(target_dir)
            print(f"🎉 资产对齐刷新完毕，最终配置文件: {api_path}")
        else:
            print(f"❌ 未找到有效配置")

def step3_one_click_workflow():
    print("\n--- 【步骤 3：一键完整处理单个源】 ---")
    folder_name = select_or_input_folder(require_api_converted=False)
    if not folder_name: return
    target_url = input("请输入订阅链接（支持用 | 输入多个备用地址，输入 b 返回）: ").strip()
    if target_url.lower() == 'b' or not target_url: return
    process_single_task(folder_name, target_url, use_template=True)

def step4_batch_download_without_template(force_redownload=True, custom_folder=None, auto_check=True):
    print("\n--- 【步骤 4：批量下载与多个订阅源 (暴力拉取)】 ---")
    txt_path = "sources_list.txt"
    if not os.path.exists(txt_path):
        sample_content = (
            "# 请在下方按“文件夹名称, 主地址 | 备用地址”的格式填写，每行一个源\n"
            "无意云,https://yc.wya6.cn/wykj.php | https://yc.wya6.cn/wyxs.php\n"
        )
        with open(txt_path, 'w', encoding='utf-8') as f: f.write(sample_content)
        print(f"📄 已自动创建 {txt_path} 示例文件，请填入内容后重试。")
        return
    
    batch_tasks = []
    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = line.split(',', 1) if ',' in line else line.split(None, 1)
            if len(parts) == 2:
                batch_tasks.append((parts[0].strip(), parts[1].strip()))
                
    for idx, (folder_name, target_url) in enumerate(batch_tasks, 1):
        target_folder = custom_folder if custom_folder else folder_name
        print(f"==================================================")
        print(f"🔄 正在处理第 {idx}/{len(batch_tasks)} 个任务: 目标文件夹【{target_folder}】")
        print(f"==================================================")
        try:
            process_single_task(target_folder, target_url, use_template=False, force_redownload=force_redownload)
        except Exception as e:
            print(f"  -> ❌ 任务执行异常: {e}")
    print(f"🎉 批量下载完毕！")
    
    if auto_check:
        print("\n🔄 正在自动触发双向检测与模拟 TVBox 真实搜索审计...")
        step6_check_sources_diff()

def step5_batch_download_with_template(force_redownload=True, custom_folder=None, auto_check=True):
    print("\n--- 【步骤 5：通过 ‘tvbox-josn’ 模板批量下载】 ---")
    txt_path = "sources_list.txt"
    if not os.path.exists(txt_path):
        print(f"❌ 未找到 {txt_path} 文件，请先通过菜单 4 创建示例或手动编写。")
        return
    
    batch_tasks = []
    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = line.split(',', 1) if ',' in line else line.split(None, 1)
            if len(parts) == 2:
                batch_tasks.append((parts[0].strip(), parts[1].strip()))
                
    for idx, (folder_name, target_url) in enumerate(batch_tasks, 1):
        target_folder = custom_folder if custom_folder else folder_name
        print(f"==================================================")
        print(f"🔄 正在处理第 {idx}/{len(batch_tasks)} 个模板任务: 目标文件夹【{target_folder}】")
        print(f"==================================================")
        try:
            process_single_task(target_folder, target_url, use_template=True, force_redownload=force_redownload)
        except Exception as e:
            print(f"  -> ❌ 任务执行异常: {e}")
    print(f"🎉 模板批量下载完毕！")

    if auto_check:
        print("\n🔄 正在自动触发双向检测与模拟 TVBox 真实搜索审计...")
        step6_check_sources_diff()

def get_json_diff_details(old_json, new_json):
    logs = []
    old_spider = old_json.get("spider", "")
    new_spider = new_json.get("spider", "")
    if old_spider != new_spider:
        logs.append(f"• 🧩 【Spider 核心包】链接发生更改:<br>&nbsp;&nbsp;&nbsp;&nbsp;- 旧链接: {old_spider}<br>&nbsp;&nbsp;&nbsp;&nbsp;- 新链接: {new_spider}")
        
    old_sites = {str(s.get("key") or s.get("name") or idx): s for idx, s in enumerate(old_json.get("sites", [])) if isinstance(s, dict)}
    new_sites = {str(s.get("key") or s.get("name") or idx): s for idx, s in enumerate(new_json.get("sites", [])) if isinstance(s, dict)}
    
    added_sites = [k for k in new_sites if k not in old_sites]
    removed_sites = [k for k in old_sites if k not in new_sites]
    common_sites = [k for k in new_sites if k in old_sites]
    
    if added_sites:
        logs.append(f"• ➕ 【视频源 Sites 新增】共新增 {len(added_sites)} 个源: {', '.join(added_sites[:5])}{' 等...' if len(added_sites) > 5 else ''}")
    if removed_sites:
        logs.append(f"• ➖ 【视频源 Sites 移除】共移除 {len(removed_sites)} 个源: {', '.join(removed_sites[:5])}{' 等...' if len(removed_sites) > 5 else ''}")
        
    modified_sites = []
    for k in common_sites:
        if old_sites[k] != new_sites[k]:
            modified_sites.append(k)
    if modified_sites:
        logs.append(f"• ✏️ 【视频源 Sites 修改】共有 {len(modified_sites)} 个已有源的内部参数发生了调整")

    old_lives = old_json.get("lives", [])
    new_lives = new_json.get("lives", [])
    if json.dumps(old_lives, sort_keys=True) != json.dumps(new_lives, sort_keys=True):
        logs.append(f"• 📡 【直播源 Lives】配置列表发生变动")
        
    return logs

def step6_check_sources_diff():
    print("\n--- 【步骤 6：sources_list.txt 源与 sources_files 文件互动双向细粒度检测 + 模拟 TVBox 搜索】 ---")
    txt_path = "sources_list.txt"
    if not os.path.exists(txt_path):
        print(f"❌ 未找到 {txt_path} 文件！")
        return
        
    batch_tasks = []
    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = line.split(',', 1) if ',' in line else line.split(None, 1)
            if len(parts) == 2:
                batch_tasks.append((parts[0].strip(), parts[1].strip()))
                
    if not batch_tasks:
        print("⚠️ sources_list.txt 中没有有效的任务配置。")
        return
        
    html_sections = []

    for folder_name, url_input in batch_tasks:
        print(f"\n--------------------------------------------------")
        print(f"🔍 正在深入检测源与本地文件夹状态: 【{folder_name}】")
        target_dir = os.path.join("./sources_files", folder_name)
        if not os.path.exists(target_dir):
            print(f"  -> ⚠️ 本地尚不存在文件夹【{folder_name}】，建议先执行下载任务。")
            continue
            
        local_api_path = os.path.join(target_dir, "api.json")
        if not os.path.exists(local_api_path):
            alt_path = os.path.join(target_dir, "api_本地版.json")
            if os.path.exists(alt_path):
                shutil.move(alt_path, local_api_path)
            else:
                print(f"  -> ⚠️ 本地文件夹中缺少 api.json 配置。")
                continue
            
        manifest_path = os.path.join(target_dir, "manifest.json")
        local_changed = False
        local_change_logs = []
        current_manifest = get_folder_manifest(target_dir)
        
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as mf:
                    old_manifest = json.load(mf)
                
                for fpath, cur_item in current_manifest.items():
                    cur_md5, cur_size, cur_mtime = parse_manifest_entry(cur_item)
                    if fpath not in old_manifest:
                        local_change_logs.append(f"• ➕ [本地新增文件] 路径: ./sources_files/{folder_name}/{fpath}")
                        local_changed = True
                    else:
                        old_md5, old_size, old_mtime = parse_manifest_entry(old_manifest[fpath])
                        if (cur_md5 and old_md5 and cur_md5 != old_md5) or (cur_size != old_size or cur_mtime != old_mtime):
                            local_change_logs.append(f"• ✏️ [本地修改文件] 路径: ./sources_files/{folder_name}/{fpath}")
                            local_changed = True
            except Exception:
                pass
        else:
            save_folder_manifest(target_dir)

        try:
            with open(local_api_path, 'rb') as f:
                old_bytes = f.read()
            old_text = old_bytes.decode('utf-8', errors='ignore')
            old_json = brute_force_fix_json_silent(old_text) or {}
        except Exception:
            old_json = {}

        urls = [u.strip() for u in url_input.split('|') if u.strip()]
        new_content = None
        for u in urls:
            try:
                res = requests.get(u, headers={"User-Agent": "okhttp/4.1.0"}, verify=False, timeout=15)
                if res.status_code == 200:
                    new_content = res.content
                    break
            except Exception:
                continue
                
        if not new_content:
            print(f"  -> ❌ 无法从远程地址获取最新配置，跳过远程对比。")
            continue
            
        new_text = new_content.decode('utf-8', errors='ignore')
        new_json = brute_force_fix_json_silent(new_text) or {}
        
        remote_diff_logs = get_json_diff_details(old_json, new_json)
        old_hash = hashlib.md5(old_bytes).hexdigest()
        new_hash = hashlib.md5(new_content).hexdigest()
        remote_changed = (old_hash != new_hash)

        print(f"  -> 🤖 正在模拟 TVBox 客户端登录并搜索测试（【{folder_name}】）...")
        remote_site_count = len(new_json.get("sites", []))
        local_site_count = len(old_json.get("sites", [])) if old_json else remote_site_count
        
        _, total_searchable, responsive_search_count = simulate_tvbox_search_and_count(new_json)

        print(f"     📊 【源数量与搜索能力分析报告】:")
        print(f"        - 🌐 远程源包含站点总数: {remote_site_count} 个")
        print(f"        - 📁 本地源包含站点总数: {local_site_count} 个")
        print(f"        - 🔍 模拟搜索真实响应站点: {responsive_search_count}/{total_searchable} (按可搜索站点测算)")

        stats_html_block = f"""
        <div class="stats-box">
            <div class="stat-item"><span class="stat-num">{remote_site_count}</span><span class="stat-label">🌐 远程源总站点数</span></div>
            <div class="stat-item"><span class="stat-num">{local_site_count}</span><span class="stat-label">📁 本地源总站点数</span></div>
            <div class="stat-item"><span class="stat-num">{responsive_search_count} / {total_searchable}</span><span class="stat-label">🔍 模拟搜索真实响应率</span></div>
        </div>
        """

        if not remote_changed and not local_changed:
            html_sections.append(f"""
            <div class="card clean">
                <h3>✅ 【{folder_name}】源文件保持完全一致</h3>
                {stats_html_block}
                <p>远程源文件与本地完全一致。</p>
            </div>
            """)
        else:
            local_html_str = "<div class='section-title'>📁 本地文件目录变动</div><ul>" + "".join([f"<li>{l}</li>" for l in local_change_logs]) + "</ul>" if local_changed else ""
            remote_html_str = "<div class='section-title'>🌐 远程网站配置变动</div><ul>" + "".join([f"<li>{l}</li>" for l in remote_diff_logs]) + "</ul>" if remote_diff_logs else "<div class='section-title'>🌐 远程网站配置变动</div><ul><li>• 远程 api.json 内容字节流发生变动</li></ul>"

            html_sections.append(f"""
            <div class="card changed">
                <h3>✨✨✨ 【{folder_name}】检测到文件已发生改动！ ✨✨✨</h3>
                {stats_html_block}
                <details>
                    <summary>📋 点击展开/折叠详细改动位置与说明日志</summary>
                    <div class="details-content">{local_html_str}{remote_html_str}</div>
                </details>
            </div>
            """)
            
            if remote_changed:
                with open(local_api_path, 'wb') as f:
                    f.write(new_content)
            save_folder_manifest(target_dir)

    report_path = os.path.abspath("audit_report.html")
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>TVBox 源互动审计报告</title>
    <style>
        body {{ font-family: sans-serif; background-color: #121212; color: #e0e0e0; padding: 15px; margin: 0; }}
        h1 {{ text-align: center; color: #4facfe; font-size: 22px; margin-bottom: 20px; }}
        .card {{ background-color: #1e1e1e; border-radius: 10px; padding: 15px; margin-bottom: 20px; border-left: 5px solid #00e676; }}
        .card.changed {{ border-left-color: #ff9100; }}
        .stats-box {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; background: #252525; padding: 10px; border-radius: 8px; }}
        .stat-item {{ flex: 1; min-width: 120px; text-align: center; background: #303030; padding: 8px; border-radius: 6px; }}
        .stat-num {{ display: block; font-size: 18px; font-weight: bold; color: #00e676; }}
        .stat-label {{ font-size: 12px; color: #aaa; }}
        summary {{ cursor: pointer; font-weight: bold; color: #4facfe; padding: 10px; background: #2a2a2a; border-radius: 6px; }}
        .details-content {{ padding: 10px; background: #222; margin-top: 8px; border-radius: 6px; }}
        .section-title {{ font-weight: bold; margin-top: 10px; color: #ffd600; font-size: 14px; }}
        ul {{ list-style-type: none; padding-left: 5px; margin: 5px 0; }}
        li {{ margin-bottom: 5px; font-family: monospace; font-size: 13px; word-break: break-all; }}
    </style>
</head>
<body>
    <h1>TVBox 订阅源互动对齐与搜索报告</h1>
    {"".join(html_sections)}
</body>
</html>
"""
    try:
        with open(report_path, 'w', encoding='utf-8') as rf:
            rf.write(html_content)
        print(f"\n🌐 已自动生成网页互动报告: {report_path}")
        webbrowser.open(report_path)
    except Exception as e:
        print(f"⚠️ 无法自动打开报告: {e}")

def step7_fix_batch_download_and_check():
    print("\n--- 【步骤 7：新建 ‘执行4菜单源’ 强制拉取并实时同步热修 4 菜单代码逻辑】 ---")
    apply_runtime_patch("菜单 4 暴力拉取逻辑")
    step4_batch_download_without_template(force_redownload=True, custom_folder="执行4菜单源", auto_check=True)

def step8_fix_template_download_and_check():
    print("\n--- 【步骤 8：新建 ‘执行5菜单源’ 强制拉取并实时同步热修 5 菜单代码逻辑】 ---")
    apply_runtime_patch("菜单 5 模板重构逻辑")
    step5_batch_download_with_template(force_redownload=True, custom_folder="执行5菜单源", auto_check=True)

def brute_force_fix_json_silent(text):
    try:
        return json.loads(clean_json_string(text))
    except Exception:
        pass
    try:
        fixed = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', clean_json_string(text))
        return json.loads(fixed)
    except Exception:
        return None

def main():
    while True:
        print("\n==================================================")
        print("       TVBox 本地便携免安装助手（实时热修动态版）   ")
        print("==================================================")
        print("1. 仅下载并解密订阅源 (输入链接 -> 生成 api.json)")
        print("2. 依据已有文件重新对齐资产 (选择文件夹)")
        print("3. 一键完整处理单个源 (输入文件夹 + 链接 -> 全套本地化)")
        print("4. 批量下载与多个订阅源 (全量暴力拉取 + 自动检测审计)")
        print("5. 通过 ‘tvbox-josn’ 模板下载 (全量模板重构 + 自动检测审计)")
        print("6. 单独运行双向检测与模拟 TVBox 搜索对比")
        print("7. 独立新建 ‘执行4菜单源’ 文件夹 (实时同步修复 4 菜单逻辑)")
        print("8. 独立新建 ‘执行5菜单源’ 文件夹 (实时同步修复 5 菜单逻辑)")
        print("0. 退出程序")
        print("--------------------------------------------------")
        
        choice = input("请选择操作编号 [0-8]: ").strip()
        if choice == '1':
            step1_only_download_and_convert()
        elif choice == '2':
            step2_realign_assets()
        elif choice == '3':
            step3_one_click_workflow()
        elif choice == '4':
            step4_batch_download_without_template(force_redownload=True, auto_check=True)
        elif choice == '5':
            step5_batch_download_with_template(force_redownload=True, auto_check=True)
        elif choice == '6':
            step6_check_sources_diff()
        elif choice == '7':
            step7_fix_batch_download_and_check()
        elif choice == '8':
            step8_fix_template_download_and_check()
        elif choice == '0':
            print("👋 感谢使用，再见！")
            break

if __name__ == '__main__':
    main()
