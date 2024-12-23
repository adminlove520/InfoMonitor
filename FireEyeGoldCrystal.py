#!/usr/bin/python3
import requests
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
from openpyxl import Workbook
import argparse
import schedule
from bs4 import BeautifulSoup
import random

result=[]

# 钉钉机器人的加签密钥
secret = 'SECcc3da4f218d34da7fdc4cb778692087a7660b911120c5033b670db26a505fae8'
# 钉钉机器人的Webhook
webhook = 'https://oapi.dingtalk.com/robot/send?access_token=18dba005ec58f2a60dae62be24630b2d4108f7f8120ddb576cdc91904bbfc5ff'
# 企业微信webhook
wxwork_url=''

def clearResult():
    result.clear()

def get_all_bing_daily_wallpapers(num_wallpapers=8):
    wallpaper_urls = []  # 初始化一个空的壁纸地址列表

    # 获取Bing每日壁纸的API地址，设置n参数以获取多天的壁纸
    url = f"https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n={num_wallpapers}&mkt=en-US"

    # 发送HTTP GET请求获取JSON数据
    response = requests.get(url)
    data = json.loads(response.text)

    # 构建完整的壁纸URL列表
    bing_base_url = "https://www.bing.com"
    for image_data in data['images']:
        wallpaper_url = urllib.parse.urljoin(bing_base_url, image_data['url'])
        wallpaper_urls.append(wallpaper_url)  # 将壁纸URL添加到列表中

    return wallpaper_urls

def get_random_bing_wallpaper():
    # 获取近8天Bing壁纸的URL列表
    bing_wallpaper_urls = get_all_bing_daily_wallpapers()
    
    if bing_wallpaper_urls:
        # 随机选择一个壁纸URL
        random_wallpaper_url = random.choice(bing_wallpaper_urls)
        return random_wallpaper_url
    else:
        return None

def proxy(proxy):
    try:
        key=proxy.split('://')[0]
        return {key:proxy}
    except:
        exit('[!] 代理地址格式有误！')

def headers(header):
    try:
        headers=json.loads(header)
        return headers
    except:
        exit('[!] HTTP请求头格式有误！')

# 钉钉推送
def DingDing(msg):
    if not msg:
        return
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    url=webhook+'&timestamp='+timestamp+'&sign='+sign
    #json={"msgtype": "text","text": {"content": msg},"isAtAll": True}
    msglist=[{
                "title": "东方隐侠·GitHub情报"+str(len(msg))+"条",
                "picURL": get_random_bing_wallpaper()
            }]
    for i in range(len(msg)):
        tmpj = {"title": msg[i]['存储库描述'],
                "messageURL": msg[i]['存储库链接']
                }
        msglist.append(tmpj)
    json ={
    "msgtype": "feedCard",
    "feedCard": {
        "links": msglist
    }
}
    r=requests.post(url,json=json,headers=head,proxies=proxies,timeout=timeout,verify=False)
    #print(r.text)

# 企业微信推送
def WXWork(msg):
    #json格式化发送的数据信息
    if not msg:
        return
    res = "# GitHub情报"+str(len(msg))+"条\n"
    for i in range(len(msg)):
        res+=str(i+1)+". ["+msg[i]['存储库描述']+"]("+msg[i]['存储库链接']+")\n"
    data = json.dumps({
        "msgtype": "markdown",
        "markdown": {
            "content": res
            }
        })
    # 指定机器人发送消息
    resp = requests.post(wxwork_url,data,auth=('Content-Type', 'application/json'))
    #print(resp.json)

# 获取GitHub存储库更新信息
def GetNewSearch():
    # 存储包含各关键字的存储库的数量
    init_count=[]
    
    sl=len(SearchList)
    i=0
    while i<sl:
        search_url = "https://api.github.com/search/repositories?q="+SearchList[i]+"&sort=updated"
        try:
            init = requests.get(search_url,headers=head,proxies=proxies,timeout=timeout,verify=False).text
        except Exception as e:
            print(e)
            time.sleep(10)
            continue
        if 'API rate limit exceeded' in init:
            time.sleep(10)
            continue
        #print(json.loads(init).get('total_count'))
        # 获取包含当前关键字的存储库总数
        init_count.append(json.loads(init).get('total_count'))
        time.sleep(6)
        i+=1
    #print(init_count)
    #print("[*] total_count",total_count)
    # 设置监控阈值
    #time.sleep(60*mt)
    temp=[]
    for i in range(len(SearchList)):
        try:
            github_api = "https://api.github.com/search/repositories?q="+SearchList[i]+"&sort=updated"
            res = requests.get(github_api,headers=head,proxies=proxies,timeout=timeout,verify=False).text
            json_res=json.loads(res)
            # 获取包含当前关键字的存储库总数
            current_count=json_res.get('total_count')
            if current_count==None:
                continue
            newRes_num=current_count > init_count[i]
            if newRes_num > 0:
                items=json_res.get('items')
                # 更新的存储库总在前边显示，因此只需取前N个即可
                for i in range(newRes_num):
                    newRes=items[i]
                    html_url=newRes.get('html_url')
                    desc=newRes.get('description')
                    if desc==None:
                        desc=SearchList[i] + html_url.split('/')[-1]
                    else:
                        # 过滤包含敏感词的存储库
                        if Filter(desc):
                            continue
                    #print("仓库描述：",desc,"仓库链接：",newRes.get('html_url'))
                    # 过滤黑名单用户
                    if FilterUser(html_url):
                        continue
                    result.append({"存储库描述":desc,"存储库链接":html_url})
                    temp.append({"存储库描述":desc,"存储库链接":html_url})
                time.sleep(6)
        except Exception as e:
            print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),e)
    print(temp)
    if temp and args.r:
        DingDing(temp)
        WXWork(temp)
        #ServerChan(temp)
        #Telegram(temp)

# 获取单页中的存储库描述和链接地址
def GetOnePageData(jsonResp,sheet):
    json_res=json.loads(jsonResp)
    item_num=len(json_res.get('items'))
    for i in range(item_num):
        desc=json_res.get('items')[i].get('description')
        if desc==None:
            desc="空"
        else:
            # 过滤包含敏感词的存储库
            if Filter(desc):
                continue
        html_url=json_res.get('items')[i].get('html_url')
        # 过滤黑名单用户
        if FilterUser(html_url):
            continue
        print(desc,html_url)
        # 写入sheet
        sheet.append([desc,html_url])

# 获取GitHub所有存储库
def GetAll():
    # 实例化Excel工作簿
    wb=Workbook()
    sl=len(SearchList)
    # 创建Sheet
    sheets=[]
    for s in SearchList:
        sheets.append(wb.create_sheet(s))
    i=0
    while i<sl:
        url="https://api.github.com/search/repositories?q="+SearchList[i]+"&per_page=100"
        r = requests.get(url,headers=head,proxies=proxies,timeout=timeout,verify=False)
        if 'API rate limit exceeded' in r.text:
            time.sleep(6)
            continue
        try:
            # 获取查询结果总页数
            link=r.headers['Link']
            page=int(link.split('page=')[-1].split('>')[0])
            # 获取第一页数据
            GetOnePageData(r.text,sheets[i])
            # 获取其它页数据
            j=2
            while j<=page:
                url="https://api.github.com/search/repositories?q="+SearchList[i]+"&per_page=100&page="+str(j)
                r=requests.get(url,headers=head,proxies=proxies,timeout=timeout,verify=False)
                if 'API rate limit exceeded' in r.text:
                    time.sleep(6)
                    continue
                GetOnePageData(r.text,sheets[i])
                time.sleep(3)
                j+=1
        except KeyError:
            GetOnePageData(r.text,sheets[i])
        time.sleep(6)
        # 设置Sheet颜色
        sheets[i].sheet_properties.tabColor = "9AFF9A"
        i+=1
    wb.remove(wb['Sheet'])
    wb.save('FEGC.xlsx')

# 过滤敏感词
def Filter(msg):
    for w in SensitiveWords:
        if w in msg:
            return True
    return False

# 过滤黑名单用户
def FilterUser(url):
    user=url.split("/")[3]
    if user in BlacklistUsers:
        return True
    else:
        return False

# Server酱推送
def ServerChan(msg):
    # sckey为自己的server SCKEY
    sckey = ''
    url = 'https://sc.ftqq.com/'+sckey+'.send?text=GitHub&desp='+msg
    requests.get(url,headers=head,proxies=proxies,timeout=timeout,verify=False)


# Telegram推送
def Telegram(msg):
    import telegram
    # 自己的Telegram Bot Token
    token = ''
    bot = telegram.Bot(token=token)
    # 自己的Group ID
    group_id = ''
    bot.send_message(chat_id=group_id, text=msg)

procdesc="FireEyeGoldCrystal 是一个GitHub监控和信息收集工具，支持钉钉、Server酱和Telegram推送，过滤敏感词，查找包含关键字的所有仓库并输出到FEGC.xlsx文件     --By NHPT"
parser=argparse.ArgumentParser(description=procdesc,epilog="GitHub:https://github.com/adminlove520")

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-m',action='store_true',help='监控模式，定时推送')
group.add_argument('-c',action='store_true',help='信息收集模式')

parser.add_argument('-p',help='设置代理地址，如：http://127.0.0.1:8080')
parser.add_argument('-t',help='设置超时时间，单位：秒')
parser.add_argument('-r',action='store_true',help='是否实时推送')
parser.add_argument('-d',default='09:00',help='设置每天定时推送时间，默认为：09:00，需要使用24小时格式')
parser.add_argument('-H',help='设置HTTP请求头，json格式，如：{"X-Forwarded-For":"127.0.0.1"}')
parser.add_argument('-mT',type=int,default=5,help='设置监控阈值，单位：分，默认5分钟')
parser.add_argument('-iF',type=argparse.FileType('r',encoding='utf8'),help='设置关键字文件')
parser.add_argument('-sW',type=argparse.FileType('r',encoding='utf8'),help='设置敏感词文件')

args=parser.parse_args()

requests.packages.urllib3.disable_warnings()
# 当前年份
current_year=time.localtime()[0]
# 监控阈值，默认5分钟
mt=args.mT
timeout=None
proxies=None
head = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36"
}
# 关键字列表
SearchList=["CVE-"+str(current_year) ,"CVE-"+str(current_year-1),"CVE-"+str(current_year-2), "CobaltStrike" , "免杀" , "内网渗透" ,
 "应急响应", "信息收集", "漏洞" , "渗透", "cobaltstrike" , "rce" , "Burp插件" ,
  "综合利用工具" , "绕过" , "红队" , "漏洞集合"]

# 敏感词列表
SensitiveWords=[]

# 黑名单用户
BlacklistUsers=["thathttp01","thatjohn0a","thatjohn01","redflagblog-com"]

if args.p:
    proxies=proxy(args.p)
if args.t:
    timeout=float(args.t)
if args.H:
    head=headers(args.H)
if args.mT:
    mt=args.mT
if args.iF:
    SearchList=[x.strip('\n') for x in args.iF.readlines()]
if args.sW:
    SensitiveWords=[x.strip('\n') for x in args.sW.readlines()]
if args.c:
    GetAll()
if args.m:
    schedule.every(mt).minutes.do(GetNewSearch)
    if args.d:
        #schedule.every().day.at(args.d).do(WXWork,result).tag('wxwork')
        schedule.every().day.at(args.d).do(DingDing,result).tag('dingding')
        schedule.every().day.at(args.d).do(clearResult).tag('clearflag')
    while 1:
        schedule.run_pending()
        time.sleep(1)
