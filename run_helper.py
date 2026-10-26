import os, re, requests, time, sys, json, hashlib, shutil, base64, zlib, gzip, random
from datetime import datetime, timezone, timedelta
from io import StringIO
from urllib.parse import urljoin, urlparse
import tvbox_helper

bj_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
state_file = '.source_state.json'

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; V2231A Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
    'TVBox/1.1.4 (Linux; Android 11)',
    'okhttp/4.10.0'
]

try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False

# 独立内置深度字节解密与内容解析引擎，彻底解决模块属性缺失问题
def parse_tvbox_content(raw_bytes, target_url=''):
    content_candidates = []

    if b'IEND' in raw_bytes:
        try:
            iend_pos = raw_bytes.rfind(b'IEND')
            after_iend = raw_bytes[iend_pos + 8:]
            content_candidates.append(after_iend.decode('utf-8', errors='ignore'))
        except Exception:
            pass

    try:
        text_preview = raw_bytes[:120].decode('utf-8', errors='ignore').strip()
        if text_preview.startswith('2423') or (len(text_preview) > 50 and all(c in '0123456789abcdefABCDEF' for c in text_preview[:100])):
            raw_bytes = bytes.fromhex(text_preview)
    except Exception:
        pass

    try:
        if raw_bytes.startswith(b'$#'):
            idx_end = raw_bytes.find(b'#$', 2)
            if idx_end != -1:
                raw_bytes = raw_bytes[idx_end + 2:]
    except Exception:
        pass

    try:
        content_candidates.append(raw_bytes.decode('utf-8', errors='ignore'))
    except:
        pass
        
    try:
        content_candidates.append(zlib.decompress(raw_bytes).decode('utf-8', errors='ignore'))
    except:
        try:
            content_candidates.append(gzip.decompress(raw_bytes).decode('utf-8', errors='ignore'))
        except:
            pass

    try:
        full_str = raw_bytes.decode('latin1', errors='ignore')
        b64_matches = re.findall(r'[A-Za-z0-9+/=]{30,}', full_str)
        for b64_str in b64_matches:
            try:
                dec = base64.b64decode(b64_str.encode('utf-8'))
                content_candidates.append(dec.decode('utf-8', errors='ignore'))
                try:
                    content_candidates.append(zlib.decompress(dec).decode('utf-8', errors='ignore'))
                except:
                    pass
            except:
                pass
    except:
        pass

    content_candidates.append(raw_bytes.decode('latin1', errors='ignore'))
    combined_content = "\n".join(content_candidates)
    
    clean_lines = [line for line in combined_content.splitlines() if not line.strip().startswith('//') and '高抬贵手' not in line]
    clean_content = '\n'.join(clean_lines).strip()

    possible_indices = [i for i, char in enumerate(clean_content) if char in ('{', '[')]
    json_data = None
    
    for idx in possible_indices:
        try:
            data, _ = json.JSONDecoder().raw_decode(clean_content, idx)
            if isinstance(data, (dict, list)) and len(data) > 0:
                if isinstance(data, dict) and any(k in data for k in ('sites', 'spider', 'lives', 'channels', 'parses')):
                    json_data = data
                    break
                elif json_data is None and isinstance(data, dict):
                    json_data = data
        except Exception:
            continue

    if json_data is None and 'sites' in clean_content:
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', clean_content)
        if match:
            try:
                json_data = json.loads(match.group(1))
            except Exception:
                pass

    if json_data is None:
        raise ValueError("未能提取到合法的 JSON 配置对象")
        
    return json_data, clean_content

# 自动初始化/补充【茄子库】和【无意云】多备用地址
default_sources_content = (
    "茄子库,http://boluo.live | http://vip.boluo.live | http://李白.shop | https://700sjro44343.vicp.fun/vip/2505/qiezi/tv.php | https://700sjro44343.vicp.fun/vip/2505/qiezi/duo.txt\n"
    "无意云,https://yc.wya6.cn/wykj.php | https://yc.wya6.cn/wyxs.php\n"
)

if not os.path.exists('sources_list.txt'):
    with open('sources_list.txt', 'w', encoding='utf-8') as f:
        f.write(default_sources_content)
else:
    with open('sources_list.txt', 'r', encoding='utf-8') as f:
        existing_content = f.read()
    if "茄子库" not in existing_content and "无意云" not in existing_content:
        with open('sources_list.txt', 'a', encoding='utf-8') as f:
            f.write("\n" + default_sources_content)

old_state = {}
if os.path.exists(state_file):
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            old_state = json.load(f)
    except:
        pass

new_state = {}
sources_raw = []
if os.path.exists('sources_list.txt'):
    with open('sources_list.txt', 'r', encoding='utf-8') as f:
        sources_raw = [line.strip() for line in f if line.strip()]

new_sources_lines = []
source_results = []

for idx, line in enumerate(sources_raw, 1):
    if line.startswith('#'):
        new_sources_lines.append(line)
        continue
    
    parts = line.split(',', 1)
    name = parts[0].strip() if len(parts) > 1 else f'源{idx}'
    url_part = parts[1] if len(parts) > 1 else line
    
    urls = [u.strip() for u in re.split(r'[|\s]+', url_part) if u.strip().startswith('http')]
    
    if not urls:
        source_results.append(f'📌 <b>源 [{idx}] ({name})</b>\n状态: ❌ 失败 (未找到有效网址)')
        new_sources_lines.append(line)
        continue
        
    working_url = None
    fail_details = []
    fetched_content = None
    parsed_json = None
    
    for u_idx, url in enumerate(urls, 1):
        addr_type = '主地址' if u_idx == 1 else f'备用地址 {u_idx-1}'
        success = False
        last_err = ''
        
        parsed_u = urlparse(url)
        netloc_safe = parsed_u.netloc
        try:
            netloc_safe = parsed_u.netloc.encode('idna').decode('ascii')
        except Exception:
            pass
        domain_root = f"{parsed_u.scheme}://{netloc_safe}"
        domain_referer = domain_root + "/"
        
        for ua in USER_AGENTS:
            try:
                res = requests.get(url, headers={'User-Agent': ua, 'Referer': domain_referer}, timeout=30, verify=False)
                if res.content and len(res.content) > 100:
                    try:
                        parsed_json, _ = parse_tvbox_content(res.content, url)
                        fetched_content = res.content
                        success = True
                        break
                    except Exception as inner_ex:
                        last_err = f'解析失败: {inner_ex}'
                else:
                    last_err = f'HTTP状态码 {res.status_code}'
            except Exception as e:
                last_err = f'异常 {str(e)}'
        
        if not success and HAS_CFFI:
            try:
                res = cffi_requests.get(url, impersonate="chrome120", timeout=30)
                if res.content and len(res.content) > 100:
                    parsed_json, _ = parse_tvbox_content(res.content, url)
                    fetched_content = res.content
                    success = True
            except Exception as e:
                last_err = f'CFFI异常 {str(e)}'

        if success:
            working_url = url
            break
        else:
            fail_details.append(f'{addr_type} ({url}): {last_err}')
            
    if not working_url:
        details_str = '\n  '.join(fail_details)
        source_results.append(f'📌 <b>源 [{idx}] ({name})</b>\n状态: ❌ <b>全部地址失效</b>\n  {details_str}')
        new_sources_lines.append(line)
    else:
        jar_status_tip = ''
        try:
            if isinstance(parsed_json, dict):
                spider_val = parsed_json.get('spider', '')
                base_jar_name = None
                if spider_val:
                    spider_path_part = spider_val.split(';')[0].strip()
                    lower_part = spider_path_part.lower()
                    if not any(lower_part.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']):
                        base_jar_name = os.path.basename(spider_path_part) if lower_part.endswith('.jar') or '.' in spider_path_part else 'spider.jar'

                if base_jar_name:
                    local_rel_path = f"sources_files/{name}/{base_jar_name}"
                    if os.path.exists(local_rel_path) and os.path.getsize(local_rel_path) > 1024:
                        jar_status_tip = f' | 📦 <b>{base_jar_name} 已存在</b>'
                    else:
                        jar_status_tip = f' | 📦 <b>jar同步完成</b>'

            normalized_str = json.dumps(parsed_json, sort_keys=True, ensure_ascii=False)
        except Exception:
            normalized_str = re.sub(r'\s+', '', fetched_content.decode('utf-8', errors='ignore'))

        content_hash = hashlib.md5(normalized_str.encode('utf-8')).hexdigest()
        prev_info = old_state.get(name, {})
        prev_hash = prev_info.get('hash', '')
        prev_time = prev_info.get('time', bj_time)
        
        update_status = '✨ 内容已更新' if content_hash != prev_hash else '🟢 内容无变化'
        last_update_time = bj_time if content_hash != prev_hash else prev_time
            
        new_state[name] = {'hash': content_hash, 'time': last_update_time}
        source_results.append(f'📌 <b>源 [{idx}] ({name})</b>\n状态: ✅ 成功 | {update_status}{jar_status_tip}\n地址: {working_url}\n最后更新时间: {last_update_time}')
        
        other_urls = [u for u in urls if u != working_url]
        reordered_line = f'{name},' + ' | '.join([working_url] + other_urls) if len(parts) > 1 else working_url
        new_sources_lines.append(reordered_line)

with open(state_file, 'w', encoding='utf-8') as f:
    json.dump(new_state, f, ensure_ascii=False, indent=2)

with open('sources_list.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_sources_lines) + '\n')

sys.stdin = StringIO('4\n0\n')
try:
    tvbox_helper.main()
except SystemExit:
    pass

details_text = '\n\n'.join(source_results)
message = f'<b>📊 TVBox 智能备用源独立监控报告</b>\n\n{details_text}'

for i in range(1, 11):
    token = os.getenv(f'TG_TOKEN_{i}')
    chat_id = os.getenv(f'TG_CHAT_{i}')
    if token and chat_id:
        try:
            requests.post(f'https://api.telegram.org/bot{token}/sendMessage', json={
                'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'
            }, timeout=10)
        except Exception:
            pass
