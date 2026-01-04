import os
import time
import requests
import zipfile
import io
import datetime
from DrissionPage import ChromiumPage, ChromiumOptions

# ==================== 基础工具 ====================
def log(message):
    """实时日志"""
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{current_time}] {message}", flush=True)

def download_silk():
    """下载插件"""
    extract_dir = "silk_ext"
    if os.path.exists(extract_dir): return os.path.abspath(extract_dir)
    log(">>> [系统] 正在下载过盾插件...")
    try:
        url = "https://clients2.google.com/service/update2/crx?response=redirect&prodversion=122.0&acceptformat=crx2,crx3&x=id%3Dajhmfdgkijocedmfjonnpjfojldioehi%26uc"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, stream=True)
        if resp.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                zf.extractall(extract_dir)
            return os.path.abspath(extract_dir)
    except: pass
    return None

# ==================== 核心逻辑 ====================

def pass_full_page_shield(page):
    """处理全屏 Cloudflare (门神)"""
    for _ in range(3):
        if "just a moment" in page.title.lower():
            log("--- [门神] 正在通过全屏盾...")
            # timeout=2 自带等待
            iframe = page.ele('css:iframe[src*="cloudflare"]', timeout=2)
            if iframe: 
                iframe.ele('tag:body').click(by_js=True)
                time.sleep(3)
        else:
            return True
    return False

def pass_modal_captcha(modal):
    """
    【修复版】处理弹窗内的 CF 盾
    不再使用 wait.ele_displayed，改用 .ele(timeout=...)
    """
    log(">>> [弹窗] 正在扫描验证码 iframe...")
    
    # ⚠️ 修复点：直接用 ele 配合 timeout，这在所有版本都通用
    # 尝试找 cloudflare 的 iframe，最多等 10 秒
    iframe = modal.ele('css:iframe[src*="cloudflare"]', timeout=10)
    
    if not iframe:
        # 备选：有时候是 widget
        iframe = modal.ele('css:iframe[title*="Widget"]', timeout=2)

    if iframe:
        log(">>> [弹窗] 👁️ 发现验证码，点击...")
        try:
            iframe.ele('tag:body').click(by_js=True)
            log(">>> [弹窗] 👆 已点击，强制等待 5 秒 (变绿)...")
            time.sleep(5) 
            return True
        except: 
            pass
    else:
        log(">>> [弹窗] 未发现验证码 (可能无需验证)")
    return False

def check_result_status(page):
    """检查结果"""
    html = page.html.lower()
    if "can't renew" in html or "too early" in html:
        return "TOO_EARLY"
    if "success" in html or "extended" in html:
        return "SUCCESS"
    return "UNKNOWN"

# ==================== 主程序 ====================
def job():
    ext_path = download_silk()
    
    co = ChromiumOptions()
    co.set_argument('--headless=new')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--window-size=1920,1080')
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    if ext_path: co.add_extension(ext_path)
    co.auto_port()

    page = ChromiumPage(co)
    page.set.timeouts(15)

    try:
        email = os.environ.get("KB_EMAIL")
        password = os.environ.get("KB_PASSWORD")
        target_url = os.environ.get("KB_RENEW_URL")
        
        if not all([email, password, target_url]): 
            log("❌ Secrets 配置缺失")
            exit(1)

        # ---------------- Step 1: 登录 ----------------
        log(">>> [1/3] 前往登录页...")
        page.get('https://dashboard.katabump.com/auth/login')
        pass_full_page_shield(page)

        if page.ele('css:input[name="email"]'):
            log(">>> 输入账号密码...")
            page.ele('css:input[name="email"]').input(email)
            page.ele('css:input[name="password"]').input(password)
            page.ele('css:button#submit').click()
            page.wait.url_change('login', exclude=True, timeout=20)
        
        # ---------------- Step 2: 直达服务器页面 ----------------
        log(">>> [2/3] 跳转至服务器续期页...")
        page.get(target_url)
        pass_full_page_shield(page)
        
        # ---------------- Step 3: 寻找 Renew 按钮 ----------------
        log(">>> 正在定位 Renew 按钮...")
        
        renew_btn = None
        for _ in range(10):
            # 使用您提供的精准 data 属性
            renew_btn = page.ele('css:button[data-bs-target="#renew-modal"]')
            if renew_btn and renew_btn.states.is_displayed: break
            time.sleep(1)

        if renew_btn:
            log(">>> [动作] 点击主 Renew 按钮...")
            renew_btn.click(by_js=True)
            
            log(">>> 等待弹窗加载...")
            # 这里也改用 ele(timeout=...) 防止报错
            modal = page.ele('css:.modal-content', timeout=10)
            
            if modal:
                # 1. 先处理弹窗里的盾 (已修复函数)
                pass_modal_captcha(modal)
                
                # 2. 点击确认
                confirm_btn = modal.ele('css:button[type="submit"].btn-primary')
                
                if confirm_btn:
                    log(">>> [动作] 点击最终确认 (Confirm)...")
                    confirm_btn.click(by_js=True)
                    
                    time.sleep(5)
                    status = check_result_status(page)
                    if status == "SUCCESS":
                        log("🎉🎉🎉 续期成功！(Success)")
                    else:
                        log("⚠️ 未检测到成功字样，请检查截图。")
                else:
                    log("❌ 弹窗里找不到 Submit 按钮")
                    exit(1)
            else:
                log("❌ 弹窗未出现")
                exit(1)
        else:
            log("⚠️ 未找到 Renew 按钮，检查状态...")
            status = check_result_status(page)
            if status == "TOO_EARLY":
                log("✅ [结果] 还没到时间 (Too Early)，无需操作。")
            else:
                log("❌ 页面异常：没按钮也没提示。")
                exit(1)

    except Exception as e:
        log(f"❌ 运行异常: {e}")
        exit(1)
    finally:
        page.quit()

if __name__ == "__main__":
    job()
