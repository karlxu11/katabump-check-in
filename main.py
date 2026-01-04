import os
import time
import requests
import zipfile
import io
from DrissionPage import ChromiumPage, ChromiumOptions

def download_and_extract_silk_extension():
    """自动下载并解压 Silk 插件"""
    extension_id = "ajhmfdgkijocedmfjonnpjfojldioehi"
    crx_path = "silk.crx"
    extract_dir = "silk_ext"
    
    if os.path.exists(extract_dir) and os.listdir(extract_dir):
        print(f">>> [系统] 插件已就绪: {extract_dir}")
        return os.path.abspath(extract_dir)
        
    print(">>> [系统] 正在下载 Silk 隐私插件...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    download_url = f"https://clients2.google.com/service/update2/crx?response=redirect&prodversion=122.0&acceptformat=crx2,crx3&x=id%3D{extension_id}%26uc"
    
    try:
        resp = requests.get(download_url, headers=headers, stream=True)
        if resp.status_code == 200:
            content = resp.content
            zip_start = content.find(b'PK\x03\x04')
            if zip_start == -1: return None
            with zipfile.ZipFile(io.BytesIO(content[zip_start:])) as zf:
                if not os.path.exists(extract_dir): os.makedirs(extract_dir)
                zf.extractall(extract_dir)
            return os.path.abspath(extract_dir)
        return None
    except: return None

def wait_for_cloudflare(page, timeout=20):
    """
    等待并处理页面级的 Cloudflare
    """
    print(f"--- [盾] 检查全页 Cloudflare ({timeout}s)... ---")
    start = time.time()
    while time.time() - start < timeout:
        if "just a moment" not in page.title.lower():
            if not page.ele('@src^https://challenges.cloudflare.com'):
                return True
        try:
            iframe = page.get_frame('@src^https://challenges.cloudflare.com')
            if iframe: iframe.ele('tag:body').click(by_js=True)
        except: pass
        time.sleep(1)
    return False

def solve_modal_captcha(modal):
    """
    【新增】专门解决弹窗里的验证码
    """
    print(">>> [验证] 正在寻找弹窗内的 Captcha...")
    # 在弹窗元素内部寻找 iframe
    iframe = modal.ele('tag:iframe') 
    # 或者更精确: modal.ele('@src^https://challenges.cloudflare.com')
    
    if iframe:
        print(">>> [验证] 发现验证码 iframe，尝试点击...")
        try:
            # 点击 iframe 内部
            iframe.ele('tag:body').click(by_js=True)
            # 点击后必须死等几秒，等它转圈圈变绿
            print(">>> [验证] 已点击，等待验证生效 (5秒)...")
            time.sleep(5)
            return True
        except Exception as e:
            print(f"⚠️ 验证码点击异常: {e}")
    else:
        print(">>> [验证] 弹窗内未发现 iframe，可能无验证码。")
    return False

def robust_click(ele):
    """多重保障点击逻辑"""
    try:
        ele.scroll.to_see()
        time.sleep(0.5)
        print(f">>> [动作] 点击按钮: {ele.text}")
        ele.click(by_js=True)
        return True
    except Exception as e:
        print(f"⚠️ JS点击失败，尝试普通点击...")
        try:
            ele.wait.displayed(timeout=3)
            ele.click()
            return True
        except Exception as e2:
            print(f"❌ 点击彻底失败: {e2}")
            return False

def capture_real_message(page):
    """扫描页面真实反馈"""
    print(">>> [6/5] 正在扫描页面真实反馈...")
    start_time = time.time()
    found_any_message = False

    while time.time() - start_time < 10:
        alerts = page.eles('css:div[class*="alert"]') # 抓取提示框
        messages = []
        
        for alert in alerts:
            # 修复 DrissionPage 4.x 语法: 使用 .states.is_displayed
            if alert.states.is_displayed:
                text = alert.text
                messages.append(f"[提示框]: {text}")

        if messages:
            found_any_message = True
            print("\n" + "="*50)
            print("📢 【页面真实回显】:")
            for msg in messages:
                print(f"   {msg}")
            print("="*50 + "\n")
            
            full_msg_str = str(messages).lower()
            
            # 成功抓取到验证码错误的提示，说明脚本之前的操作确实被拦截了
            if "captcha" in full_msg_str or "验证码" in full_msg_str:
                print("⚠️ 警告：因为验证码未通过被拦截，本次操作可能失败。")
                return False

            if "can't renew" in full_msg_str or "too early" in full_msg_str:
                print("✅ 判定结果: 还没到时间 (脚本操作正确)")
                return True
            elif "success" in full_msg_str or "extended" in full_msg_str:
                print("✅ 判定结果: 续期成功")
                return True
            
        time.sleep(1)
    
    if not found_any_message:
        print("⚠️ 未捕捉到明显提示。")
    return True

def job():
    ext_path = download_and_extract_silk_extension()
    co = ChromiumOptions()
    co.set_argument('--headless=new')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--window-size=1920,1080')
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    if ext_path: co.add_extension(ext_path)
    co.auto_port()
    
    page = ChromiumPage(co)
    try: page.set.timeouts(15)
    except: pass

    try:
        email = os.environ.get("KB_EMAIL")
        password = os.environ.get("KB_PASSWORD")
        target_url = os.environ.get("KB_RENEW_URL")
        if not all([email, password, target_url]): raise Exception("缺少 Secrets 配置")

        # ==================== 1. 登录 ====================
        print(">>> [1/5] 前往登录页...")
        page.get('https://dashboard.katabump.com/auth/login', retry=3)
        wait_for_cloudflare(page)
        
        if "auth/login" in page.url:
            print(">>> 输入账号密码...")
            page.ele('css:input[name="email"]').input(email)
            page.ele('css:input[name="password"]').input(password)
            time.sleep(1)
            page.ele('css:button[type="submit"]').click()
            print(">>> 等待跳转...")
            time.sleep(5)
            wait_for_cloudflare(page)
        
        if "login" in page.url: raise Exception("登录失败")
        print(">>> ✅ 登录成功！")

        # ==================== 2. 直达服务器 ====================
        print(f">>> [3/5] 进入服务器页面...")
        page.get(target_url, retry=3)
        page.wait.load_start()
        wait_for_cloudflare(page)
        time.sleep(3)

        # ==================== 3. 点击主 Renew 按钮 ====================
        print(">>> [4/5] 寻找主界面 Renew 按钮...")
        renew_btn = page.ele('css:button:contains("Renew")') or \
                    page.ele('xpath://button[contains(text(), "Renew")]') or \
                    page.ele('text:Renew')
        
        if renew_btn:
            robust_click(renew_btn)
            print(">>> 已点击主按钮，等待弹窗加载...")
            time.sleep(5) # 必须等待弹窗完全加载，否则找不到里面的 iframe
            
            # ==================== 4. 处理弹窗 (重点) ====================
            print(">>> [5/5] 处理续期弹窗...")
            
            modal = page.ele('css:.modal-content')
            if modal:
                print(">>> 检测到弹窗容器...")
                
                # 【关键修正】在点击确认前，先处理弹窗里的验证码！
                solve_modal_captcha(modal)
                
                # 寻找确认按钮
                confirm_btn = modal.ele('css:button.btn-primary') or \
                              modal.ele('css:button[type="submit"]') or \
                              modal.ele('xpath:.//button[contains(text(), "Renew")]')
                
                if confirm_btn:
                    if not confirm_btn.states.is_enabled:
                         print("⚠️ 按钮是灰色的 (Disabled)，直接检查反馈...")
                         capture_real_message(page)
                    else:
                        print(">>> 准备点击最终确认按钮...")
                        if robust_click(confirm_btn):
                            print("🎉🎉🎉 指令已发送，等待服务器响应...")
                            time.sleep(3) 
                            capture_real_message(page)
                        else:
                             raise Exception("点击操作最终失败")
                else:
                    print("❌ 弹窗内未找到可点击的按钮")
            else:
                print("❌ 未检测到弹窗元素 (.modal-content)")
        else:
            print("⚠️ 主界面未找到 Renew 按钮")
            capture_real_message(page)

    except Exception as e:
        print(f"❌ 运行出错: {e}")
        exit(1)
    finally:
        page.quit()

if __name__ == "__main__":
    job()
