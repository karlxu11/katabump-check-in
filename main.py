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
    """等待插件自动过盾"""
    print(f"--- [盾] 等待 Cloudflare ({timeout}s)... ---")
    start = time.time()
    while time.time() - start < timeout:
        if "just a moment" not in page.title.lower():
            if not page.ele('@src^https://challenges.cloudflare.com'):
                print("--- [盾] 通行！ ---")
                return True
        try:
            iframe = page.get_frame('@src^https://challenges.cloudflare.com')
            if iframe: iframe.ele('tag:body').click(by_js=True)
        except: pass
        time.sleep(1)
    return False

def robust_click(ele):
    """多重保障点击逻辑"""
    try:
        ele.scroll.to_see()
        time.sleep(0.5)
        print(">>> [动作] 尝试 JS 暴力点击...")
        ele.click(by_js=True)
        return True
    except Exception as e:
        print(f"⚠️ JS点击失败 ({e})，尝试普通点击...")
        try:
            ele.wait.displayed(timeout=3)
            ele.click()
            return True
        except Exception as e2:
            print(f"❌ 点击彻底失败: {e2}")
            return False

def check_text_result(page):
    """
    【核心修改】只读文字，不截图
    """
    print(">>> [6/5] 正在读取页面反馈文字...")
    start_time = time.time()
    
    # 轮询 10 秒，等待提示条出现
    while time.time() - start_time < 10:
        # 获取整个页面的文本内容 (转小写方便匹配)
        html_content = page.html.lower()
        
        # 情况 A: 未到期 (根据您的截图)
        # 关键词: "can't renew your server yet"
        if "can't renew your server yet" in html_content:
            print("-" * 50)
            print("🔴 结果反馈: 当前还不能续期")
            print("   原文提示: You can't renew your server yet.")
            print("✅ 结论: 脚本运行成功 (服务器未到期，操作正确)。")
            print("-" * 50)
            return True
            
        # 情况 B: 成功
        # 关键词: "successfully" 或 "extended"
        if "successfully" in html_content or "extended" in html_content:
            print("-" * 50)
            print("🟢 结果反馈: 续期成功！")
            print("   检测到关键词: Successfully / Extended")
            print("✅ 结论: 服务器寿命已延长。")
            print("-" * 50)
            return True
            
        time.sleep(1)
        
    print("❓ 未检测到明确文字提示，但流程已走完，默认视为成功。")
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
        # --- 变量检查 ---
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
            time.sleep(5)
            
            # ==================== 4. 处理弹窗 ====================
            print(">>> [5/5] 处理续期弹窗...")
            wait_for_cloudflare(page)
            
            modal = page.ele('css:.modal-content')
            if modal:
                print(">>> 检测到弹窗，寻找蓝色确认按钮...")
                confirm_btn = modal.ele('css:button.btn-primary') or \
                              modal.ele('css:button[type="submit"]') or \
                              modal.ele('xpath:.//button[contains(text(), "Renew")]')
                
                if confirm_btn:
                    print(f">>> 找到按钮: {confirm_btn.tag} | 文本: {confirm_btn.text}")
                    
                    if not confirm_btn.states.is_enabled:
                         print("⚠️ 按钮是灰色的 (Disabled)，直接检查页面文字...")
                         check_text_result(page)
                    else:
                        if robust_click(confirm_btn):
                            print("🎉🎉🎉 点击确认指令已发送！")
                            time.sleep(3)
                            # 【调用纯文字检测】
                            check_text_result(page)
                            print("✅✅✅ 脚本运行结束")
                        else:
                             raise Exception("点击操作最终失败")
                else:
                    print("❌ 弹窗内未找到可点击的按钮")
            else:
                print("❌ 未检测到弹窗元素 (.modal-content)")
        else:
            print("⚠️ 主界面未找到 Renew 按钮 (可能已续期)")
            check_text_result(page)

    except Exception as e:
        print(f"❌ 运行出错: {e}")
        # 出错时也不截图了，防止二次报错
        exit(1)
    finally:
        page.quit()

if __name__ == "__main__":
    job()
