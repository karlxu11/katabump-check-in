import os
import time
import requests
import zipfile
import io
import datetime
from DrissionPage import ChromiumPage, ChromiumOptions

# ==================== 实时日志工具 ====================
def log(message):
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{current_time}] {message}", flush=True)

# ==================== 核心逻辑 ====================

def download_and_extract_silk_extension():
    extension_id = "ajhmfdgkijocedmfjonnpjfojldioehi"
    crx_path = "silk.crx"
    extract_dir = "silk_ext"
    if os.path.exists(extract_dir) and os.listdir(extract_dir):
        log(f">>> [系统] 插件已就绪")
        return os.path.abspath(extract_dir)
    log(">>> [系统] 正在下载 Silk 隐私插件...")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
        resp = requests.get(f"https://clients2.google.com/service/update2/crx?response=redirect&prodversion=122.0&acceptformat=crx2,crx3&x=id%3D{extension_id}%26uc", headers=headers, stream=True)
        if resp.status_code == 200:
            content = resp.content
            zip_start = content.find(b'PK\x03\x04')
            with zipfile.ZipFile(io.BytesIO(content[zip_start:])) as zf:
                if not os.path.exists(extract_dir): os.makedirs(extract_dir)
                zf.extractall(extract_dir)
            return os.path.abspath(extract_dir)
    except: pass
    return None

def handle_modal_captcha(modal):
    """
    【核心需求】专门处理弹窗里的 Cloudflare
    """
    # 在弹窗里找 iframe，最多找 3 秒
    iframe = modal.ele('css:iframe[src*="cloudflare"]', timeout=3)
    if not iframe:
        iframe = modal.ele('css:iframe[title*="Widget"]', timeout=1)
        
    if iframe and iframe.states.is_displayed:
        log(">>> [弹窗] 👁️ 发现验证码，点击...")
        try:
            iframe.ele('tag:body').click(by_js=True)
            log(">>> [弹窗] 👆 已点击，等待 5 秒让它变绿...")
            time.sleep(5) 
            return True
        except: pass
    return False

def check_text_result(page):
    """扫描页面文字，判断结果"""
    full_text = page.html.lower()
    if "can't renew" in full_text or "too early" in full_text:
        log("✅ 结果: 还没到时间 (Too Early)")
        return "SUCCESS"
    if "success" in full_text or "extended" in full_text:
        log("✅ 结果: 续期成功 (Success)")
        return "SUCCESS"
    return "UNKNOWN"

def job():
    ext_path = download_and_extract_silk_extension()
    co = ChromiumOptions()
    co.set_argument('--headless=new')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--window-size=1920,1080')
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    if ext_path: co.add_extension(ext_path)
    co.auto_port()

    page = ChromiumPage(co)
    page.set.timeouts(10) # 默认超时设短一点，别傻等

    try:
        email = os.environ.get("KB_EMAIL")
        password = os.environ.get("KB_PASSWORD")
        target_url = os.environ.get("KB_RENEW_URL")
        
        if not all([email, password, target_url]): 
            log("❌ Secrets 缺失")
            exit(1)

        # ==================== 1. 登录 ====================
        log(">>> [Step 1] 登录...")
        page.get('https://dashboard.katabump.com/auth/login')
        
        # 简单的全页盾处理 (如果有)
        if page.title.lower() == "just a moment":
            log("--- 处理登录页 Cloudflare...")
            time.sleep(5) 
        
        if page.ele('css:input[name="email"]'):
            page.ele('css:input[name="email"]').input(email)
            page.ele('css:input[name="password"]').input(password)
            page.ele('css:button[type="submit"]').click()
            page.wait.url_change('login', exclude=True)

        # ==================== 2. 直奔主题 ====================
        log(">>> [Step 2] 进入服务器页面...")
        page.get(target_url)
        
        # 简单的进门盾处理
        if "just a moment" in page.title.lower():
             log("--- 处理页面 Cloudflare...")
             time.sleep(5) # 插件会自动过，稍微等等就行

        # 【直接找按钮】不循环，不刷新，有就是有，没有就是没有
        renew_btn = page.ele('css:button:contains("Renew")', timeout=5)
        
        if renew_btn:
            log(">>> [动作] 点击主 Renew 按钮...")
            renew_btn.click(by_js=True)
            
            # 等待弹窗
            log(">>> 等待弹窗...")
            modal = page.wait.ele_displayed('css:.modal-content', timeout=5)
            
            if modal:
                # ==========================================
                # 这就是您要求的：在点确认前，加一个 CF 验证
                # ==========================================
                handle_modal_captcha(modal)
                
                # 验证完后，再点确认
                confirm = modal.ele('css:button.btn-primary')
                if confirm:
                    log(">>> [动作] 点击最终确认 (Confirm)...")
                    confirm.click(by_js=True)
                    time.sleep(5) # 等待结果回显
                    check_text_result(page)
                else:
                    log("⚠️ 弹窗里没找到确认按钮")
            else:
                log("❌ 弹窗未弹出")
        else:
            # 没找到按钮？直接检查是不是“时间未到”
            # 这一步非常关键，避免了之前的傻等
            log("⚠️ 未找到 Renew 按钮，直接检查页面提示...")
            if check_text_result(page) == "UNKNOWN":
                log("❓ 既没按钮，也没提示，可能需要人工检查。")

        log("\n🏁 脚本运行结束")

    except Exception as e:
        log(f"❌ 异常: {e}")
        exit(1)
    finally:
        page.quit()

if __name__ == "__main__":
    job()
