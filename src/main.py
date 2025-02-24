import network
from utime import sleep, sleep_ms, ticks_ms
from machine import Pin, Timer, ADC, WDT
import urequests
import gc
gc.enable()

# SSID、パスワード、Discord アクセストークンは、別ファイル (secrets.py) へ記載。
from secrets import ssid, password, dhcp, static_ip, static_mask, static_gateway, static_dns, discord_token 

### ウォッチドッグタイマ設定
ENABLE_WDT = False

### ピン設定
button1_pin = 19

debounce = 0
def button1_onClick(button1):
    global debounce, WifiConnected
    if debounce+100 < ticks_ms():
        print('Button1 Click')
        if WifiConnected == True:
            alert_led.on()
            pushDiscord('[玄関チャイム] てすと')
            alert_led.off()
        debounce = ticks_ms()


led = Pin('WL_GPIO0', Pin.OUT)
timer = Timer()
def blink(timer):
    led.toggle()

alert_led = Pin(22, Pin.OUT)
timer4 = Timer()
def alert(timer4):
    alert_led.toggle()
    
timer5 = Timer()
def stop_alert(timer5):
    alert_led.off()
    timer4.deinit()

timer2 = Timer()
def checkWifi(timer2):
    gc.collect()

    if wlan.isconnected() == False:
        print('【エラー】Wi-Fi が切断されました。')
        WifiConnected = False
        machine.reset()

mac = ""
WifiConnected = False
def connect():
    # WiFi 接続
    global wlan
    wlan = network.WLAN(network.STA_IF)
    global mac
    mac = wlan.config('mac').hex().upper()
    print(f'MACアドレスは {mac}')
    wlan.active(True)
    print(f'Wi-Fi "{ssid}" へ接続しています...', end='')
    wlan.connect(ssid, password)
    if dhcp == False:
        wlan.ifconfig((static_ip, static_mask, static_gateway, static_dns))
    retry = 10
    while (wlan.isconnected() == False) and (retry > 0):
        print('.', end='')
        WLANstatus = wlan.status()
        sleep(2)
        retry -= 1
        if ENABLE_WDT:
            wdt.feed()
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f'\n接続しました。IP アドレスは {ip}')
        global WifiConnected
        WifiConnected = True
        timer.deinit()
        timer2.init(freq=0.1, mode=Timer.PERIODIC, callback=checkWifi)
        timer3.init(freq=100, mode=Timer.PERIODIC, callback=adc_read)
        led.on()
        return ip
    else:
        timer.deinit()
        timer.init(freq=5, mode=Timer.PERIODIC, callback=blink)
        if WLANstatus == 1:
            errmsg = 'パスワードが違います。'
        elif WLANstatus == -2:
            errmsg = 'アクセスポイントが見つからないか、応答がありません。'
        else:
            errmsg = f'その他のエラー({WLANstatus})'
        print(f'\n【エラー】Wi-Fi 接続に失敗しました: {errmsg}')
        global WifiConnected
        WifiConnected = False
        sleep(10)
        machine.reset()   

# Discord 通知
def pushDiscord(message):

    endpoint = "https://discordapp.com/api/webhooks/"
    header = {'Content-Type':'application/x-www-form-urlencoded'}

    try:
        # 送信データエンコード
        push_data = f'content={message}'.encode('utf-8')
            
        # デバッグ出力: Discord サーバーへのリクエスト
        print(message)
        print(push_data)

        # 送信
        res = urequests.post(url=endpoint+discord_token, headers=header, data=push_data)
        
        # デバッグ出力: Discord サーバーからのレスポンス
        print(res.text)

        # Discord サーバーとの接続を閉じる
        res.close()
        del res
        gc.collect()

    except Exception as e:
        print(e)
        sleep(5)
        machine.soft_reset()


adc = ADC(Pin(26))
timer3 = Timer()
repeat_check = 0
# https://docs.arduino.cc/built-in-examples/sensors/Knock
def adc_read(timer3):
    val = adc.read_u16()
    if val > 768:
        global repeat_check
        if repeat_check+10000 < ticks_ms():
            alert_led.on()
            pushDiscord('[玄関チャイム] 👈ぴんぽ～ん！')
            alert_led.off()
            repeat_check = ticks_ms()
    

### MAIN
led.on()
alert_led.on()
sleep(2) ## WDT起動猶予時間
if ENABLE_WDT:
    wdt = WDT(timeout=8000)
led.off()
alert_led.off()
sleep(1)

timer.init(freq=1.8, mode=Timer.PERIODIC, callback=blink)
ip = connect()

button1 = Pin(button1_pin, Pin.IN, Pin.PULL_UP)
button1.irq(trigger=Pin.IRQ_RISING, handler=button1_onClick)

while True:
    # 24時間で再起動
    if ticks_ms() >= 86400000:
        machine.reset()

    if ENABLE_WDT:
        wdt.feed()
    
    sleep_ms(100)
